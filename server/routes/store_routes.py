"""
Public Store Routes - Marketplace browsing and checkout
Phase 2: Buyer Storefront Implementation
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from database import get_db, release_db
from services.dodo_service import dodo_service
from config import DODO_ENVIRONMENT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/store", tags=["Store"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ProductListItem(BaseModel):
    """Product item for listing"""

    id: str
    name: str
    short_description: Optional[str]
    price_cents: int
    currency: str
    category: Optional[str]
    cover_image_url: Optional[str]
    seller_name: str
    language: str


class ProductDetail(BaseModel):
    """Full product details"""

    id: str
    name: str
    short_description: Optional[str]
    long_description: Optional[str]
    price_cents: int
    currency: str
    category: Optional[str]
    cover_image_url: Optional[str]
    seller_name: str
    seller_id: str
    language: str
    dodo_product_id: Optional[str]


class CheckoutRequest(BaseModel):
    """Request to create checkout session"""

    buyer_email: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with checkout URL"""

    checkout_url: str
    product_id: str
    price_cents: int


# =============================================================================
# Public Store Endpoints
# =============================================================================


@router.get("/products", response_model=List[ProductListItem])
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price in cents"),
    max_price: Optional[int] = Query(None, ge=0, description="Maximum price in cents"),
    language: Optional[str] = Query(
        None, description="Filter by language (python, nodejs)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all public products in the marketplace.
    No authentication required - this is the public storefront.
    """
    conn = await get_db()
    try:
        # Build dynamic query
        query = """
            SELECT 
                p.id,
                p.name,
                p.short_description,
                p.price_cents,
                p.currency,
                p.category,
                p.cover_image_url,
                p.language,
                u.name as seller_name
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.is_public_store = TRUE
        """
        params = []
        param_idx = 1

        # Apply filters
        if category:
            query += f" AND p.category = ${param_idx}"
            params.append(category)
            param_idx += 1

        if search:
            query += f" AND (p.name ILIKE ${param_idx} OR p.short_description ILIKE ${param_idx})"
            params.append(f"%{search}%")
            param_idx += 1

        if min_price is not None:
            query += f" AND p.price_cents >= ${param_idx}"
            params.append(min_price)
            param_idx += 1

        if max_price is not None:
            query += f" AND p.price_cents <= ${param_idx}"
            params.append(max_price)
            param_idx += 1

        if language:
            query += f" AND p.language = ${param_idx}"
            params.append(language)
            param_idx += 1

        # Add ordering and pagination
        query += (
            f" ORDER BY p.created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        )
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        products = []
        for row in rows:
            products.append(
                ProductListItem(
                    id=row["id"],
                    name=row["name"],
                    short_description=row["short_description"],
                    price_cents=row["price_cents"] or 0,
                    currency=row["currency"] or "USD",
                    category=row["category"],
                    cover_image_url=row["cover_image_url"],
                    seller_name=row["seller_name"],
                    language=row["language"],
                )
            )

        return products

    finally:
        await release_db(conn)


@router.get("/products/{project_id}", response_model=ProductDetail)
async def get_product(project_id: str):
    """
    Get detailed information about a single product.
    No authentication required.
    """
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            """
            SELECT 
                p.id,
                p.name,
                p.short_description,
                p.long_description,
                p.price_cents,
                p.currency,
                p.category,
                p.cover_image_url,
                p.language,
                p.dodo_product_id,
                p.user_id as seller_id,
                u.name as seller_name
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = $1 AND p.is_public_store = TRUE
        """,
            project_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductDetail(
            id=row["id"],
            name=row["name"],
            short_description=row["short_description"],
            long_description=row["long_description"],
            price_cents=row["price_cents"] or 0,
            currency=row["currency"] or "USD",
            category=row["category"],
            cover_image_url=row["cover_image_url"],
            seller_name=row["seller_name"],
            seller_id=row["seller_id"],
            language=row["language"],
            dodo_product_id=row["dodo_product_id"],
        )

    finally:
        await release_db(conn)


@router.post("/checkout/{project_id}", response_model=CheckoutResponse)
async def create_checkout(
    project_id: str,
    data: CheckoutRequest,
):
    """
    Create a checkout session for purchasing a product.
    Returns a Dodo Payments checkout URL.

    The buyer_email is optional but recommended for sending the license.
    """
    conn = await get_db()
    try:
        # Get product details
        product = await conn.fetchrow(
            """
            SELECT 
                p.id,
                p.name,
                p.price_cents,
                p.currency,
                p.dodo_product_id,
                p.user_id as seller_id
            FROM projects p
            WHERE p.id = $1 AND p.is_public_store = TRUE
        """,
            project_id,
        )

        if not product:
            raise HTTPException(
                status_code=404, detail="Product not found or not for sale"
            )

        if not product["dodo_product_id"]:
            raise HTTPException(
                status_code=400, detail="Product not properly configured for checkout"
            )

        # Create Dodo checkout session with metadata
        checkout_url = await dodo_service.create_checkout_session(
            product_id=product["dodo_product_id"],
            metadata={
                "project_id": project_id,
                "seller_id": product["seller_id"],
                "buyer_email": data.buyer_email or "",
            },
        )

        if not checkout_url:
            raise HTTPException(
                status_code=500, detail="Failed to create checkout session"
            )

        logger.info(f"Checkout created for project {project_id}")

        return CheckoutResponse(
            checkout_url=checkout_url,
            product_id=project_id,
            price_cents=product["price_cents"] or 0,
        )

    finally:
        await release_db(conn)


@router.get("/categories")
async def list_categories():
    """
    Get list of available product categories with counts.
    """
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT 
                category,
                COUNT(*) as count
            FROM projects
            WHERE is_public_store = TRUE AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)

        return [{"category": row["category"], "count": row["count"]} for row in rows]

    finally:
        await release_db(conn)

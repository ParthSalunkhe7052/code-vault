# Phase 1 Implementation Plan: Seller Infrastructure & Product Sync

**Objective:** Transform CodeVault users into "Sellers" and allow them to monetize their projects by syncing them with Dodo Payments.

## 1. Context & Configuration
*   **Project Root:** `CodeVaultV1/`
*   **Backend:** FastAPI (`server/`)
*   **Frontend:** React (`frontend/`)
*   **Database:** PostgreSQL (AsyncPG)
*   **Payment Provider:** Dodo Payments (Replacing Stripe)
*   **Goal:** Marketplace Transformation.

## 2. Database Schema Changes
**Task:** Create a migration file or execute SQL to update the schema.

### A. New Table: `sellers`
Stores seller identity and Dodo linkage.
```sql
CREATE TABLE sellers (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    dodo_vendor_id VARCHAR(255), -- If Dodo supports sub-merchants, otherwise internal ref
    payout_details JSONB, -- Encrypted bank/UPI details or Dodo payout ID
    balance_cents BIGINT DEFAULT 0, -- Current unpaid balance
    total_earnings_cents BIGINT DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### B. Update Table: `projects`
Add metadata for the storefront.
```sql
ALTER TABLE projects 
ADD COLUMN is_public_store BOOLEAN DEFAULT FALSE,
ADD COLUMN price_cents INTEGER DEFAULT 0,
ADD COLUMN currency VARCHAR(3) DEFAULT 'USD', -- or INR
ADD COLUMN dodo_product_id VARCHAR(255), -- Link to Dodo Product
ADD COLUMN short_description VARCHAR(255),
ADD COLUMN long_description TEXT, -- Markdown allowed
ADD COLUMN cover_image_url TEXT,
ADD COLUMN category VARCHAR(50); -- e.g., 'automation', 'scraper', 'bot'
```

## 3. Backend Implementation (`server/`)

### A. Dodo Service Module
**File:** `server/services/dodo_service.py` (Create New)
*   **Class:** `DodoService`
*   **Methods:**
    *   `create_product(name: str, description: str, price_cents: int, currency: str) -> str`: Calls Dodo API to create a product/payment link. Returns the `product_id` or `payment_link_id`.
    *   `update_product(...)`: Updates price/details on Dodo.
*   **Config:** Load `DODO_API_KEY` from `server/config.py`.

### B. Seller Routes
**File:** `server/routes/seller_routes.py` (Create New)
*   **Endpoints:**
    *   `POST /api/v1/sellers/onboard`: Accepts payout details, creates `sellers` entry.
    *   `GET /api/v1/sellers/me`: Returns seller status and balance.
    *   `PUT /api/v1/projects/{project_id}/monetization`:
        *   **Input:** `price`, `description`, `is_public`.
        *   **Logic:** 
            1. Validate user owns project.
            2. Update local DB `projects` table.
            3. Call `DodoService.create_product()` if `dodo_product_id` is null.
            4. Save returned `dodo_product_id`.

### C. Register Router
**File:** `server/main.py`
*   Import and include `seller_router`.

## 4. Frontend Implementation (`frontend/`)

### A. Project Settings > Monetization Tab
**File:** `frontend/src/pages/ProjectSettings.jsx` (Modify)
*   Add a new tab "Monetization" or "Store Listing".
*   **Form Fields:**
    *   **Toggle:** "Publish to Store" (`is_public_store`).
    *   **Input:** Price (USD/INR).
    *   **Textarea:** Short Description (Card view).
    *   **Textarea:** Long Description (Markdown editor).
    *   **Action:** "Save & Publish". Triggers `PUT /monetization`.

### B. Seller Onboarding Modal
**File:** `frontend/src/components/SellerOnboarding.jsx` (Create New)
*   If user tries to Publish but is not in `sellers` table, show this modal.
*   **Fields:** "Payment/UPI Details" (for payouts).
*   **Action:** Calls `POST /onboard`.

## 5. Verification Steps
1.  Run DB migrations.
2.  Set `DODO_API_KEY` in `.env`.
3.  Create a project via UI.
4.  Go to Settings > Monetization.
5.  Enable "Publish", set price $10.
6.  Click Save.
7.  **Check:** DB `projects` table should have `dodo_product_id`. Dodo Dashboard should show new Product.

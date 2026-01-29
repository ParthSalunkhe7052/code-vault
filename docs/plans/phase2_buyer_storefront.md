# Phase 2 Implementation Plan: Buyer Storefront & Fulfillment

**Objective:** Create the public-facing marketplace where buyers can purchase scripts, and implement the webhook logic to fulfill orders (Generate License + Send Binary).

## 1. Context & Configuration
*   **Project Root:** `CodeVaultV1/`
*   **Backend:** FastAPI (`server/`)
*   **Frontend:** React (`frontend/`)
*   **Payment Provider:** Dodo Payments.
*   **Dependencies:** Requires Phase 1 (Database changes) to be complete.

## 2. Frontend Implementation (`frontend/`)

### A. Public Layout
**File:** `frontend/src/layouts/PublicStoreLayout.jsx` (Create New)
*   A simplified layout (Navbar with "CodeVault Store" logo, Cart icon, Login button).
*   No sidebar. Dark mode optimized.

### B. Storefront Homepage
**File:** `frontend/src/pages/public/StoreHome.jsx` (Create New)
*   **Route:** `/store`
*   **API Call:** `GET /api/v1/store/products` (List all `is_public_store=true`).
*   **UI:** Grid of Product Cards.
    *   Image, Title, Short Description, Price, "Seller Name".
    *   Filter/Search bar.

### C. Product Detail Page
**File:** `frontend/src/pages/public/ProductDetail.jsx` (Create New)
*   **Route:** `/store/product/:store_slug` or `/:project_id`
*   **UI:**
    *   Full details (Long Description rendered as Markdown).
    *   **"Buy Now" Button:**
        *   **Action:** Redirects to Dodo Payment Link (URL stored in `projects.dodo_payment_link` or generated dynamically via `dodo_product_id`).
        *   **Important:** Must append query params or metadata to the Dodo URL to track `project_id` and `seller_id` if Dodo supports it, OR use a backend proxy endpoint `POST /api/v1/store/checkout/{project_id}` to generate a session.

## 3. Backend Implementation (`server/`)

### A. Public Store Routes
**File:** `server/routes/store_routes.py` (Create New)
*   `GET /products`: Returns public projects (paginated).
*   `GET /products/{id}`: Returns project details.
*   `POST /checkout/{id}`:
    *   **Input:** Buyer Email (optional if auth'd).
    *   **Logic:** Create a Dodo Checkout Session (if API supports) or return the Payment Link.
    *   **Crucial:** Attach Metadata: `{"project_id": "...", "seller_id": "..."}`.

### B. Webhook Handler (The Core Logic)
**File:** `server/routes/dodo_webhook.py` (Create New)
*   **Endpoint:** `POST /api/v1/webhooks/dodo`
*   **Logic:**
    1.  **Verify Signature:** Check Dodo signature header against `DODO_WEBHOOK_SECRET`.
    2.  **Event Check:** Handle `payment.succeeded`.
    3.  **Extract Metadata:** Get `project_id`, `buyer_email`, `transaction_id`.
    4.  **Idempotency:** Check if `transaction_id` already processed in `sales` table.
    5.  **Fulfillment (The "Magic"):**
        *   **License:** Call internal `LicenseService.create_license(project_id, owner_email=buyer_email)`.
        *   **Record Sale:** Insert into `sales` table (created in Phase 3 or here).
        *   **Ledger:** Credit the Seller's balance (Sales Price - Fees).
        *   **Email:** Send email to `buyer_email` with:
            *   "Thank you for buying [Project Name]"
            *   License Key: `XXXX-XXXX`
            *   Download Link: (Link to the *latest* compiled artifact of the project).

### C. Email Service Update
**File:** `server/email_service.py`
*   Add `send_purchase_receipt(email, project_name, license_key, download_url)`.

## 4. Verification Steps
1.  Start backend & frontend.
2.  Navigate to `localhost:5173/store`.
3.  Click a product.
4.  Click "Buy Now" (Should redirect to Dodo Test Checkout).
5.  Complete payment (Test Mode).
6.  **Check Backend Logs:** Webhook received? Signature verified?
7.  **Check Database:** New License created?
8.  **Check Email:** Did "Buyer" receive the license key?

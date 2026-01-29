# Phase 3 Implementation Plan: Payouts & Seller Dashboard

**Objective:** Implement the financial ledger to track seller earnings, calculate platform fees, and provide a dashboard for sellers to view and request payouts.

## 1. Context & Configuration
*   **Project Root:** `CodeVaultV1/`
*   **Database:** PostgreSQL (`sellers` table exists from Phase 1).
*   **Payment Provider:** Dodo Payments.
*   **Platform Fee:** 10% (Configurable).

## 2. Database Schema Changes

### A. New Table: `sales`
Tracks every individual transaction.
```sql
CREATE TABLE sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dodo_transaction_id VARCHAR(255) UNIQUE NOT NULL,
    project_id VARCHAR(32) REFERENCES projects(id),
    seller_id UUID REFERENCES users(id),
    buyer_email VARCHAR(255),
    gross_amount_cents INTEGER, -- Total paid by buyer
    platform_fee_cents INTEGER, -- Your cut
    net_seller_amount_cents INTEGER, -- What seller gets
    status VARCHAR(50) DEFAULT 'completed', -- completed, refunded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### B. New Table: `payouts`
Tracks money sent to sellers.
```sql
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID REFERENCES users(id),
    amount_cents INTEGER,
    status VARCHAR(50), -- pending, processing, paid, failed
    dodo_payout_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);
```

## 3. Backend Implementation (`server/`)

### A. Ledger Logic (in Webhook)
**File:** `server/routes/dodo_webhook.py` (Update)
*   Inside `payment.succeeded` logic:
    *   Calculate Fees: `fee = gross * 0.10`.
    *   Calculate Net: `net = gross - fee`.
    *   Insert into `sales` table.
    *   Update `sellers`: `UPDATE sellers SET balance_cents = balance_cents + net, total_earnings_cents = total_earnings_cents + net WHERE user_id = ...`.

### B. Payout Routes
**File:** `server/routes/payout_routes.py` (Create New)
*   `GET /api/v1/seller/stats`: Returns `balance_cents`, `total_earnings`, list of recent sales.
*   `POST /api/v1/seller/request-payout`:
    *   Checks if `balance_cents > MIN_THRESHOLD` (e.g., $50).
    *   Creates a `payouts` record with status `pending`.
    *   Deducts from `sellers.balance_cents` immediately (to prevent double spend).

### C. Admin Payout Processing (Manual or Auto)
**File:** `server/routes/admin_routes.py`
*   `GET /api/v1/admin/payouts/pending`: List all pending requests.
*   `POST /api/v1/admin/payouts/{id}/process`:
    *   **Manual Mode:** Admin manually sends money via Bank/UPI, then clicks "Mark as Paid".
    *   **Auto Mode (If Dodo Payouts API exists):** Calls `DodoService.trigger_payout(...)`.

## 4. Frontend Implementation (`frontend/`)

### A. Earnings Dashboard
**File:** `frontend/src/pages/dashboard/Earnings.jsx` (Create New)
*   **Stats Cards:** "Available Balance", "Total Earnings", "Pending Payouts".
*   **Chart:** Sales over time (Line chart).
*   **Table:** Transaction History (Date, Project, Amount, Buyer).
*   **Button:** "Request Payout" (Disabled if balance < Threshold).

### B. Sidebar Update
**File:** `frontend/src/components/Sidebar.jsx`
*   Add "Earnings" link (only visible if user has `is_seller=true` or has `sellers` record).

## 5. Verification Steps
1.  **Simulate Sale:** Manually trigger a webhook or make a test purchase.
2.  **Check DB:** `sales` table has row? `sellers.balance_cents` increased? `platform_fee` calculated correctly?
3.  **Frontend:** Go to Earnings page. Verify balance matches DB.
4.  **Payout:** Click "Request Payout".
5.  **Check DB:** `payouts` table has row? `sellers.balance_cents` decreased?
6.  **Admin:** "Process" the payout and verify status updates to `paid`.

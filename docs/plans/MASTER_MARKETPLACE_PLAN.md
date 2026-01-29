# CodeVault Marketplace Master Plan ??

**Version**: 2.0 (The Pivot)
**Objective**: Transform CodeVault from a SaaS tool into a **Digital Goods Marketplace** where developers sell protected binaries, not source code.

---

## 1. The Core Architecture

| Feature | Description | Status |
| :--- | :--- | :--- |
| **Merchant of Record** | **Dodo Payments**. Handles all collections, fraud, and compliance. | ? Integration Started |
| **Seller System** | Users onboard as Sellers. Earnings are tracked in sellers table. | ? Database Ready |
| **Product Sync** | Projects are synced to Dodo as Products. | ? Logic Exists |
| **Storefront** | Public React App (`/store`) for browsing and buying. | **DONE** |
| **Fulfillment** | Webhook triggers License Generation + Binary Delivery. | **DONE** |
| **Payouts** | Weekly cron job sends earnings to Sellers via Dodo Payouts. | **DONE** |

---

## 5. Implementation Status
**ALL SYSTEMS GO.** 🥒
- Database Migrations: APPLIED
- Webhook Fulfillment: ACTIVE
- Storefront: ONLINE
- Payouts: READY


---

## 2. Implementation Roadmap

### Phase 1: Seller Infrastructure (Hardening)
**Goal**: Ensure sellers can onboard, set prices, and sync to Dodo.

1.  **Database Updates**:
    *   Add current_build_id to projects table (FK to cloud_builds). This locks the version sold in the store.
    *   Rename/Standardize payout_details usage in sellers.
2.  **Backend Logic**:
    *   Update PUT /projects/{id}/monetization to require a uild_id (must be a successful, cloud-compiled build).
    *   Ensure dodo_service correctly passes metadata (project_id, seller_id) to Dodo.

### Phase 2: The Buyer Experience (Storefront)
**Goal**: A seamless "Buy -> Download" flow.

1.  **Frontend (React)**:
    *   **Layout**: Create PublicStoreLayout.jsx (Navbar, Cart, minimal footer).
    *   **Routing**: Fix App.jsx to expose /store routes.
    *   **Pages**: Polish StoreHome.jsx and ProductDetail.jsx.
    *   **Checkout**: "Buy Now" button triggers POST /api/v1/store/checkout/{id}, redirecting to Dodo.
2.  **Fulfillment Webhook (dodo_webhook.py)**:
    *   **Trigger**: payment.succeeded.
    *   **Action 1**: Verify Signature.
    *   **Action 2**: Lookup project.current_build_id. If null, FAIL (or alert admin).
    *   **Action 3**: Generate Signed URL for the build artifact (from R2).
    *   **Action 4**: Generate License Key.
    *   **Action 5**: Send Email with **BOTH** License Key and Download Link.

### Phase 3: Payouts & Ledger
**Goal**: Pay the developers.

1.  **Database**:
    *   Create payouts table:
        `sql
        CREATE TABLE payouts (
            id TEXT PRIMARY KEY,
            seller_id TEXT REFERENCES users(id),
            amount_cents INTEGER,
            status VARCHAR(50) DEFAULT 'pending',
            dodo_payout_id VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            processed_at TIMESTAMPTZ
        );
        `
2.  **Backend Routes (payout_routes.py)**:
    *   GET /api/v1/sellers/stats: Returns earnings, pending balance, payout history.
    *   POST /api/v1/sellers/request-payout: Manual trigger (if balance > threshold).
3.  **Cron Job**:
    *   Script to auto-process payouts weekly (or admin trigger).
4.  **Frontend**:
    *   Create Earnings.jsx in Dashboard.

---

## 3. Gap Analysis (Current vs. Goal)

| Component | Current State | Required Change |
| :--- | :--- | :--- |
| **DB Schema** | Added `payouts`, `projects.current_build_id` | **DONE** |
| **Store Routes** | store_routes.py exists | **No Change** |
| **Webhook** | Generates License only | **Add Artifact Download Link Logic** |
| **Frontend** | Broken Routing, Missing Layout | **Implement Layout & Routes** |
| **Payouts** | Non-existent | **Implement Full Stack** |

---

## 4. Execution Order (Pickle Rick Style)

1.  **Database Migration**: Add missing columns/tables.
2.  **Fix Webhook**: Ensure we can deliver the goods (Binary).
3.  **Fix Frontend**: Open the doors to the store.
4.  **Implement Payouts**: Set up the ledger.


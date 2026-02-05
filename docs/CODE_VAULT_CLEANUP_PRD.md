# Code Vault Cleanup & Licensing Optimization PRD

## HR Eng

| Code Vault Cleanup |  | Summary: Remove all Marketplace features to transition Code Vault into a pure Licensing-as-a-Service (LaaS) platform. Ensure stability of HWID/Heartbeat systems and optimize for performance. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick | **Status**: Approved | **Created**: 2026-02-04 |

## Introduction
Code Vault is pivoting from a Marketplace to a dedicated Licensing Tool. The current codebase contains "ghost" logic, orphaned database columns, and UI elements from the marketplace era that pose stability and security risks. This project aims to excise these remnants and optimize the core licensing engine.

## Problem Statement
**Current Process:** The codebase is a hybrid of a reverted marketplace and a licensing tool. It contains dead code (commission logic, seller dashboards) that bloats the system and confuses the architecture.
**Primary Users:** Python/Node.js Developers (Customers), Admin (Owner).
**Pain Points:** Potential broken imports, security holes from unused endpoints, database bloat, UI clutter.
**Importance:** Essential for legal compliance and system stability before relaunching as a pure SaaS.

## Objective & Scope
**Objective:** Create a lean, high-performance Licensing-as-a-Service platform.
**Ideal Outcome:** A codebase with zero marketplace references, a clean database schema, and a streamlined checkout flow.

### In-scope
1.  **Search & Destroy**: Removal of all Marketplace logic (Sellers, Products, Commissions, Payouts).
2.  **Core Stabilization**: Verification and hardening of HWID Locking and Heartbeat systems.
3.  **UI/UX Cleanup**: Removal of "Seller" tabs, marketplace listings, and "Buy" buttons.
4.  **Database Migration**: creating a migration script to drop unused tables/columns.
5.  **Revenue Readiness**: Verification of the "Licensing-only" Stripe checkout flow.

### Not-in-scope
-   Adding new features beyond the core licensing scope.
-   Complete UI redesign (only cleanup).

## Product Requirements

### Critical User Journeys (CUJs)
1.  **The Developer Journey**: A user logs in, creates a project (not a product), generates a license key, and views active sessions (Heartbeats) without seeing any "Seller" options.
2.  **The End-User Journey**: An end-user runs a Python/Node.js app protected by Code Vault. The app validates the HWID and Heartbeat against the server. The server responds instantly without checking "Purchase" history.
3.  **The Subscription Journey**: A user upgrades their Code Vault account to a "Pro" tier via Stripe to unlock more licenses/projects.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | **Remove Marketplace Schema** | As an Admin, I want no "SellerID" or "Commission" columns in the DB to avoid confusion. |
| P0 | **Stabilize HWID/Heartbeat** | As a User, I need my app's locking mechanism to work 100% of the time. |
| P1 | **Clean Dashboard UI** | As a User, I don't want to see "Become a Seller" buttons. |
| P1 | **Fix Checkout Flow** | As a User, I want to pay for the Tool, not a "Product". |
| P2 | **Performance Optimization** | As an Admin, I want the validation endpoint to respond in <100ms. |

## Risks & Mitigations
-   **Risk**: Deleting a shared utility function used by both Marketplace and Licensing.
    -   **Mitigation**: Run `grep` searches for all usages before deletion. Run full test suite after every major deletion.
-   **Risk**: Database data loss during migration.
    -   **Mitigation**: Backup database before applying any schema changes.

## Success Metrics
-   **Zero** "Marketplace" related strings in the codebase (excluding historical migrations).
-   **100%** Success rate on License Validation tests.
-   **<100ms** Response time on `/api/validate`.

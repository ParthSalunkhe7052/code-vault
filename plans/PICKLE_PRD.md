# CodeVault Implementation PRD

## HR Eng

| CodeVault Implementation |  | Summary: Systematic transformation of CodeVault from prototype to Enterprise LaaS platform. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: User **Intended audience**: Engineering | **Status**: Approved **Created**: 2026-02-11 | **Context**: Implementation Plan |

## Introduction

CodeVault is evolving from a credit-burning prototype into a secure, monetized Licensing-as-a-Service (LaaS) platform. This implementation plan addresses Stability, Security, and Monetization in three distinct phases.

## Problem Statement

**Current Process:** Prototype grade. Loose dependencies, weak crypto (HMAC), no revenue model, no integrity checks.
**Primary Users:** Developers protecting their Python/Node.js applications.
**Pain Points:**
1.  **Instability:** Unpinned dependencies, "works on my machine" issues.
2.  **Insecurity:** HMAC is insufficient; lack of binary integrity checks.
3.  **No Revenue:** No enforcement of license types or concurrency.
**Importance:** Without these changes, CodeVault is just a toy. With them, it's a business.

## Objective & Scope

**Objective:** Execute the 3-Phase Implementation Plan to achieve Stability, Security, and Monetization.
**Ideal Outcome:** A stable CLI, Ed25519-secured licensing, and a functional Stripe/Analytics integration.

### In-scope
-   **Phase 1: Stability**: Dependency pinning, CLI consolidation, Integration Tests.
-   **Phase 2: Security**: Ed25519 migration, Binary Integrity, HWID Heuristics, Heartbeat.
-   **Phase 3: Monetization**: License Types (Perpetual/Sub), Floating Licenses, SDK, Analytics, Stripe.

### Not-in-scope
-   New UI designs (unless specified for Analytics).
-   Mobile app support.

## Product Requirements

### Critical User Journeys (CUJs)
1.  **The Upgrade**: Developer updates CLI. Old wrappers are gone. Dependencies fail explicitly if missing.
2.  **The Secure Build**: Developer builds app. Binary hash is recorded. Keys are auto-rotated to Ed25519.
3.  **The Floating User**: End-user grabs a floating license. Heartbeat maintains session. Session expires on disconnect.
4.  **The Admin**: Admin views "Validation Heatmaps" and "Usage Counters" on the dashboard.

### Functional Requirements

| ID | Priority | Requirement | Depends On |
| :--- | :--- | :--- | :--- |
| **S1** | P0 | Remove auto-pip install requests; fail explicitly. | None |
| **S2** | P0 | Pin PKG_VERSION to 5.12.0. | None |
| **S3** | P1 | Replace `os.system('cls')` with ANSI codes. | None |
| **S4** | P1 | Fix SSL CERT_NONE; add `DB_SSL_VERIFY` env var. | None |
| **S5** | P0 | Delete `cli/wrappers.py`; update imports. | None |
| **S6** | P0 | Consolidate CLI; merge commands, thin shim for `lw_compiler.py`. | S5 |
| **S7** | P0 | Pin all dependency versions. | S2 |
| **S8** | P0 | Create integration test suite (7 cases). | S4 |
| **S8b** | P1 | Expose FastAPI /docs with response models. | None |
| **SEC1** | P0 | Migrate to Ed25519; deprecate HMAC. | S8 |
| **SEC2** | P0 | Binary integrity checking (SHA-256). | SEC1 |
| **SEC3** | P1 | HWID validation heuristics & webhooks. | S8 |
| **SEC4** | P0 | Heartbeat periodic re-validation. | SEC1 |
| **SEC5** | P1 | Upgrade javascript-obfuscator to 5.x. | S2, S8 |
| **MON1** | P0 | Implement License types (Perpetual, Sub, Trial). | S8 |
| **MON2** | P1 | Implement Floating/Concurrent licenses. | SEC4, MON1 |
| **MON3** | P1 | Create Standalone SDK (Python/Node). | SEC1, SEC4 |
| **MON4** | P2 | Analytics Dashboard (Heatmaps, Trends). | S8 |
| **MON5** | P0 | Usage-based pricing + Stripe integration. | MON1 |
| **MON6** | P2 | Enhance API Documentation. | Independent |

## Database Migrations
-   010: `signing_algorithm` on projects
-   011: `binary_hashes` table
-   012: Heartbeat columns + `flagged_reason`
-   013: `license_type`, trial/sub fields
-   014: `license_mode`, `max_concurrent`, `license_sessions`
-   015: Analytics Materialized Views
-   016: `usage_counters`, Stripe fields

## Risks & Mitigations
-   **Risk**: Migration breaks existing clients. -> **Mitigation**: 90-day grace period for Ed25519.
-   **Risk**: Floating license race conditions. -> **Mitigation**: Database transactions for session checkout.

## Success Metrics
-   100% of dependencies pinned.
-   0% reliance on `os.system` for clear screens.
-   Successful End-to-End test run of the new Licensing Flow.

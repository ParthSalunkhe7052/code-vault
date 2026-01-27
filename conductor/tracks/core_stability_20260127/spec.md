# Specification: Core System Stability & Verification

## 1. Overview
This track focuses on solidifying the foundations of CodeVault by implementing rigorous verification for two critical components: the Hardware ID (HWID) licensing system and the Cloud Build worker communication. The goal is to ensure that license checks are tamper-resistant and that build jobs are dispatched and processed reliably.

## 2. Goals
- **HWID Verification:** Implement a test suite that simulates various hardware configurations to verify the robustness of the fingerprinting logic.
- **Worker Reliability:** enhance the build worker to handle network interruptions and provide detailed status updates back to the core API.
- **End-to-End Testing:** Create an automated test flow that provisions a license, locks it to a mock HWID, and verifies validation responses.

## 3. Scope
- **In Scope:**
    - server/utils.py (HWID logic)
    - server/routes/license.py (Validation endpoints)
    - server/worker.py (or equivalent build worker logic)
    - New test files in 	ests/
- **Out of Scope:**
    - Frontend dashboard UI changes (API only)
    - New payment gateway integrations

## 4. Technical Requirements
- Use pytest for all new test cases.
- Mock external hardware calls using unittest.mock or pytest-mock.
- Ensure build worker implements exponential backoff for failed status updates.

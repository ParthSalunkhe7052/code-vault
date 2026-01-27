# Implementation Plan - Core Stability

## Phase 1: HWID Licensing Robustness
- [ ] Task: Audit and Refactor HWID Generation
    - [ ] Sub-task: Write Tests: Create unit tests for current HWID generation in server/utils.py using mock system calls.
    - [ ] Sub-task: Implement Feature: Refactor get_hwid to handle edge cases (e.g., missing serial numbers) gracefully.
- [ ] Task: Secure License Validation Endpoint
    - [ ] Sub-task: Write Tests: Create integration tests for /api/validate endpoint checking various invalid/valid signatures.
    - [ ] Sub-task: Implement Feature: Add request signing verification to the validation endpoint if missing.
- [ ] Task: Conductor - User Manual Verification 'HWID Licensing Robustness' (Protocol in workflow.md)

## Phase 2: Cloud Build Worker Reliability
- [ ] Task: Worker Status Reporting
    - [ ] Sub-task: Write Tests: Mock the API receiver and test worker status reporting under network failure simulations.
    - [ ] Sub-task: Implement Feature: Add exponential backoff retry logic to the worker's status update mechanism.
- [ ] Task: Build Job Timeout Handling
    - [ ] Sub-task: Write Tests: Simulate a hung build process and verify the worker kills it and reports failure.
    - [ ] Sub-task: Implement Feature: Implement a strict timeout wrapper for the Nuitka compilation process.
- [ ] Task: Conductor - User Manual Verification 'Cloud Build Worker Reliability' (Protocol in workflow.md)

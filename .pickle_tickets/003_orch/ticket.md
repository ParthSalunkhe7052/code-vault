---
id: 003_orch
title: Orchestration & Polling
status: Triage
priority: High
project: Code Vault
created: 2026-02-07
updated: 2026-02-07
links:
  - url: ../parent.md
    title: Parent Ticket
assignee: Pickle Rick
---

# Description

## Problem to solve
We need to loop until we get a result, and fail if the build takes too long.

## Solution
Create `tests/harness/run_e2e.py`.
- Import `ServerManager` and `simulate_upload`.
- Main logic:
  1. Start Server.
  2. Upload Zip.
  3. Get Build ID.
  4. Poll `/api/builds/{id}` every 2s.
  5. If status == 'SUCCESS', exit 0.
  6. If status == 'FAILURE' or timeout, dump logs and exit 1.

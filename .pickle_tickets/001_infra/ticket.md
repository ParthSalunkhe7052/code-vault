---
id: 001_infra
title: Infrastructure Setup (Backend Launcher)
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
We need the backend running to test against it, but we don't want to manually start 3 terminals.

## Solution
Create `tests/harness/manage_server.py`.
- Class `ServerManager`
- `start()`: Launches `server/main.py` (or correct entry point) in a subprocess.
- `stop()`: Kills the process tree.
- Wait for health check (port 8000) before proceeding.

---
id: 002_payload
title: Payload Engineering (API Replay)
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
Python's `requests` library creates "perfect" requests. Browsers create messy ones. We need the mess.

## Solution
Create `tests/harness/replay_payload.py`.
- Analyze `frontend/src` to find the Cloud Build upload call.
- Replicate Headers (User-Agent, specific Content-Type boundary behavior if needed).
- Load `TestBot/TestBot.zip` dynamically.
- Function `simulate_upload(server_url, zip_path) -> response`.

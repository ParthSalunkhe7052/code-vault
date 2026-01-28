---
id: 11111111
title: Research Subscription Logic
status: Triage
priority: Urgent
project: CodeVault
created: 2026-01-28
updated: 2026-01-28
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [research]
assignee: Pickle Rick
---
# Description
## Problem to solve
We need to identify exactly where the "is Pro" check is failing for Enterprise users.

## Solution
1. Search codebase for `is_pro` or `isPro` usage.
2. Check `server/models.py` or `server/routes/` for subscription validation.
3. Check `frontend/` for banner rendering logic.

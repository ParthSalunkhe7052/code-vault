---
id: 44444444
title: Verify Subscription Fixes
status: Backlog
priority: High
project: CodeVault
created: 2026-01-28
updated: 2026-01-28
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [verify, test]
assignee: Pickle Rick
---
# Description
## Problem to solve
Ensure the fixes actually work and didn't break Free users.

## Solution
Manual verification:
1. Simulate Enterprise user -> Check Cloud Build (Mac allowed?) -> Check Wizard (No banners?).
2. Simulate Free user -> Check Cloud Build (Mac blocked?) -> Check Wizard (Banners present?).

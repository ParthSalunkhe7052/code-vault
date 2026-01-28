---
id: 22222222
title: Fix Backend Subscription Logic
status: Backlog
priority: Urgent
project: CodeVault
created: 2026-01-28
updated: 2026-01-28
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [backend, bug]
assignee: Pickle Rick
---
# Description
## Problem to solve
The backend likely treats "Enterprise" as a distinct tier that doesn't inherit "Pro" permissions for Cloud Build.

## Solution
Update the User model or permission dependency to ensure `is_pro` returns True for Enterprise users, or update the check to `is_pro or is_enterprise`.

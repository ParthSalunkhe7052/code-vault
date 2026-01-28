---
id: notify
title: Build Notifications
status: Triage
priority: Medium
project: CodeVault
created: 2026-01-27
updated: 2026-01-27
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [frontend, notifications]
assignee: Pickle Rick
---

# Description

## Problem to solve
User doesn't know when build finishes if tab is backgrounded.

## Solution
In `BuildContext`, when status changes to `completed` or `failed`:
- Trigger `new Notification(...)`.
- Ensure permissions are requested.

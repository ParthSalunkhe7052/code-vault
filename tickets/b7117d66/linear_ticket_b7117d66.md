---
id: b7117d66
title: [SEC1] Ed25519 everywhere
status: Triage
priority: Medium
project: CodeVault
created: 2026-02-11
updated: 2026-02-11
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [phase1]
assignee: Pickle Rick
---

# Description

## Problem to solve
Implement task SEC1 from the plan.

## Solution
Deprecate HMAC, auto-generate keys. Files: server/utils.py, server/routes/license_routes.py

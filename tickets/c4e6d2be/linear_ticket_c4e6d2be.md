---
id: c4e6d2be
title: [S4] Fix SSL CERT_NONE
status: Done
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
Implement task S4 from the plan.

## Solution
Add DB_SSL_VERIFY env var in server/database.py, server/config.py

---
id: backend
title: Fix output_name validation in cloud_build_routes.py
status: Triage
priority: High
project: CodeVault
created: 2026-01-26
updated: 2026-01-26
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [backend, python]
assignee: Pickle Rick
---

# Description

## Problem to solve
The `config` object generated in `cloud_build_routes.py` allows `output_name` to be empty/null.

## Solution
Modify `server/routes/cloud_build_routes.py`.
In the `start_cloud_build` function (or wherever config is built):
1.  Check if `output_name` is empty/null.
2.  If so, default to sanitized project name or "app".

---
id: 1448fe8d
title: [S1] Remove auto-pip install of requests
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
Implement task S1 from the plan.

## Solution
Fail explicitly if missing. Files: cli/lw_compiler.py, cli/pyproject.toml, cli/requirements.txt

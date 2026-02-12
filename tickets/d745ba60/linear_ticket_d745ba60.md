---
id: d745ba60
title: [SEC2] Binary integrity checking
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
Implement task SEC2 from the plan.

## Solution
SHA-256 hash at build. Files: cli/compiler_logic.py, server/models.py

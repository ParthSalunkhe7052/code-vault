---
id: optimize
title: Optimize Cloud Runner Config
status: Triage
priority: High
project: CodeVault
created: 2026-01-27
updated: 2026-01-27
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [implementation, python]
assignee: Pickle Rick
---

# Description

## Problem to solve
Current config thrashes the CPU.

## Solution
Modify `cloud_runner.py`:
1. Cap `jobs` at 2 (or `cpu_count` if < 2).
2. Enable `anti-bloat` by default.
3. Add logging for applied optimizations.

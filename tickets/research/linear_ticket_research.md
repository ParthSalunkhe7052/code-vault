---
id: research
title: Research Build Resource Usage
status: Triage
priority: High
project: CodeVault
created: 2026-01-27
updated: 2026-01-27
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [research, audit]
assignee: Pickle Rick
---

# Description

## Problem to solve
Need to verify current flags and logic in `cloud_runner.py`.

## Solution
Read `cloud_runner.py` and identify where `jobs` count is set and how `anti-bloat` is toggled.

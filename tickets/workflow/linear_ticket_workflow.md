---
id: workflow
title: Add output_name fallback in cloud-compile.yml
status: Triage
priority: Medium
project: CodeVault
created: 2026-01-26
updated: 2026-01-26
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [github-actions, ci]
assignee: Pickle Rick
---

# Description

## Problem to solve
Even if backend sends bad data, the workflow shouldn't produce `.exe`.

## Solution
Modify `.github/workflows/cloud-compile.yml`.
In the `Parse config` step (both Windows and Linux/MacOS):
1.  Check if extracted `output_name` is empty.
2.  If empty, set it to "app".

---
id: t5
title: "CLI: Modernize UI with Rich Progress"
status: Done
priority: Medium
project: project
created: 2026-02-16
updated: 2026-02-16
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [cli, ui]
assignee: Pickle Rick
---

# Description

## Problem to solve
Current terminal output is fragmented and sometimes lags during long builds.

## Solution
1. Replace manual progress bar logic with `rich.progress.Progress`.
2. Integrate with the new `asyncio` compiler classes for smooth updates.

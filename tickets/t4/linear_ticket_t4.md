---
id: t4
title: "CLI: Environment Doctor & Pre-flight Checks"
status: Done
priority: Medium
project: project
created: 2026-02-16
updated: 2026-02-16
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [cli, ux]
assignee: Pickle Rick
---

# Description

## Problem to solve
Users often start builds only to have them fail minutes later due to missing tools (node, gcc, etc.).

## Solution
1. Implement `detect_tools()` function.
2. Run checks before starting any build.
3. Provide helpful error messages with installation links.

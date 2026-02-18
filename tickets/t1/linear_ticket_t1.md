---
id: t1
title: "CLI Refactor: Decouple Compiler Logic"
status: Done
priority: High
project: project
created: 2026-02-16
updated: 2026-02-16
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [core, cli, refactor]
assignee: Pickle Rick
---

# Description

## Problem to solve
`cli/compiler_logic.py` is a monolith. It mixes Python and Node.js logic, making it hard to implement language-specific optimizations safely.

## Solution
1. Create `cli/compilers/base.py`, `cli/compilers/python.py`, and `cli/compilers/node.py`.
2. Port logic from `compiler_logic.py` into these classes.
3. Switch to `asyncio.create_subprocess_exec` for process management.

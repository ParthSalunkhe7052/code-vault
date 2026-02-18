---
id: t3
title: "Python: Implement Turbo Mode Optimizations"
status: Done
priority: High
project: project
created: 2026-02-16
updated: 2026-02-16
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [cli, python, performance]
assignee: Pickle Rick
---

# Description

## Problem to solve
CLI builds are slower and larger than Cloud Builds because they don't exclude heavy, unused standard library modules.

## Solution
1. Port `blacklist_modules` from `server/compilers/python_compiler.py`.
2. Add `--turbo` flag logic to the Python compiler class.
3. Ensure Nuitka uses these exclusions during compilation.

---
id: t2
title: "Node.js: Implement Bootstrap Wrapping"
status: Done
priority: High
project: project
created: 2026-02-16
updated: 2026-02-16
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [cli, nodejs, security]
assignee: Pickle Rick
---

# Description

## Problem to solve
Current "inline injection" overwrites user source code, which is risky and breaks modern JS syntax.

## Solution
1. Port `_prepare_package_json` from `server/compilers/nodejs_compiler.py` to the CLI.
2. Implement `_create_bootstrap_file` logic.
3. Update `pkg` configuration to use the bootstrap file as the entry point.

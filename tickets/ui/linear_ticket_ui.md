---
id: ui
title: Global Build Indicator UI
status: Triage
priority: Medium
project: CodeVault
created: 2026-01-27
updated: 2026-01-27
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [frontend, ui]
assignee: Pickle Rick
---

# Description

## Problem to solve
User needs to see build status outside the Wizard.

## Solution
Create `components/GlobalBuildStatus.jsx`.
- Fixed position (bottom right?).
- Shows "Building [Project]... 45%".
- Click opens Wizard/Details.
Add to `App.jsx`.

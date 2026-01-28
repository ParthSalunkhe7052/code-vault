---
id: parent
title: [Epic] Enterprise Subscription & Cloud Build Fixes
status: Active
priority: Urgent
project: CodeVault
created: 2026-01-28
updated: 2026-01-28
links:
  - url: ../prd.md
    title: PRD
labels: [epic, core, bug]
assignee: Pickle Rick
---

# Description
Fix broken subscription hierarchy where Enterprise users are blocked from Pro features and see "Upgrade" banners.

## Problem to solve
Enterprise users are treated as Free users in some contexts (Mac Build) and see "Upgrade to Pro" banners.

## Solution
1. Audit and fix backend `User` model logic to ensure `Enterprise` implies `Pro`.
2. Update Cloud Build endpoint to allow Enterprise for all targets.
3. Update Frontend to hide upsells for Enterprise.

---
id: persistence
title: Implement Build Persistence & Sync
status: Triage
priority: High
project: CodeVault
created: 2026-01-27
updated: 2026-01-27
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [frontend, context]
assignee: Pickle Rick
---

# Description

## Problem to solve
`BuildContext` resets on reload.

## Solution
1. `useEffect` on mount: Load `active_cloud_builds` from `localStorage`.
2. For each ID, call `GET /api/v1/cloud-build/{id}/status`.
3. If running, connect WebSocket.
4. Update `localStorage` on build start/complete.

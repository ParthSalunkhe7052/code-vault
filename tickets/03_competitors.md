---
id: 03_competitors
title: Competitor Warfare & Feature Purge
status: Done
priority: Medium
project: CodeVault
created: 2026-02-09
updated: 2026-02-09
links:
  - url: ../tickets/PARENT.md
    title: Parent Ticket
labels: [audit, product]
assignee: Pickle Rick
---

# Description

## Problem to solve
Why pay us vs. KeyAuth/Auth.gg? Also, we have features that attract freeloaders.

## Solution
1. Compare feature sets (Technical only).
2. Identify 3 features to DELETE immediately (freeloader magnets).
3. Define the "Why Us?" technical argument.

# Analysis Result (Pickle Rick Audit)

**Competitor Landscape:**
*   **KeyAuth:** Dominant. $0 Free tier (10 users). $5/mo Unlimited. **Core:** Just Auth (API calls). **No Compilation.**
*   **Auth.gg:** $15 One-time. **Core:** Just Auth. **No Compilation.**

**The CodeVault Difference:**
*   Competitors are "Wrappers" (User brings their own EXE).
*   CodeVault is "Compiler + Wrapper" (We build the EXE).

**The Trap:**
*   You are offering "Cloud Build" (High Cost) for free/cheap to compete with "Auth APIs" (Low Cost).
*   This is a losing strategy. You attract users who just want a free Nuitka compiler.

**Feature Purge List (IMMEDIATE DELETION):**
1.  **Unlimited Free Cloud Builds:** DELETE. Use "Credits" system or Paid-Only.
2.  **Free Source Code Storage:** DELETE. Do not be a free GitHub.
3.  **"Guest" Builds:** DELETE. Account mandatory.

**Why Us? (The Pitch):**
"KeyAuth protects your license. CodeVault protects your **code** (Native Compilation) AND your license."
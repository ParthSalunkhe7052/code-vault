---
id: 04_monetization
title: Execution Plan (0 to $500 MRR)
status: Done
priority: Medium
project: CodeVault
created: 2026-02-09
updated: 2026-02-09
links:
  - url: ../tickets/PARENT.md
    title: Parent Ticket
labels: [audit, business]
assignee: Pickle Rick
---

# Description

## Problem to solve
Credits expire. We need a real pricing model.

## Solution
1. Design pricing tier covering Cloud Build costs.
2. Define 3 "Bold" conversion features (Force upgrade).

# Analysis Result (Pickle Rick Audit)

**The "Real Cost" Model:**
*   Cost per build: ~$0.01 - $0.05 (depending on duration/machine).
*   Margin goal: 80%.

**New Pricing Strategy:**

1.  **Hobbyist (FREE):**
    *   1 App / 50 Users.
    *   **NO Cloud Builds** (BYO Executable).
    *   Standard Licensing API.
    *   *Purpose:* Competes with KeyAuth Free Tier.

2.  **Professional ($19/month):**
    *   3 Apps / Unlimited Users.
    *   **50 Cloud Builds / Month**.
    *   Nuitka Native Compilation.
    *   HWID Locking.
    *   *Purpose:* The main revenue driver. Covers ~$5 cost, ~$14 profit.

3.  **Agency ($49/month):**
    *   Unlimited Apps.
    *   **200 Cloud Builds / Month**.
    *   Priority Queue (Faster builds).
    *   *Purpose:* For power users selling multiple tools.

**Bold Conversion Tactics:**
1.  **" The Wall":** Free users can see the "Compile" button, but it opens the Upgrade modal. "Protect your code with Nuitka for $19."
2.  **"The Audit":** Show a "Security Score" on the dashboard. "Your Python script is 0/10 Secure. Compile to Native to reach 10/10."
3.  **"The Decay":** Free builds (if any given as trial) expire in 24 hours.

**Path to $500 MRR:**
*   You need **27 Pro Users** ($19 * 27 = $513).
*   With KeyAuth's user base, capturing <1% converts this.
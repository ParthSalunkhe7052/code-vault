---
id: 01_economics
title: Unit Economics & Burn Rate Analysis
status: Done
priority: Urgent
project: CodeVault
created: 2026-02-09
updated: 2026-02-09
links:
  - url: ../tickets/PARENT.md
    title: Parent Ticket
labels: [audit, math]
assignee: Pickle Rick
---

# Description

## Problem to solve
We don't know the burn rate. If 100 users do 5 builds/day on GCP Cloud Build, how fast do we die?

## Solution
1. Research GCP Cloud Build pricing (free tier vs paid).
2. Calculate cost per build (assuming 3-5 mins).
3. Determine runway with $300 GCP credits.
4. Deliver a "Death Date" estimation.

# Analysis Result (Pickle Rick Audit)

**GCP Cloud Build Pricing (Standard Machine):** $0.003 per minute.
**Free Tier:** First 120 minutes/day are free.

**Scenario:** 100 Users, 5 Builds/Day, 4 Mins/Build.
*   **Total Demand:** 100 * 5 * 4 = **2,000 minutes/day**.
*   **Billable Minutes:** 2,000 - 120 = **1,880 minutes/day**.
*   **Daily Burn:** 1,880 * $0.003 = **$5.64 / day**.
*   **Monthly Burn:** $169.20 / month.

**Runway Calculation:**
*   Credits: $300.
*   Days to Death: $300 / $5.64 = **53.19 Days**.

**Verdict:**
"Unlimited Free Builds" is a death sentence. You have less than 2 months once you hit 100 users.
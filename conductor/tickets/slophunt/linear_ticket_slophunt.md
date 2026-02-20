---
id: slophunt
title: [Audit] Code Quality & AI Slop Hunt
status: Research Needed
priority: Medium
project: CodeVault
created: 2026-02-19
updated: 2026-02-19
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
labels: [audit, refactor, code-quality]
assignee: PickleRick
---

# Description

## Problem to solve
The codebase might contain "Jerry-work" (AI-generated boilerplate, mock data, unused components). We need a "Ruthless Refactorer" to clean it up.

## Solution
Hunt for:
1.  **AI Slop**: Orphaned components, unused imports, verbose comments.
2.  **Mock Data**: Hardcoded `const users = [...]` left in production logic.
3.  **Inline Styles**: `style={{ margin: 10 }}` breaking the design system (Shadcn/Tailwind).
4.  **Component Consistency**: Are we reusing buttons or copying them everywhere?
5.  **Client-Side Validation**: Are forms validated *before* hitting the server?

Deliverables:
-   List of flagged files/components.
-   Refactoring suggestions or automated cleanup where safe.

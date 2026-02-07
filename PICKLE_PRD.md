# Frontend Refactoring & Security Overhaul PRD

## HR Eng

| Frontend Overhaul PRD |  | Comprehensive refactoring of the Dashboard and Landing Page to address critical security vulnerabilities, accessibility failures, and technical debt. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: User **Intended audience**: Engineering | **Status**: Draft **Created**: 2026-02-07 | **Context**: CodeVault Frontend |

## Introduction

The CodeVault frontend (Dashboard and Landing Page) has significant technical debt, critical security flaws (fake encryption, hardcoded keys), and accessibility violations. This PRD defines the scope for a "God Mode" overhaul to bring the engineering quality up to the level of the visual design.

## Problem Statement

**Current Process:** The current frontend is visually appealing but engineered with "Jerry-level" shortcuts.
**Primary Users:** Developers using CodeVault to license their software.
**Pain Points:**
-   False sense of security (client-side encryption).
-   Accessibility barriers (screen readers cannot use key dialogs).
-   Fragile architecture (excessive re-renders, window event bus).
-   Zero type safety despite TypeScript config.
**Importance:** Critical. Security flaws undermine the core value proposition (licensing protection). Accessibility violations are legally and ethically unacceptable.

## Objective & Scope

**Objective:** Eliminate 100% of identified blockers (Security, A11y, Build) and significant technical debt.
**Ideal Outcome:** A secure, accessible, type-safe, and performant frontend codebase.

### In-scope or Goals
-   **Security**: Remove fake encryption, secure cookies, fix auth navigation, try-catch logout.
-   **Accessibility**: Fix ConfirmDialog, Navigation labels, Skip links, reduced motion.
-   **Architecture**: Optimize Contexts (useMemo), fix WebSocket reconnection, optimistic updates.
-   **Type Safety**: Migration to TSX, strict mode.
-   **Landing Page**: SEO tags, contrast fixes, build pipeline fixes.

### Not-in-scope or Non-Goals
-   Backend API changes (except where strictly necessary for auth cookies).
-   New feature development (Feature freeze effective immediately).

## Product Requirements

### Critical User Journeys (CUJs)
1.  **Secure Authentication**: User logs in, receives a secure cookie (or token), and session persists safely. On 401, user is prompted to save work before redirect.
2.  **Accessible Project Deletion**: Screen reader user navigates to "Delete Project", hears the alert dialog context, confirms deletion using keyboard only.
3.  **Resilient Build Monitoring**: User starts a build. Network glitches. WebSocket reconnects automatically without page refresh.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | **Security**: Remove client-side encryption & hardcoded keys. | As a user, I want my data to be actually secure, not obfuscated. |
| P0 | **Security**: Fix hard navigation on 401. | As a user, I don't want to lose my work if my token expires. |
| P0 | **A11y**: Fix ConfirmDialog accessibility. | As a screen reader user, I need to know what I'm confirming. |
| P0 | **Build**: Enable strict type checking. | As a dev, I want the build to fail if types are wrong. |
| P1 | **Perf**: Fix Context re-renders. | As a user, I want the app to be snappy. |
| P1 | **Architecture**: WebSocket Reconnection. | As a user, I want build updates to persist through network blips. |
| P1 | **Landing Page**: SEO & Social Meta Tags. | As a marketing lead, I want links to look professional on Twitter. |

## Risks & Mitigations

-   **Risk**: TS migration reveals massive hidden bugs. **Mitigation**: Phased migration (critical paths first).
-   **Risk**: Auth changes break login. **Mitigation**: Test E2E login flow extensively.

## Business Benefits

**Success Metrics:**
| Metric | Current State | Future State | Impact |
| :---- | :---- | :---- | :---- |
| Build Errors (Types) | Ignored | 0 | Higher reliability |
| Lighthouse A11y Score | ~60 | >90 | Legal compliance |
| Security Vulnerabilities | 4 (Critical) | 0 | Trust |

## Stakeholders / Owners

| Name | Role |
| :---- | :---- |
| Pickle Rick | Lead Engineer |
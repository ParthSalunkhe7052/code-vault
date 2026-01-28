# Enterprise Subscription & Cloud Build Fixes PRD

## HR Eng

| Enterprise Subscription Fixes | | Fix broken subscription hierarchy where Enterprise users are blocked from Pro features. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: Parth **Intended audience**: Engineering | **Status**: Draft **Created**: 2026-01-28 | **Self Link**: N/A **Context**: CodeVaultV1 |

## Introduction

Currently, the CodeVault platform treats "Enterprise" users like second-class citizens, showing them "Upgrade to Pro" banners and blocking access to Mac Cloud Builds. This is unacceptable logic slop. Enterprise includes Pro.

## Problem Statement

**Current Process:** Enterprise users log in and are bombarded with upsells intended for Free users. They are also denied access to Mac builds.
**Primary Users:** Enterprise Admins/Users.
**Pain Points:**
- False "Upgrade to Pro" prompts.
- Blocked access to paid features (Mac Build).
- Broken user trust.
**Importance:** Enterprise users pay the most. They should get the best experience, not a broken one.

## Objective & Scope

**Objective:** Correct the subscription validation logic so Enterprise inherits all Pro privileges and UI elements reflect the correct tier.
**Ideal Outcome:** Enterprise users see zero upsells and have full access to all Cloud Build targets (Win, Mac, Linux).

### In-scope or Goals
- Fix `User.is_pro` / `User.plan` logic to ensure Enterprise >= Pro.
- Update Cloud Build permission checks.
- Update UI components (Wizard, Dashboard) to hide "Upgrade" banners for Enterprise.
- Verify Free users are still correctly restricted.

### Not-in-scope or Non-Goals
- Changing the pricing model.
- Adding new features to Pro.

## Product Requirements

### Critical User Journeys (CUJs)
1.  **Enterprise Cloud Build**: Enterprise User selects "Mac Build" -> System validates Enterprise tier -> Build initiates. (No "Upgrade" banner).
2.  **Wizard Navigation**: Enterprise User clicks through the setup wizard -> All Pro settings are enabled -> No upsell banners appear.
3.  **Free User Gate**: Free User selects "Mac Build" -> System blocks request -> "Upgrade to Pro" modal appears.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | Enterprise tier must grant Pro access privileges. | As an Enterprise user, I want to use Mac Cloud Build so I can deploy my app. |
| P0 | Remove "Upgrade to Pro" banners for Enterprise. | As an Enterprise user, I don't want to be asked to upgrade to a lower tier. |
| P1 | Consolidate subscription checking logic. | As a developer, I want a single source of truth for "Can use feature X". |

## Assumptions

- There is a `plan` or `tier` field in the user/org model.
- The UI checks a flag like `isPro` which is currently returning `false` for Enterprise.

## Risks & Mitigations

- **Risk**: Giving Free users access by accident. -> **Mitigation**: Add explicit unit tests for Free user restrictions.

## Business Benefits/Impact/Metrics

**Success Metrics:**
- Zero support tickets about "Upgrade" banners from Enterprise users.
- 100% success rate for Enterprise Mac Build requests (auth-wise).

## Stakeholders / Owners

| Name | Team/Org | Role | Note |
| :---- | :---- | :---- | :---- |
| Parth | Eng | User | The one suffering from the bugs. |

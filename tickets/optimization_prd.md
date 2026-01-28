# Cloud Build Optimization Research PRD

## HR Eng

| Cloud Build Optimization Research PRD |  | Summary: Investigation into reducing cloud build times (currently ~30m) to match local CLI performance (~15m) using free resources. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: User **Intended audience**: DevOps, Engineering | **Status**: Draft **Created**: 2026-01-27 | **Self Link**: N/A **Context**: GitHub Student Pack Available |

## Introduction

The current "CodeVaultV1" CI/CD pipeline relies on GitHub Actions. It is significantly slower (2x) than local builds. This project aims to analyze the bottlenecks and propose a concrete plan to optimize or replace the current runner setup, strictly adhering to "free tier" constraints.

## Problem Statement

**Current Process:**
- GitHub Actions workflow runs build scripts.
- Duration: ~30 minutes for a small test bot.
- Comparison: Local CLI tool does the same in ~15 minutes.

**Pain Points:**
- Slow feedback loop for developers.
- Inefficient use of "Action Minutes" (even if free, time is money... sort of).

**Importance:**
- Faster builds = faster iteration.
- Reducing 30m -> 15m cuts wait time by 50%.

## Objective & Scope

**Objective:** Identify the root cause of the performance delta and propose a solution to bring cloud builds under 20 minutes using free resources.

### In-scope or Goals
- Analyze current `.github/workflows` configuration.
- specific comparison of Local vs. Cloud environment resources (CPU/RAM/IO).
- Research GitHub Actions optimizations (Caching, Artifacts, Docker layer caching).
- Research Alternative Free Providers (GitLab CI, Azure Pipelines, CircleCI) compatible with the Student Pack.
- detailed "Optimization Plan" document delivery.

### Not-in-scope or Non-Goals
- Implementing the final production changes (this is a Planning phase).
- Paid solutions (Strictly $0 budget).

## Product Requirements

### Critical User Journeys (CUJs)
1.  **Analysis**: Engineer reviews current workflow and identifies bottlenecks (CPU bound? Network bound?).
2.  **Research**: Engineer evaluates alternatives (e.g., "Is CircleCI free tier faster?").
3.  **Decision**: Engineer presents a "Recommended Path Forward" document.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | Root Cause Analysis | As a dev, I want to know *why* GH Actions is slow. |
| P0 | Optimization Strategy | As a dev, I want a list of steps to speed it up (e.g., "Enable caching"). |
| P1 | Alternative Evaluation | As a dev, I want to know if I should switch providers. |

## Assumptions
- The "Local CLI" is optimized or benefits from local caching/state that the Cloud runner lacks.
- The build process is CPU/Disk intensive.

## Risks & Mitigations
- **Risk**: GitHub Actions Free Tier (2-core) is physically too slow. -> **Mitigation**: Investigate efficient parallelism or self-hosted runners (if free compute is found).

## Business Benefits/Impact/Metrics

**Success Metrics:**

| Metric | Current State (Benchmark) | Future State (Target) | Impact |
| :---- | :---- | :---- | :---- |
| Build Time | ~30 Minutes | < 20 Minutes | 33%+ Improvement |
| Cost | Free | Free | Sustainability |

## Stakeholders / Owners

| Name | Team/Org | Role | Note |
| :---- | :---- | :---- | :---- |
| User | Engineering | Owner | Student Pack Holder |

# CodeVault CLI Modernization PRD

## HR Eng

| CodeVault CLI Modernization PRD |  | Modernizing the local CLI tool to match server-side performance and reliability without breaking Cloud Build. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: Morty **Intended audience**: Engineering | **Status**: Draft **Created**: 2026-02-16 | **Visibility**: Internal |

## Introduction

The CodeVault CLI is the local arm of our Licensing-as-a-Service platform. Currently, it's a bit of a Jerry—functional but brittle. This project refactors the CLI to use the same robust "Bootstrap" wrapping and "Turbo" optimization strategies used by our server-side Cloud Build, while maintaining strict isolation to ensure Cloud Build remains untouched.

## Problem Statement

**Current Process:** Users run `lw_compiler.py` which uses "inline injection" (modifying source code directly) and synchronous subprocess calls.
**Primary Users:** Developers license their Python/Node.js apps locally.
**Pain Points:** 
- **Inline Injection Risk:** Modifying user source code can break syntax (ESM/CJS conflicts) and makes debugging a nightmare.
- **Performance:** Lacks the aggressive module blacklisting used in Cloud Build.
- **UI Lag:** Synchronous calls can cause the CLI to hang or show stale progress.
**Importance:** As we scale, the local experience must be as professional and reliable as the cloud experience.

## Objective & Scope

**Objective:** Upgrade the CLI architecture to match Server-side standards (Async, Modular, Bootstrap-based).
**Ideal Outcome:** A faster, more reliable CLI that produces high-quality protected binaries on Windows.

### In-scope or Goals
- **Architecture Refactor:** Decouple `compiler_logic.py` into specialized language-specific classes.
- **Node.js Bootstrap Wrapping:** Create a separate `_cv_bootstrap.js` instead of modifying user code.
- **Python Turbo Mode:** Implement aggressive module blacklisting to reduce EXE size and build time.
- **Async Process Management:** Use `asyncio` for all subprocess calls to prevent UI hangs.
- **Environment Doctor:** Pre-flight checks for `node`, `npm`, `nuitka`, etc.

### Not-in-scope or Non-Goals
- **Legacy Support:** No support for old "inline" wrappers.
- **Cross-Platform:** Windows only for this phase.
- **Server Modification:** Absolute ZERO changes to `server/compilers/` logic (we copy/port logic, not link it).

## Product Requirements

### Critical User Journeys (CUJs)
1. **Authenticated Build**: User logs into CLI (`codevault login`), selects a build from the dashboard, and the CLI pulls the config and starts a modernized build.
2. **Protected Node.js Binary**: User compiles a Node.js project. CLI creates a bootstrap loader, uses `pkg` with optimized assets scanning, and produces a working EXE without source code corruption.
3. **Optimized Python Binary**: User compiles a Python project. CLI applies "Turbo Mode" exclusions, significantly reducing build time compared to standard Nuitka.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | Specialized Compiler Classes | As a developer, I want a clean codebase that doesn't mix Node and Python logic. |
| P0 | Bootstrap Wrapping (Node) | As a user, I want my source code left untouched during the build process. |
| P1 | Turbo Mode (Python) | As a user, I want my local builds to be as fast as the Cloud Builds. |
| P1 | Async UI Progress | As a user, I want to see real-time, non-laggy progress updates. |
| P2 | Environment Doctor | As a user, I want to know exactly why a build failed (e.g., missing GCC) before it starts. |

## Assumptions

- The existing Dashboard API for config retrieval is stable.
- Users have the necessary build tools (`node`, `python`, `nuitka`) installed for local compilation.

## Risks & Mitigations

- **Risk**: Divergent logic between CLI and Server. -> **Mitigation**: Ported logic must be kept in sync; future refactors should consider a shared 'core' library (post-modernization).
- **Risk**: Breaking user projects with new bootstrap logic. -> **Mitigation**: Comprehensive local testing with `test_projects/` before release.

## Business Benefits/Impact/Metrics

**Success Metrics:**
- **Build Success Rate**: Increase from ~85% to 98% (by eliminating inline injection errors).
- **Build Time**: 30-40% reduction in Python compilation time.
- **Binary Size**: 20-30% reduction in Python EXE size.

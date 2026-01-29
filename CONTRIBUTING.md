# Contributing to CodeVault

## 🧠 For Agents (The Brain)
**STOP.** Before you edit any code in `CodeVaultV1`, you must:
1.  Read `.agent/rules` for the latest directives.
2.  Check `.agent/plans` for the active mission.
3.  **Shadow Directory Rule**: If you create a new feature or major refactor, save your "Implementation Plan" artifact in the parent `artifacts/` folder. This helps us track history even if Git gets messy.

## 🛠️ Recommended Tools
We use a specific stack to keep "vibe coding" safe and fast.

| Tool | Purpose | Status |
| :--- | :--- | :--- |
| **GitButler** | Virtual branching for testing ideas without conflicts. | **Recommended** (Windows) |
| **Aider** | CLI companion for large refactors. | **Recommended** |
| **Trivy** | Security scanner for secrets and vulnerabilities. | **Essential** |
| **Ruff** | Ultra-fast Python linter/formatter. | **Required** |
| **Biome** | Fast Node.js linter/formatter. | **Required** |

## 📦 Project Structure
- `CodeVaultV1/`: The main application code (The Body).
- `.agent/`: Context, memory, and rules (The Brain).
- `docs/`: Human-readable documentation.

# Decision Log

## Technical Decisions

### [2025-12-23] Workflow Upgrade
- **Context:** User requested workflow improvements based on an AI audit.
- **Decision:** Implement "Meta-Code" separation (Agent vs. CodeVault), "Memory Bank", and Automated Security.
- **Reasoning:** To prevent "vibe drift" (loss of context) and improve security/quality in a solo "vibe coding" environment.
- **Implications:** Agents must now check `.agent/memory` before suggesting changes.

### [2025-12-23] Tool Selection
- **Context:** Improving dev tooling.
- **Decision:** Adopt GitButler (Windows), Aider (CLI), Trivy (Security), Ruff (Python Linting), Biome (Node Linting).
- **Reasoning:** Best-in-class tools for rapid iteration ("vibe coding") while maintaining safety rails.
- **Implications:** `CONTRIBUTING.md` updated to reflect these recommendations.

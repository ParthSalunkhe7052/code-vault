# Tech Context

## Stack Definitions
This project uses a specific stack. **Do not suggest alternatives unless explicitly requested.**

### Backend (The Body)
- **Language:** Python
- **Framework:** FastAPI
- **Database:** SQLite (local), potentially migrated to Postgres later.
- **Payment:** Stripe API (Latest Version).
- **Security:** CodeQL, Trivy.

### Frontend
- **Language:** JavaScript/Node.js (for CLI/Compiler wrappers).
- **Framework:** React (if applicable for dashboard).

### Development Patterns
- **Linting:** Ruff (Python), Biome (Node).
- **Testing:** Pytest.
- **Documentation:** Markdown in `docs/` and `artifacts/`.

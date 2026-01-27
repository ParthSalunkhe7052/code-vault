# Technology Stack

## Backend
- **Core:** Python 3.12, FastAPI
- **Database:** SQLAlchemy ORM with PostgreSQL
- **Caching & Queueing:** Redis

## Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS

## CLI & Protection
- **CLI Framework:** Typer
- **Compiler:** Nuitka (translating Python to C/Machine Code)
- **Security:** Hardware ID (HWID) binding logic

## Infrastructure
- **Containerization:** Docker (used for isolated build environments)
- **Storage:** Cloudflare R2 (for storing compiled binaries and artifacts)
- **Deployment:** Vercel (frontend) and potentially self-hosted or cloud providers for backend/workers

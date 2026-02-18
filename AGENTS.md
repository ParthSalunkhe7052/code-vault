# CodeVault

Infrastructure platform for Independent Software Vendors (ISVs) and Python/Node.js developers to securely license, protect, and distribute desktop applications.

## Project Overview

CodeVault simplifies the transition from local scripts to commercial products by automating compilation, licensing, and payment integration.

**Target Audience:**
- Independent Software Vendors (ISVs)
- Python and Node.js developers monetizing their scripts

**Core Value Propositions:**
- Native Security: Python compiled to C/machine code via Nuitka
- Operational Convenience: All-in-one licensing and payment solution
- Deployment Flexibility: Cross-platform builds via cloud pipeline

## Technology Stack

### Backend
- Python 3.12, FastAPI
- SQLAlchemy ORM with PostgreSQL
- Redis for caching/queueing

### Frontend
- React 18 with TypeScript
- Vite build tool
- Tailwind CSS

### CLI & Protection
- Typer CLI framework
- Nuitka compiler (Python to C/Machine Code)
- HWID binding for security

### Infrastructure
- Docker containerization
- Cloudflare R2 storage
- Vercel deployment (frontend)

## Project Structure

```
cli/                    # CLI application
  codevault_cli/        # Main CLI commands
  generators/           # Code generators (Python/NodeJS)
  templates/            # License wrapper templates

server/                 # FastAPI backend
  routes/               # API endpoints
  compilers/            # Build orchestration
  models.py             # Database models

sdk/                    # Client SDKs
  python/               # Python SDK
  nodejs/               # NodeJS SDK

conductor/              # Project documentation
  tracks/               # Development tracks
  code_styleguides/     # Language-specific style guides
```

## Code Style

Reference: `conductor/code_styleguides/`

### Python
- Follow Google Python Style Guide
- Run `ruff check` for linting
- Use type hints for all public APIs
- Docstrings required for public functions

### TypeScript/React
- Use functional components with hooks
- Follow existing component patterns
- Use Tailwind CSS for styling

## Development Workflow

Detailed workflow: `conductor/workflow.md`

### Key Principles
1. Test-Driven Development (TDD) - write tests first
2. High code coverage (>80%)
3. Quality gates before merge
4. Non-interactive commands preferred (use `CI=true`)

### Testing Commands
```bash
# Run tests with coverage
pytest --cov=app --cov-report=html

# Lint Python code
ruff check .

# Type check
mypy .
```

### Commit Format
```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore
```

## Quality Gates

Before marking any task complete:
- [ ] All tests pass
- [ ] Code coverage >80%
- [ ] No linting errors
- [ ] Type safety enforced
- [ ] Documentation updated
- [ ] No security vulnerabilities

## Restricted Files

These files contain sensitive data and MUST NOT be read or modified:
- `.env`
- `.env.*`
- `credentials.json`
- `secrets.json`
- `*_secrets.py`
- SSL certificates and keys

## Key Commands

### Setup
```bash
pip install -e ./cli      # Install CLI locally
pip install -e ./sdk/python  # Install Python SDK
```

### Development
```bash
cd server && uvicorn main:app --reload  # Start backend
cd frontend && npm run dev               # Start frontend
```

### Build
```bash
codevault build           # Standard build
codevault build --fast    # Fast mode (directory output)
```

## Documentation References

- Product Definition: `conductor/product.md`
- Tech Stack Details: `conductor/tech-stack.md`
- Full Workflow: `conductor/workflow.md`
- Style Guides: `conductor/code_styleguides/`

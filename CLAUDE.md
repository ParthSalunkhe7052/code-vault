# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**CodeVault** is a Software Monetization Platform (SaaS) that wraps Python and Node.js applications with license protection and compiles them to standalone Windows executables.

### Architecture
```
CodeVaultV1/
├── frontend/         # React + Vite (Port 5173)
├── server/           # FastAPI backend (Port 8000)
├── cli/              # CLI compilation tools
├── tests/            # API and structure tests
└── docs/archive/     # Historical docs, inspections, plans
```

## Quick Commands

```bash
# Start full app (frontend + backend)
./Run Web App.bat

# Or manually:
cd server && python main.py          # Backend :8000
cd frontend && npm run dev           # Frontend :5173

# CLI
cd cli && python lw_compiler.py login
cd cli && python lw_compiler.py build

# Linting
python -m ruff check server/ --fix
cd frontend && npm run lint

# Tests
python -m pytest tests/
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.104+, asyncpg, Pydantic 2.5+, bcrypt, PyJWT |
| Frontend | React 18, Vite 5, TailwindCSS 3.4, Recharts, Leaflet |
| Database | PostgreSQL (Neon serverless) |
| Cache | Redis (Upstash) |
| Storage | Cloudflare R2 |
| Payments | Stripe |
| Email | Resend |
| Compilation | Nuitka (Python), pkg (Node.js) |

## Key Files

| Purpose | Location |
|---------|----------|
| API routes | `server/routes/*.py` |
| Database | `server/database.py` |
| Models | `server/models.py` |
| Config | `server/config.py` |
| HWID/Crypto | `server/utils.py` |
| API client | `frontend/src/services/api.js` |
| CLI entry | `cli/lw_compiler.py` |
| Wrappers | `cli/wrappers.py` |

## Code Patterns

### Backend Route Pattern
```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/api/v1/example")

@router.post("/endpoint")
async def handler(request: Model, api_key: str = Depends(verify_api_key)):
    # async database operations
    pass
```

### Frontend API Pattern
```javascript
// services/api.js - centralized API calls
const response = await fetch(`/api/v1${endpoint}`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

## Security Architecture

1. **JWT Authentication** - Bearer tokens with expiration
2. **HWID Binding** - Hardware fingerprinting (CPU, motherboard, disk)
3. **Offline Lease** - 7-day cached validation with HMAC signatures
4. **Nonce System** - Replay attack prevention (5-min window)
5. **Nuitka Compilation** - Python → C → machine code (no bytecode)

## Environment Variables

Required in `CodeVaultV1/.env`:
```
DATABASE_URL=postgresql://...
SECRET_KEY=...
JWT_SECRET=...
R2_BUCKET_NAME=...
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
RESEND_API_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_PUBLISHABLE_KEY=...
```

## MCP Servers (Configured)

The project has MCP servers configured in `.mcp.json`:
- **filesystem** - File system access
- **postgres** - Database queries (uses DATABASE_URL)
- **github** - GitHub integration
- **context7** - Documentation fetching

Use `/mcp` in Claude Code to manage servers.

## Hooks (Configured)

Hooks are shell commands that run automatically at specific points:

| Hook | Trigger | Purpose |
|------|---------|---------|
| `PreToolUse` | Before Bash commands | Security check - blocks commits with secrets |
| `PostToolUse` | After Edit/Write | Auto-lint Python (Ruff) and JS (ESLint) |

### Hook Events Available
- **PreToolUse** - Before tool executes (can block)
- **PostToolUse** - After tool completes
- **UserPromptSubmit** - When user sends a message
- **SessionStart** - When session begins
- **Stop** - When Claude finishes responding

Config location: `.claude/settings.local.json`

## Known Issues (from CodeRabbitReview.md)

See `docs/archive/CodeRabbitReview.md` for tracked issues:
- Deprecated asyncio/datetime calls (mostly fixed)
- Storage service test uses invalid project ID
- Some test files have hardcoded values

## Development Notes

- Frontend proxies `/api` to `localhost:8000` via Vite config
- Database uses async connection pooling
- Build pipeline: Upload → Inject License → Obfuscate → Compile → R2 Storage
- CLI performs local compilation, uploads result to cloud

## Useful Claude Code Commands

```bash
# Ralph Wiggum - iterative debugging for complex bugs
/ralph-wiggum:ralph-loop

# View MCP server status
/mcp

# View configured hooks
/hooks

# Plan mode for complex features
# (Claude enters plan mode automatically for multi-step tasks)
```

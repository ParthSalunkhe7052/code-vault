# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**CodeVault** is a Software Monetization Platform (SaaS) that wraps Python and Node.js applications with license protection and compiles them to standalone Windows executables.

**Business Model**: Multi-tier SaaS platform where developers can:
1. Upload their Python/Node.js applications
2. Add license protection and hardware ID binding
3. Compile to standalone executables
4. Distribute protected software to end-users
5. Manage licenses, monitor usage, and prevent piracy

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

### License Protection System
1. **JWT Authentication** - Bearer tokens with expiration for API access
2. **HWID Binding** - Hardware fingerprinting (CPU, motherboard, disk) to bind licenses to specific machines
3. **Offline Lease** - 7-day cached validation with HMAC signatures for offline license verification
4. **Nonce System** - Replay attack prevention (5-min window) for all license validation requests
5. **Nuitka Compilation** - Python → C → machine code (no bytecode, reverse engineering protection)

### 🔴 CRITICAL SECURITY REQUIREMENTS

This platform compiles and executes user-submitted code. Security is paramount.

#### Code Upload & Storage Security
- **Validate all uploads**: Check file types, sizes, and structures
- **Sanitize filenames**: Prevent path traversal attacks (`../`, absolute paths)
- **Scan for malicious patterns**: Block obvious malware patterns before storage
- **Isolated storage**: Each user's code isolated in separate R2 buckets/folders
- **No direct execution**: Never run user code on main server - use isolated build workers

#### Build Worker Security (Docker)
- **Isolated containers**: Each build runs in fresh Docker container
- **Resource limits**: CPU, memory, time limits enforced
- **Network isolation**: No internet access during build (except allowlisted package registries)
- **Read-only mounts**: User code mounted read-only
- **Privileged operations**: No root access, no privileged flags
- **Cleanup**: Destroy container after build completion

#### License Wrapper Security
- **Input validation**: All license check inputs validated (HWID, nonce, timestamps)
- **Cryptographic signing**: All offline leases signed with HMAC-SHA256
- **Rate limiting**: Prevent brute force attacks on license endpoints
- **Secure key storage**: License keys encrypted at rest
- **Audit logging**: All license validations logged with context

#### API Security
- **Authentication required**: All endpoints except `/health` and `/register` require JWT
- **Authorization checks**: Verify user owns resource before access
- **Input validation**: Pydantic models validate all inputs
- **Rate limiting**: Per-user and per-IP rate limits
- **CORS**: Restricted to frontend domain only
- **SQL injection**: Use parameterized queries (asyncpg/Prisma handles this)
- **No sensitive data in errors**: Generic error messages to users, detailed logs server-side

#### Payment Security
- **Stripe webhooks**: Verify webhook signatures
- **No card storage**: Never store credit card data (Stripe handles PCI compliance)
- **Idempotency**: Prevent duplicate charges
- **Audit trail**: Log all payment events

#### Secret Management
- **Environment variables**: All secrets in `.env`, never in code
- **No hardcoding**: No API keys, passwords, or tokens in source code
- **Rotation**: Support secret rotation without downtime
- **Access control**: Database credentials limited to backend only

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

---

## Error Handling Conventions

### Backend Error Pattern
```python
from fastapi import HTTPException, status

# Use HTTPException for client errors
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

# Use try-except for expected failures
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Operation failed"
    )
```

### Error Response Format
All API errors should return:
```json
{
  "detail": "User-friendly error message"
}
```

### Error Logging
- Log all errors with context (user_id, action, request_id)
- Use different log levels appropriately:
  - `ERROR`: System errors, exceptions
  - `WARNING`: Expected failures, validation issues
  - `INFO`: Successful operations, state changes
  - `DEBUG`: Detailed debugging info (development only)
- Never log sensitive data (passwords, tokens, full API keys)

### Frontend Error Handling
```javascript
try {
  const data = await api.fetchData();
  setData(data);
} catch (error) {
  console.error('Fetch failed:', error);
  // Show user-friendly message
  toast.error(error.response?.data?.detail || 'Something went wrong');
}
```

---

## API Response Conventions

### Success Response
```python
# Single resource
return {"data": resource_dict}

# List of resources
return {"data": resource_list, "total": count}

# Operation with message
return {"message": "Operation successful", "data": result}
```

### HTTP Status Codes
- `200 OK` - Successful GET, PUT, PATCH, DELETE
- `201 Created` - Successful POST that creates a resource
- `204 No Content` - Successful DELETE with no response body
- `400 Bad Request` - Malformed request, invalid JSON
- `401 Unauthorized` - Missing or invalid authentication token
- `403 Forbidden` - Authenticated but lacks permission
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Validation failed, business logic error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Unexpected server error

---

## Code Style & Conventions

### Python (Backend/CLI)
- Follow PEP 8 style guide
- Use type hints for all function parameters and returns
- Use async/await for all I/O operations
- Prefer Pydantic models for validation
- Use descriptive variable names (no single letters except loops)
- Maximum line length: 100 characters
- Use Ruff for linting: `python -m ruff check --fix`

```python
# Good example
async def create_project(
    user_id: int,
    name: str,
    description: str | None = None
) -> Project:
    """Create a new project for the user.
    
    Args:
        user_id: The ID of the project owner
        name: Project name (3-50 characters)
        description: Optional project description
        
    Returns:
        The created Project object
        
    Raises:
        HTTPException: If user doesn't exist or name is taken
    """
    pass
```

### JavaScript/React (Frontend)
- Use ES6+ features (arrow functions, destructuring, etc.)
- Prefer functional components with hooks
- Use async/await instead of promises chains
- PropTypes or TypeScript for type safety
- Meaningful component and variable names
- Maximum line length: 100 characters
- Use ESLint: `npm run lint -- --fix`

```javascript
// Good example
const ProjectCard = ({ project, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  
  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteProject(project.id);
      onDelete(project.id);
    } catch (error) {
      toast.error('Failed to delete project');
    } finally {
      setIsDeleting(false);
    }
  };
  
  return (
    // JSX
  );
};
```

---

## Testing Requirements

### What to Test
- **Unit Tests**: Services, utilities, business logic
- **Integration Tests**: API endpoints with database
- **E2E Tests**: Critical user flows (register, create project, build)

### Backend Testing (pytest)
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project_success(client: AsyncClient, auth_token: str):
    """Test successful project creation."""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
```

### Test Coverage Goals
- Services: 80%+
- Routes: 70%+
- Utils: 90%+

Run tests: `python -m pytest tests/ -v --cov=server`

---

## Common Patterns

### Adding a New API Endpoint

1. **Define the Pydantic model** (`server/models.py`):
```python
class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str | None = None
```

2. **Create route handler** (`server/routes/project_routes.py`):
```python
@router.post("/projects")
async def create_project(
    request: CreateProjectRequest,
    api_key: str = Depends(verify_api_key)
):
    # Implementation
    pass
```

3. **Add to router** (in `server/main.py`):
```python
app.include_router(project_routes.router, prefix="/api/v1", tags=["projects"])
```

4. **Create frontend service** (`frontend/src/services/api.js`):
```javascript
export const createProject = async (projectData) => {
  const response = await fetch('/api/v1/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(projectData)
  });
  return handleResponse(response);
};
```

5. **Write tests** (`tests/test_api_endpoints.py`)

### Database Operations Pattern
```python
# Always use connection from pool
async with get_db_connection() as conn:
    # Use parameterized queries
    result = await conn.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
```

### Adding a New React Component
1. Create component file in appropriate folder
2. Define PropTypes or TypeScript interface
3. Implement component with proper state management
4. Export from index.js if needed
5. Add to parent component/page

---

## Protected Files (NEVER DELETE OR COMPLETELY OVERWRITE)

These files are critical to the project and should never be deleted or completely overwritten without explicit permission:

- `.env` and `.env.*` files (contain secrets)
- `server/config.py` (environment configuration)
- `server/database.py` (database connection pooling)
- `package.json` and `requirements.txt` (dependencies)
- `vite.config.js` and `tailwind.config.js` (build configuration)
- `.mcp.json` (MCP server configuration)
- Docker files (`Dockerfile`, `docker-compose.yml`)
- License wrapper templates (`cli/wrappers.py`, `cli/templates/`)

When modifying these files, make surgical changes, not full replacements.

---

## Performance Considerations

### Backend Performance
- Use connection pooling (already configured in `database.py`)
- Cache frequently accessed data in Redis
- Use database indexes on frequently queried columns
- Paginate large result sets
- Use async operations for all I/O

### Frontend Performance
- Lazy load routes with React Suspense
- Memoize expensive computations
- Debounce user inputs (search, filters)
- Optimize images and assets
- Use React.memo for expensive components

### Build Performance
- Build workers should timeout after 10 minutes
- Stream build logs instead of buffering
- Clean up build artifacts after upload
- Use Docker layer caching

---

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

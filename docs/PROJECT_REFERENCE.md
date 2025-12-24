# CodeVault - Project Reference

> **Last Updated:** December 24, 2025  
> **Purpose:** Single source of truth for AI agents and developers  
> **Status:** Production-ready with local development setup

---

## 📋 Quick Reference

### Project Status

| Component | Status | Completion |
|-----------|--------|------------|
| License Core Module | ✅ Complete | 100% |
| CLI Tool | ✅ Complete | 100% |
| Backend API Server | ✅ Complete | 100% |
| Frontend Dashboard | ✅ Complete | 95% |
| Nuitka Compilation (Python) | ✅ Complete | 100% |
| Node.js Compilation (pkg) | ✅ Complete | 90% |
| Security Features | ✅ Complete | 95% |
| Email Notifications | ✅ Complete | 100% |
| Cloud Storage (R2) | ✅ Complete | 100% |
| Tauri Desktop App | ✅ Complete | 90% |
| Docker Infrastructure | ❌ Not Implemented | 0% |

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.10+), SQLite/PostgreSQL |
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Desktop App** | Tauri 2.x (Rust) |
| **UI Icons** | Custom PNG icons |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Cache** | Redis (optional) |
| **Storage** | Local uploads (dev) / Cloudflare R2 (prod) |
| **Email** | Resend / SMTP |

---

## 🚀 How to Run

### Quick Start (Windows)

```powershell
# Just double-click this file:
Run Desktop App.bat

# This starts:
# - Backend on http://localhost:8000
# - Frontend on http://localhost:5173
# - Tauri desktop app
```

### Manual Start

```powershell
# Terminal 1: Backend
cd CodeVaultV1\server
..\..\venv\Scripts\activate
python main.py

# Terminal 2: Frontend
cd CodeVaultV1\frontend
npm run dev
```

### Login Credentials (Dev Mode)

| Email | Password |
|-------|----------|
| `demo@example.com` | `1234` |

---

## 📁 Project Structure

```
Code Vault/                         # YOUR ROOT DIRECTORY
├── .agent/                         # AI workflows (NOT pushed to git)
│   ├── memory/                     # Agent context files
│   │   ├── activeContext.md        # Current task state
│   │   └── techContext.md          # Tech stack constraints
│   └── workflows/
│       ├── architect.md            # Feature planning agent
│       ├── builder.md              # ⭐ Main building agent
│       ├── doctor.md               # Bug fixing agent
│       ├── inspector.md            # Code review agent
│       └── reality-check.md        # Market research agent
│
├── artifacts/                      # Task tracking (NOT pushed to git)
│   ├── bugs/                       # Bug tracking files
│   ├── features/                   # Feature implementation plans
│   └── inspections/                # Code review reports
│
├── docs/                           # Documentation
│   ├── PROJECT_DOCUMENTATION.md    # Full documentation
│   ├── PROJECT_REFERENCE.md        # This file
│   └── inspections/                # Inspection reports
│
├── CodeVaultV1/                    # ⭐ MAIN PROJECT (PUSH THIS TO GIT)
│   ├── cli/                        # CLI compiler tool
│   │   ├── lw_compiler.py          # Main CLI (Python + Node.js builds)
│   │   ├── lw-compiler.bat         # Windows launcher
│   │   ├── wrappers.py             # License wrapper code generators
│   │   └── README.md
│   ├── frontend/                   # React dashboard
│   │   └── src/
│   │       ├── components/         # UI components
│   │       ├── pages/              # Page components
│   │       └── services/           # API client
│   ├── server/                     # FastAPI backend
│   │   ├── main.py                 # Core endpoints
│   │   ├── routes/                 # Route modules (auth, license, etc.)
│   │   ├── compilers/              # Build orchestrator, Node.js compiler
│   │   ├── email_service.py
│   │   ├── storage_service.py
│   │   └── uploads/                # Uploaded project files
│   ├── src-tauri/                  # Tauri desktop app (Rust)
│   ├── tests/                      # Pytest tests
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── make_admin.py
│
├── .env                            # Environment variables (NOT in git)
├── .env.example                    # Template for .env
├── venv/                           # Python venv (NOT pushed to git)
├── Make Admin.bat                  # Helper scripts
├── Reset Password.bat
└── Run Desktop App.bat             # ⭐ Main launcher
```

## 🔐 Security: Sensitive Data Location

All sensitive data is stored at root level:

| Data | Location | In Git? |
|------|----------|---------|
| API Keys | `.env` | ❌ NO |
| Template | `.env.example` | ✅ YES |
| Database | `data/codevault.db` | ❌ NO |
| venv | `venv/` | ❌ NO |

---

## 🎨 Frontend Details

### Sidebar Navigation

| Route | Label | Icon File |
|-------|-------|-----------|
| `/` | Dashboard | `icon_dashboard.png` |
| `/projects` | Projects | `icon_projects.png` |
| `/licenses` | Access Keys | `icon_keys.png` |
| `/webhooks` | Webhooks | `icon_webhooks.png` |
| `/settings` | Settings | `icon_settings.png` |
| `/billing` | Billing | (Stripe integration) |

### Color Palette

```css
--background: #0a0f1a
--background-secondary: #111827
--primary: #6366f1 (Indigo)
--secondary: #10b981 (Emerald)
--accent: #06b6d4 (Cyan)
```

---

## 🔐 API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login, get JWT |
| `/api/v1/auth/me` | GET | Get current user |

### Projects

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/projects` | GET | List projects |
| `/api/v1/projects` | POST | Create project |
| `/api/v1/projects/{id}` | DELETE | Delete project |
| `/api/v1/projects/{id}/upload` | POST | Upload files |

### Licenses

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/licenses` | GET | List licenses |
| `/api/v1/licenses` | POST | Create license |
| `/api/v1/licenses/{id}/revoke` | POST | Revoke license |
| `/api/v1/license/validate` | POST | Validate license (client API) |

### Build

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/build/prerequisites` | GET | Check build tools available |
| `/api/v1/build/installer` | POST | Start installer build job |
| `/api/v1/build/installer/{job_id}/status` | GET | Get build status |

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure:

### Required

```env
SECRET_KEY=<64-char random string>
JWT_SECRET=<64-char random string>
DATABASE_URL=sqlite:///./data/codevault.db
```

### Optional

```env
# Email (Resend)
EMAIL_ENABLED=true
RESEND_API_KEY=re_...

# Cloud Storage (Cloudflare R2)
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
R2_ENDPOINT=...

# Billing (Stripe)
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## 🤖 AI Agent Workflows

| Command | Agent | Purpose |
|---------|-------|---------|
| `/architect` | Feature Architect | Plans features before coding |
| `/builder` | ⭐ **The Builder** | Main agent for implementation |
| `/doctor` | Code Doctor | Fixes bugs, optimizes code |
| `/inspector` | Code Inspector | Reviews code, creates reports |
| `/reality-check` | Reality Check | Market fit and tech debt analysis |
| `/git-commander` | Git Commander | Version control, squashing, releases |

---

## 📞 Quick Commands

```powershell
# Start everything (recommended)
.\Run Desktop App.bat

# Backend only
cd CodeVaultV1\server
..\..\venv\Scripts\activate
python main.py

# Frontend only
cd CodeVaultV1\frontend
npm run dev

# Run linting
cd CodeVaultV1
ruff check .               # Python
cd frontend && npm run lint  # JavaScript

# Run tests
cd CodeVaultV1
python -m pytest tests/ -v
```

---

## 🚀 Git Workflow

```powershell
cd CodeVaultV1
git add .
git commit -m "Your message"
git push
```

**Only `CodeVaultV1/` folder contents are pushed!**
Sensitive data in `.env`, `venv/`, `data/` stays local.

---

> **Note:** This file was last updated on December 24, 2025.

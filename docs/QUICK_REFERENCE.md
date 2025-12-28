# Quick Reference Guide

## 🚀 Running the Stack

**Start All Services:**
Double-click `Run Web App.bat`

**Start CLI Tool:**
Double-click `Run CLI.bat`

## 📁 Key File Locations

| Component | Location | Details |
|-----------|----------|---------|
| **Backend Config** | `CodeVaultV1/server/config.py` | Settings & Constants |
| **Routes** | `CodeVaultV1/server/routes/` | API Endpoints |
| **CLI logic** | `CodeVaultV1/cli/lw_compiler.py` | Build Orchestration |
| **Wrappers** | `CodeVaultV1/cli/wrappers.py` | Injection Code (Python/Node) |
| **Frontend** | `CodeVaultV1/frontend/src/` | React App |

## 🛠️ Common Commands

### Backend Development
```bash
cd CodeVaultV1/server
../../venv/Scripts/activate
python main.py
```

### Frontend Development
```bash
cd CodeVaultV1/frontend
npm run dev
```

### CLI Development
```bash
cd CodeVaultV1/cli
../../venv/Scripts/activate
python lw_compiler.py status
```

## 🔧 Environment Variables (`.env`)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string |
| `SECRET_KEY` | Flask/FastAPI session secret |
| `JWT_SECRET` | For signing auth tokens |
| `OFFLINE_LEASE_SECRET` | For signing offline leases (CRITICAL) |
| `RESEND_API_KEY` | For sending emails |

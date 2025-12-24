# CodeVault (License Wrapper) - Complete Project Documentation

> **Version:** 1.1.0  
> **Last Updated:** December 24, 2025  
> **Status:** Production-Ready (Python + Node.js)

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Core Features](#-core-features)
3. [Architecture](#-architecture)
4. [Technology Stack](#-technology-stack)
5. [Project Structure](#-project-structure)
6. [Getting Started](#-getting-started)
7. [Core Components](#-core-components)
8. [API Reference](#-api-reference)
9. [CLI Tool](#-cli-tool)
10. [Desktop Application](#-desktop-application)
11. [Security & License Protection](#-security--license-protection)
12. [Deployment](#-deployment)
13. [Development Workflows](#-development-workflows)
14. [Use Cases](#-use-cases)
15. [Troubleshooting](#-troubleshooting)

---

## 🎯 Project Overview

**CodeVault** (formerly License Wrapper) is a comprehensive **Software Monetization Platform** designed to help Python developers convert their scripts into commercial, license-protected software products. The platform automates the complex process of code protection, license management, and executable compilation.

### What Problem Does It Solve?

For Python developers selling desktop software, there are three major challenges:
1. **Code Protection**: Python scripts can be easily decompiled
2. **License Management**: Manually managing licenses is tedious
3. **Distribution**: Delivering professional executables to customers

CodeVault solves all three by providing:
- **Automated Nuitka compilation** (Python → C → machine code)
- **Built-in license validation** with HWID locking
- **Web dashboard** for managing customers and licenses
- **Cloud compilation** without local setup
- **CLI tools** for local compilation

### Who Is It For?

- **Freelancers** selling Python automation scripts to clients
- **B2B SaaS developers** distributing desktop tools
- **Independent developers** monetizing Python applications
- **Software vendors** needing license protection

---

## ✨ Core Features

### 🔐 License Protection System
- **Hardware ID (HWID) Locking**: Binds licenses to specific machines using CPU, motherboard, and disk identifiers
- **Heartbeat Validation**: Periodic license checks with configurable intervals
- **Offline Grace Period**: Cached validation with configurable offline tolerance (default 24 hours)
- **Replay Attack Prevention**: Cryptographic nonces and HMAC-SHA256 signatures
- **Multi-Machine Support**: Licenses can support 1-100 machines
- **Expiration Management**: Time-based license expiration
- **Instant Revocation**: Remotely revoke licenses in real-time

### 🔨 Compilation Engine
- **Nuitka Integration**: Compiles Python to native executables
- **Cloud Compilation**: Compile without installing Nuitka locally
- **Local Compilation**: CLI tool for offline builds
- **Multi-Folder Projects**: Support for complex project structures
- **Dependency Management**: Automatic package detection and bundling
- **Custom Build Options**: Configure Nuitka parameters via UI
- **Cross-Platform**: Windows, Linux, macOS support (Windows-optimized)

### 📊 Web Dashboard
Beautiful React-based interface with:
- **Dashboard**: Overview of activity, licenses, and compilations
- **Project Management**: Upload, configure, and manage projects
- **License Management**: Create, monitor, and revoke licenses
- **Build Settings**: Configure compilation parameters
- **Webhooks**: Integration with external systems
- **Admin Panel**: User management and system configuration
- **Real-Time Stats**: Active machines, validation counts, recent activity

### 📧 Automation Features
- **Email Notifications**: Automatic emails on license creation/revocation (Resend/SMTP)
- **Webhook Events**: Trigger external systems on license validation, creation, compilation
- **File Storage**: Local uploads or Cloudflare R2 cloud storage
- **API Keys**: Generate and manage API keys for programmatic access

### 🛠️ CLI Compiler Tool
Standalone tool for developers:
- Login with API credentials
- List projects and licenses
- Build projects locally with Nuitka
- Interactive build mode
- Embed licenses into executables

### 🖥️ Desktop Application (Tauri)
Native desktop app (Windows/Mac/Linux) for:
- Running the server locally
- Managing projects without browser
- Offline-first workflow

---

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
├──────────────┬──────────────────┬──────────────┬────────────────┤
│              │                  │              │                │
│   Web UI     │   Desktop App    │   CLI Tool   │  Client Apps  │
│  (React)     │    (Tauri)       │ (lw-compiler)│  (.exe files) │
│              │                  │              │                │
└──────┬───────┴────────┬─────────┴──────┬───────┴───────┬────────┘
       │                │                │               │
       │                │                │               │
       └────────────────┴────────────────┘               │
                        │                                │
                        ▼                                │
┌────────────────────────────────────────────────────────┼────────┐
│                   BACKEND API SERVER                   │        │
│                    (FastAPI)                           │        │
│  ┌──────────────────────────────────────────────────┐ │        │
│  │  Auth • Projects • Licenses • Compilation Jobs   │ │        │
│  │  Webhooks • Email • Storage • Admin Tools        │ │        │
│  └──────────────────────────────────────────────────┘ │        │
└────────┬───────────────────┬───────────────────┬──────┘        │
         │                   │                   │               │
         ▼                   ▼                   ▼               │
┌─────────────────┐  ┌──────────────┐  ┌────────────────┐       │
│   PostgreSQL    │  │    Redis     │  │  File Storage  │       │
│   (Database)    │  │   (Cache)    │  │   (R2/Local)   │       │
└─────────────────┘  └──────────────┘  └────────────────┘       │
                                                                  │
                        LICENSE VALIDATION                        │
                                ▲                                 │
                                │                                 │
                                └─────────────────────────────────┘
```

### Component Interaction Flow

```
1. DEVELOPER WORKFLOW
   Developer → Web UI → Upload Project
                     ↓
            Configure Build Settings
                     ↓
            Generate License Key
                     ↓
            Compile (Cloud or Local)
                     ↓
            Download Protected .exe

2. END-USER WORKFLOW
   End User → Runs .exe
                  ↓
         License validation request (embedded)
                  ↓
         Backend validates HWID + License
                  ↓
         Returns: valid/invalid/expired
                  ↓
         App runs or exits
```

---

## 🔧 Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| **API Framework** | FastAPI | Latest |
| **Language** | Python | 3.10+ |
| **Database** | PostgreSQL | 14+ (SQLite for dev) |
| **Cache** | Redis | Optional |
| **ORM** | asyncpg | Direct queries |
| **Auth** | JWT | PyJWT |
| **Email** | Resend API | / SMTP |
| **Storage** | Cloudflare R2 / Local | boto3 |
| **Compilation** | Nuitka | 2.0+ |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | React | 18.x |
| **Build Tool** | Vite | 5.x |
| **Styling** | Tailwind CSS | 3.x |
| **Routing** | React Router | 6.x |
| **HTTP Client** | Fetch API | Native |
| **State** | React Context | Native |
| **Icons** | Custom PNG | - |

### Desktop App
| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | Tauri | 2.x |
| **Language** | Rust | Latest |
| **Frontend** | React (same as web) | 18.x |

### CLI Tool
| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.9+ |
| **HTTP** | requests | Latest |
| **Compilation** | Nuitka | 2.0+ |

---

## 📁 Project Structure

```
License Wrapper/
│
├── CodeVaultV1/              # 🎯 MAIN PROJECT (Git Repository)
│   │
│   ├── server/                    # Backend API
│   │   ├── main.py                # All API endpoints (3090 lines)
│   │   ├── database.py            # PostgreSQL connection pool
│   │   ├── models.py              # Pydantic models
│   │   ├── config.py              # Configuration
│   │   ├── email_service.py       # Email notifications (Resend/SMTP)
│   │   ├── storage_service.py     # File storage (R2/Local)
│   │   ├── utils.py               # Helper functions
│   │   ├── requirements.txt       # Python dependencies
│   │   └── uploads/               # Uploaded project files
│   │
│   ├── frontend/                  # Web Dashboard
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.jsx          # Main dashboard
│   │   │   │   ├── Projects.jsx           # Project management
│   │   │   │   ├── Licenses.jsx           # License management
│   │   │   │   ├── BuildSettings.jsx      # Compilation settings
│   │   │   │   ├── Webhooks.jsx           # Webhook configuration
│   │   │   │   ├── Settings.jsx           # User settings
│   │   │   │   ├── Login.jsx              # Authentication
│   │   │   │   └── AdminDashboard.jsx     # Admin panel
│   │   │   │
│   │   │   ├── components/        # Reusable UI components
│   │   │   ├── contexts/          # React contexts
│   │   │   ├── services/          # API client
│   │   │   ├── assets/            # Images and icons
│   │   │   ├── App.jsx            # Main app component
│   │   │   ├── main.jsx           # Entry point
│   │   │   └── index.css          # Global styles
│   │   │
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   └── index.html
│   │
│   ├── cli/                       # CLI Compiler Tool
│   │   ├── lw_compiler.py         # Main CLI tool (757 lines)
│   │   ├── lw-compiler.bat        # Windows launcher
│   │   └── README.md              # CLI documentation
│   │
│   ├── src-tauri/                 # Desktop App (Tauri)
│   │   ├── src/                   # Rust backend
│   │   ├── Cargo.toml             # Rust dependencies
│   │   ├── tauri.conf.json        # Tauri configuration
│   │   └── icons/                 # App icons
│   │
│   ├── pyproject.toml             # Python package config
│   ├── requirements.txt           # Python dependencies
│   ├── README.md                  # Main README
│   ├── make_admin.py              # Admin creation script
│   ├── reset_password.py          # Password reset script
│   └── .gitignore
│
├── data/                          # 🔒 SENSITIVE (NOT in Git)
│   ├── .env                       # Environment variables
│   └── license_wrapper.db         # SQLite database (dev)
│
├── docs/                          # 📚 Documentation
│   ├── PROJECT_DOCUMENTATION.md   # This file
│   ├── PROJECT_REFERENCE.md       # Quick reference
│   ├── reality-check/             # Market analysis
│   └── inspections/               # Code reviews
│
├── .agent/                        # 🤖 AI Workflows (NOT in Git)
│   └── workflows/
│       ├── architect.md           # Feature planning
│       ├── builder.md             # Implementation
│       ├── doctor.md              # Bug fixing
│       ├── inspector.md           # Code review
│       └── reality-check.md       # Market research
│
├── test_projects/                 # Test projects
│   └── test3_fullstack/           # Full-stack test app
│
├── venv/                          # Python virtual environment
│
└── Batch Files:
    ├── Run Desktop App.bat        # Start Tauri app + backend + frontend
    ├── Make Admin.bat             # Create admin user
    └── Reset Password.bat         # Reset user password
```

---

## 🚀 Getting Started

### Prerequisites

**Required:**
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (or use SQLite for dev)

**Optional:**
- Redis (for caching)
- Nuitka (for local compilation)
- Rust (for Tauri desktop app)

### Quick Start (Windows)

1. **Clone the repository:**
```powershell
git clone https://github.com/YOUR_USERNAME/license-wrapper.git
cd license-wrapper
```

2. **Setup environment:**
```powershell
# Create Python virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
cd CodeVaultV1
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

3. **Configure environment variables:**
Create `data/.env` file:
```env
# Required
SECRET_KEY=your-64-char-random-string-here
JWT_SECRET=another-64-char-random-string-here
DATABASE_URL=sqlite:///../../data/license_wrapper.db
ADMIN_EMAIL=admin@example.com

# Optional
EMAIL_ENABLED=false
ENVIRONMENT=development
CORS_ALLOW_ALL=true
```

4. **Initialize database:**
```powershell
cd CodeVaultV1\server
python main.py
# Database auto-initializes on first run
```

5. **Start the application:**

**Option A: Web Mode (separate terminals)**
```powershell
# Terminal 1: Backend
cd CodeVaultV1\server
..\..\venv\Scripts\activate
python main.py
# Backend runs on http://localhost:8000

# Terminal 2: Frontend  
cd CodeVaultV1\frontend
npm run dev
# Frontend runs on http://localhost:5173
```

**Option B: Desktop App Mode**
```powershell
# Run the batch file:
.\Run Desktop App.bat
# Starts backend + frontend + Tauri app
```

6. **Create first user:**
```powershell
# Visit http://localhost:5173
# Click "Register" and create account
# Or use the CLI:
python CodeVaultV1\make_admin.py
```

7. **Login:**
- Email: Your registered email
- Password: Your password
- Or use demo credentials (if configured):
  - Email: `demo@example.com`
  - Password: `1234`

---

## 🔧 Core Components

### 1. Backend API Server (`server/main.py`)

**Size:** 3,090 lines  
**Framework:** FastAPI  
**Key Functions:** 96+ endpoints

#### Main Modules:

**Authentication & Users:**
- User registration with email validation
- JWT-based authentication
- Password hashing (bcrypt)
- API key generation
- Admin user management

**Project Management:**
- Create/read/update/delete projects
- Upload project files (single file or ZIP)
- Multi-folder project support
- Project configuration (entry file, output name, Nuitka options)
- File size validation (100MB limit)
- Bundle generation for CLI downloads

**License Management:**
- Generate license keys (customizable format)
- HWID binding
- Multi-machine support (1-100 machines)
- License validation endpoint (public API)
- Revocation with email notifications
- HWID reset functionality
- License statistics and history

**Compilation Jobs:**
- Cloud compilation via API
- Nuitka parameter configuration
- Real-time progress tracking
- Build logs and error reporting
- Compiled binary storage and download

**Webhooks:**
- Create/manage webhook endpoints
- Event triggers: `license.validated`, `license.created`, `license.revoked`, `compilation.completed`
- HMAC-SHA256 signature verification
- Webhook delivery tracking
- Test webhook functionality

**Email Service:**
- License creation notifications
- License revocation notifications
- Welcome emails
- Customizable templates
- Resend API or SMTP

**Storage Service:**
- Local file uploads
- Cloudflare R2 integration
- Automatic cleanup of old builds
- Pre-signed download URLs

#### Database Schema:

**Tables:**
```sql
users: id, email, password_hash, name, api_key, is_admin, created_at

projects: id, user_id, name, description, settings (JSON), 
          entry_file, output_name, created_at

licenses: id, license_key, project_id, user_id, client_name, 
          client_email, status, expires_at, max_machines, 
          features (JSON), notes, created_at

license_validations: id, license_id, hwid, machine_name, 
                     ip_address, client_version, validated_at

compile_jobs: id, project_id, user_id, status, progress, 
              output_filename, error_message, logs (JSON), 
              started_at, completed_at, created_at

webhooks: id, user_id, name, url, events (JSON), secret, 
          is_active, created_at

webhook_deliveries: id, webhook_id, event_type, payload (JSON), 
                    response_status, response_body, delivered_at
```

### 2. Frontend Dashboard (`frontend/`)

**Framework:** React 18 + Vite  
**Styling:** Tailwind CSS  
**Pages:** 8

#### Page Breakdown:

**Dashboard** (`Dashboard.jsx`)
- License statistics (total, active, expired, revoked)
- Recent activity feed
- Active machines count
- Compilation job status
- Quick actions

**Projects** (`Projects.jsx`)
- Grid view of all projects
- Create new project
- Upload files (drag & drop)
- Configure project settings
- Delete projects
- Navigate to compilation

**Licenses** (`Licenses.jsx`)
- License table with search/filter
- Create new license
- View license details
- Revoke licenses
- Reset HWID
- Export license data

**Build Settings** (`BuildSettings.jsx`)
- Select entry file
- Configure output name
- Include/exclude packages
- Advanced Nuitka options
- License embedding
- Start compilation
- Download compiled binary

**Webhooks** (`Webhooks.jsx`)
- Create webhook endpoints
- Select event types
- Test webhooks
- View delivery history
- Enable/disable webhooks

**Settings** (`Settings.jsx`)
- User profile management
- API key generation
- Password change
- Email preferences

**Login** (`Login.jsx`)
- Email/password authentication
- Registration form
- Password reset

**Admin Dashboard** (`AdminDashboard.jsx`)
- User management
- System statistics
- Database health
- Email service status

#### Design System:

**Colors:**
```css
--background: #0a0f1a (Dark navy)
--background-secondary: #111827 (Slightly lighter)
--primary: #6366f1 (Indigo)
--secondary: #10b981 (Emerald green)
--accent: #06b6d4 (Cyan)
--text-primary: #f9fafb (Off-white)
--text-secondary: #9ca3af (Gray)
```

**Typography:**
- Primary: System fonts
- Headings: Bold, large sizes
- Body: Regular weight

**Layout:**
- Sidebar navigation (left)
- Main content area (center-right)
- Responsive design (mobile-friendly)

### 3. CLI Compiler Tool (`cli/lw_compiler.py`)

**Size:** 757 lines  
**Language:** Python  
**Purpose:** Local compilation without cloud

#### Commands:

```bash
lw-compiler login              # Login with email/password
lw-compiler logout             # Clear credentials
lw-compiler projects           # List your projects
lw-compiler licenses <id>      # List licenses for project
lw-compiler build <id> -l KEY  # Build with license
lw-compiler build              # Interactive build mode
lw-compiler status             # Check environment
```

#### Features:

- **Login System:** JWT authentication with API
- **Project Selection:** Interactive mode or specify ID
- **License Embedding:** Automatically inject license wrapper
- **Nuitka Execution:** Runs Nuitka locally with progress output
- **Bundle Download:** Downloads project ZIP from server
- **Self-Contained:** No external dependencies except `requests`
- **Color Output:** Beautiful terminal UI with ANSI colors

#### Usage Example:

```bash
# 1. Login
lw-compiler login
# Enter email: developer@example.com
# Enter password: ********
# ✅ Logged in as Developer (developer@example.com)

# 2. List projects
lw-compiler projects
# 1. My Python App (abc123...)
# 2. Automation Tool (def456...)

# 3. Build interactively
lw-compiler build
# Select project: 1
# Select license: 1. LIC-XXXX-XXXX (Client Name)
# ⚙️ Compiling with Nuitka...
# ✅ BUILD SUCCESSFUL!
# Output: output/MyPythonApp.exe
```

### 4. Desktop Application (`src-tauri/`)

**Framework:** Tauri 2.x  
**Language:** Rust + React  
**Purpose:** Native desktop experience

#### Features:

- **Native Window:** System-integrated UI
- **Backend Integration:** Runs FastAPI server
- **Offline Mode:** Works without internet
- **Auto-Updates:** Built-in update mechanism
- **Platform Support:** Windows, macOS, Linux

#### Configuration (`tauri.conf.json`):

```json
{
  "productName": "CodeVault",
  "identifier": "com.codevault.app",
  "bundle": {
    "targets": ["msi", "nsis"],
    "category": "DeveloperTool"
  },
  "app": {
    "windows": [{
      "title": "CodeVault - License Management",
      "width": 1200,
      "height": 800
    }]
  }
}
```

---

## 📡 API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication

All authenticated endpoints require JWT token in header:
```http
Authorization: Bearer <jwt_token>
```

### Endpoints

#### Auth & Users

**Register User**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "John Doe"
}

Response 200:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Login**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response 200: (Same as register)
```

**Get Current User**
```http
GET /auth/me
Authorization: Bearer <token>

Response 200:
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "api_key": "cvk_...",
  "is_admin": false
}
```

#### Projects

**List Projects**
```http
GET /projects
Authorization: Bearer <token>

Response 200:
[
  {
    "id": "uuid",
    "name": "My Python App",
    "description": "Automation tool",
    "created_at": "2025-12-16T12:00:00Z",
    "settings": {
      "is_multi_folder": false,
      "entry_file": "main.py"
    }
  }
]
```

**Create Project**
```http
POST /projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Project",
  "description": "Project description"
}

Response 201:
{
  "id": "uuid",
  "name": "New Project",
  ...
}
```

**Upload Project Files**
```http
POST /projects/{project_id}/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

files: [File, File, ...]

Response 200:
{
  "message": "Files uploaded successfully",
  "files": ["main.py", "utils.py"]
}
```

**Delete Project**
```http
DELETE /projects/{project_id}
Authorization: Bearer <token>

Response 200:
{
  "message": "Project deleted successfully"
}
```

#### Licenses

**Create License**
```http
POST /licenses
Authorization: Bearer <token>
Content-Type: application/json

{
  "project_id": "uuid",
  "client_name": "Client Corp",
  "client_email": "client@example.com",
  "expires_at": "2026-12-31T23:59:59Z",
  "max_machines": 3,
  "features": ["feature1", "feature2"],
  "notes": "Special client"
}

Response 201:
{
  "id": "uuid",
  "license_key": "LIC-XXXX-XXXX-XXXX",
  "project_id": "uuid",
  "status": "active",
  ...
}
```

**Validate License** (Public - No Auth Required)
```http
POST /license/validate
Content-Type: application/json

{
  "license_key": "LIC-XXXX-XXXX-XXXX",
  "hwid": "a1b2c3d4...",
  "machine_name": "DESKTOP-ABC123",
  "nonce": "random_string_16+",
  "timestamp": 1702834567,
  "client_version": "1.0.0"
}

Response 200:
{
  "status": "valid",
  "message": "License valid",
  "expires_at": 1735689599,
  "features": ["feature1"],
  "client_nonce": "...",
  "server_nonce": "...",
  "timestamp": 1702834567,
  "signature": "hmac_signature..."
}
```

**Revoke License**
```http
POST /licenses/{license_id}/revoke
Authorization: Bearer <token>

Response 200:
{
  "message": "License revoked successfully"
}
```

**Reset HWID**
```http
POST /licenses/{license_id}/reset-hwid
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Customer changed hardware"
}

Response 200:
{
  "message": "HWID reset successfully"
}
```

#### Compilation

**Start Compilation Job**
```http
POST /projects/{project_id}/compile
Authorization: Bearer <token>
Content-Type: application/json

{
  "entry_file": "main.py",
  "output_name": "MyApp",
  "license_key": "LIC-XXXX-XXXX-XXXX",
  "options": {
    "include_packages": ["module1", "module2"]
  }
}

Response 202:
{
  "id": "job_uuid",
  "project_id": "uuid",
  "status": "pending",
  "progress": 0
}
```

**Get Compilation Status**
```http
GET /compile-jobs/{job_id}
Authorization: Bearer <token>

Response 200:
{
  "id": "job_uuid",
  "status": "completed",
  "progress": 100,
  "output_filename": "MyApp.exe",
  "logs": [...],
  "completed_at": "2025-12-16T13:00:00Z"
}
```

**Download Compiled Binary**
```http
GET /compile-jobs/{job_id}/download
Authorization: Bearer <token>

Response 200:
(Binary file download: MyApp.exe)
```

#### Webhooks

**Create Webhook**
```http
POST /webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Webhook",
  "url": "https://example.com/webhook",
  "events": ["license.validated", "license.created"],
  "secret": "optional_secret_for_hmac"
}

Response 201:
{
  "id": "uuid",
  "name": "My Webhook",
  ...
}
```

**Test Webhook**
```http
POST /webhooks/{webhook_id}/test
Authorization: Bearer <token>

Response 200:
{
  "message": "Test webhook delivered",
  "status_code": 200
}
```

---

## 🛠️ CLI Tool

### Installation

**From PyPI (when published):**
```bash
pip install license-wrapper
lw-compiler --help
```

**Local Development:**
```bash
cd CodeVaultV1/cli
python lw_compiler.py --help
```

**Windows Shortcut:**
```bash
lw-compiler.bat
```

### Configuration

CLI stores config in `cli/config.json`:
```json
{
  "api_key": "eyJ...",
  "api_url": "http://localhost:8000/api/v1",
  "email": "user@example.com",
  "user_name": "John Doe"
}
```

### Full Workflow Example

```bash
# 1. Login
$ lw-compiler login
API URL [http://localhost:8000/api/v1]:
Login with your License Wrapper account:
Email: developer@example.com
Password: ********
✅ Logged in as Developer (developer@example.com)

# 2. Check status
$ lw-compiler status
✅ Logged in as: developer@example.com
✅ Nuitka: 2.0.0
✅ Python: 3.11.0

# 3. List projects
$ lw-compiler projects
  1. Python Automation Tool
     ID: abc123-def456-...
     Type: 📄 Single file

  2. Multi-Module App
     ID: xyz789-uvw012-...
     Type: 📁 Multi-folder

# 4. Build interactively
$ lw-compiler build

Select a project to build:
  1. Python Automation Tool (abc123...)
  2. Multi-Module App (xyz789...)

Enter number: 1

Select a license (or 0 for no license):
  0. No license (demo mode)
  1. LIC-A1B2-C3D4-E5F6 - ACME Corp
  2. LIC-G7H8-I9J0-K1L2 - Beta Testers

Enter number: 1

📋 Fetching project configuration...
   Project: Python Automation Tool
   Entry file: main.py
   Output: AutomationTool.exe
   License: LIC-A1B2-C3D4-E5F6

📥 Downloading project files...
   Extracted to: C:\Temp\...

🔐 Injecting license protection...
   Injected into: main.py

🔍 Checking Nuitka installation...
   Found: Nuitka 2.0.0

⚙️  Compiling with Nuitka...
   (This may take 2-10 minutes on first run)

   Nuitka: Starting compilation...
   Nuitka: Downloading dependencies...
   Nuitka: Compiling Python to C...
   Nuitka: Compiling C to binary...
   Nuitka: Packing executable...
   
==========================================================
  ✅ BUILD SUCCESSFUL!
==========================================================

  Output: output\AutomationTool.exe
  Size: 15.3 MB
  License: LIC-A1B2-C3D4-E5F6

# 5. Logout (optional)
$ lw-compiler logout
✅ Logged out successfully.
```

### License Injection

The CLI automatically injects this wrapper into your entry file:

```python
# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _lw_sys
import os as _lw_os
import hashlib as _lw_hash
import json as _lw_json
import time as _lw_time
import platform as _lw_platform

def _lw_get_hwid():
    """Generate hardware ID."""
    info = f"{_lw_platform.node()}|{_lw_platform.machine()}|{_lw_platform.processor()}"
    return _lw_hash.sha256(info.encode()).hexdigest()[:32]

def _lw_validate():
    """Validate license with server."""
    LICENSE_KEY = "LIC-XXXX-XXXX-XXXX"
    SERVER_URL = "http://localhost:8000"
    
    if LICENSE_KEY == "DEMO":
        print("[License Wrapper] Running in DEMO mode")
        return True
    
    # ... validation logic ...
    
# Validate on startup
_lw_validate()
# ============ END LICENSE WRAPPER ============

# YOUR ORIGINAL CODE STARTS HERE
import numpy as np
...
```

---

## 🖥️ Desktop Application

### Building the Desktop App

**Prerequisites:**
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Node.js dependencies
cd CodeVaultV1/frontend
npm install

# Install Tauri CLI
npm install -g @tauri-apps/cli
```

**Development Mode:**
```bash
cd CodeVaultV1
tauri dev
```

**Build Installer:**
```bash
cd CodeVaultV1
tauri build
# Outputs in src-tauri/target/release/bundle/
```

### Running the Desktop App

**Option 1: Batch File (Windows)**
```bash
.\Run Desktop App.bat
```

This script:
1. Starts the backend server
2. Starts the frontend dev server
3. Launches the Tauri window

**Option 2: Manual**
```bash
# Terminal 1: Backend
cd CodeVaultV1\server
..\..\venv\Scripts\activate
python main.py

# Terminal 2: Frontend (if not built)
cd CodeVaultV1\frontend
npm run dev

# Terminal 3: Tauri
cd CodeVaultV1
tauri dev
```

---

## 🔐 Security & License Protection

### How License Protection Works

```
┌─────────────────────────────────────────────────────────┐
│  1. DEVELOPER EMBEDS LICENSE                            │
│     • Uploads Python script to CodeVault               │
│     • Generates license key (e.g., LIC-A1B2-C3D4-E5F6) │
│     • Compiles with license embedded                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  2. END-USER RUNS EXECUTABLE                            │
│     • .exe starts                                       │
│     • License wrapper runs BEFORE user code             │
│     • Collects HWID (CPU, motherboard, disk)          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  3. LICENSE VALIDATION REQUEST                          │
│     POST /api/v1/license/validate                       │
│     {                                                   │
│       "license_key": "LIC-A1B2-C3D4-E5F6",             │
│       "hwid": "abc123...",                             │
│       "nonce": "random_string",                        │
│       "timestamp": 1702834567                          │
│     }                                                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  4. SERVER VALIDATES                                    │
│     ✅ License exists?                                  │
│     ✅ License active (not revoked)?                    │
│     ✅ Not expired?                                     │
│     ✅ HWID matches or is new (if under max_machines)? │
│     ✅ Nonce is fresh (prevent replay)?                │
│     ✅ Timestamp within 5 minutes?                     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  5. RESPONSE WITH SIGNATURE                             │
│     {                                                   │
│       "status": "valid",                               │
│       "signature": "HMAC-SHA256(...)"                  │
│     }                                                   │
│     • Client verifies signature                        │
│     • Caches result for offline grace period           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  6. USER CODE EXECUTES                                  │
│     • License valid → app runs normally                │
│     • License invalid → app exits with error           │
└─────────────────────────────────────────────────────────┘
```

### Security Features Explained

#### 1. **HWID (Hardware ID) Locking**
```python
def get_hwid():
    info = f"{platform.node()}|{platform.machine()}|{platform.processor()}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]
```
- Binds license to specific computer
- Prevents license sharing across machines
- Uses CPU info, motherboard, and disk identifiers
- Stored as SHA-256 hash (irreversible)

#### 2. **Replay Attack Prevention**
```python
nonce = hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]
timestamp = int(time.time())
```
- Every request includes unique nonce
- Server rejects duplicate nonces
- Timestamp must be within 5 minutes of server time
- Prevents attackers from replaying old "valid" responses

#### 3. **Response Signature Verification**
```python
def compute_signature(data, secret):
    payload = json.dumps(data, sort_keys=True)
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```
- Server signs every response with HMAC-SHA256
- Client verifies signature before trusting response
- Prevents man-in-the-middle attacks

#### 4. **Offline Grace Period**
- License validation cached locally
- Configurable grace period (default: 24 hours)
- Allows temporary offline use
- Expires after grace period

#### 5. **Nuitka Compilation**
```bash
python -m nuitka --standalone --onefile main.py
```
- Compiles Python → C → machine code
- No Python bytecode in final .exe
- Prevents decompilation with tools like uncompyle6
- Makes reverse engineering significantly harder

---

## 🚢 Deployment

### Local Development (Current Setup)

**Backend:**
- SQLite database (`data/license_wrapper.db`)
- Local file uploads (`server/uploads/`)
- No Redis (caching disabled)

**Frontend:**
- Vite dev server on port 5173
- Hot module replacement (HMR)

### Production Deployment (Recommended)

#### Option 1: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: license_wrapper
      POSTGRES_USER: lwuser
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build:
      context: ./CodeVaultV1
      dockerfile: Dockerfile.api
    environment:
      DATABASE_URL: postgresql://lwuser:secure_password@postgres/license_wrapper
      REDIS_URL: redis://redis:6379
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./CodeVaultV1/frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

```bash
docker-compose up -d
```

#### Option 2: Cloud Platforms

**Heroku:**
```bash
# Install Heroku CLI
heroku create license-wrapper

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Deploy
git push heroku main
```

**Railway.app:**
- Connect GitHub repo
- Add PostgreSQL plugin
- Set environment variables
- Deploy automatically

**DigitalOcean App Platform:**
- Import from GitHub
- Configure build settings
- Add managed PostgreSQL
- Deploy

### Environment Variables (Production)

```env
# Security
SECRET_KEY=<64-char-random-string>
JWT_SECRET=<64-char-random-string>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Cache
REDIS_URL=redis://host:6379

# Email
EMAIL_ENABLED=true
RESEND_API_KEY=re_...

# Storage
STORAGE_BACKEND=r2
R2_ENDPOINT_URL=https://...r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=license-wrapper

# App
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

### Database Migration

```bash
# Backup SQLite
cp data/license_wrapper.db data/backup_$(date +%Y%m%d).db

# Export to PostgreSQL
python scripts/migrate_to_postgres.py
```

---

## 🤖 Development Workflows

### AI Agent Workflows

Located in `.agent/workflows/`:

#### 1. `/architect` - Feature Planning
```markdown
Use this agent when:
- Planning new features
- Making design decisions
- Architecting solutions

Agent will:
- Ask clarifying questions
- Analyze existing code
- Create implementation plans
- Identify risks
```

#### 2. `/builder` - Implementation
```markdown
Use this agent when:
- Implementing features
- Writing new code
- Making code changes

Agent will:
- Follow implementation plans
- Write code
- Update documentation
- Test changes
```

#### 3. `/doctor` - Bug Fixing
```markdown
Use this agent when:
- Fixing bugs
- Optimizing code
- Refactoring

Agent will:
- Diagnose issues
- Fix bugs
- Improve performance
- Clean up code
```

#### 4. `/inspector` - Code Review
```markdown
Use this agent when:
- Reviewing code quality
- Checking for issues
- Auditing the project

Agent will:
- Perform read-only analysis
- Create inspection reports
- Identify problems
- Suggest improvements
```

#### 5. `/reality-check` - Market Analysis
```markdown
Use this agent when:
- Analyzing market viability
- Researching competitors
- Evaluating features

Agent will:
- Research market
- Analyze competitors
- Provide honest assessment
- Suggest pivots
```

### Development Commands

```bash
# Backend development
cd CodeVaultV1/server
..\..\venv\Scripts\activate
python main.py
# Auto-reloads on file changes

# Frontend development
cd CodeVaultV1/frontend
npm run dev
# Hot module replacement enabled

# Format code (Python)
cd CodeVaultV1
black server/
ruff check server/

# Format code (JavaScript)
cd frontend
npm run lint
npm run format

# Run tests (when available)
pytest tests/
```

---

## 💼 Use Cases

### Use Case 1: Freelancer Selling Python Automation

**Scenario:**  
Sarah is a freelancer who created a Python script that automates data entry for accountants. She wants to sell it to multiple clients without them sharing the script.

**How CodeVault Helps:**
1. Sarah uploads her script to CodeVault
2. She compiles it to `DataEntryPro.exe` (protects source code)
3. For each client, she creates a license key
4. Each license is locked to the client's computer (HWID)
5. If a client shares the .exe, it won't work on other computers
6. Sarah can revoke licenses if clients don't pay

### Use Case 2: B2B SaaS Desktop Tool

**Scenario:**  
TechCorp built a Python desktop app for enterprise customers. They need:
- License management for 100+ customers
- Multi-machine support (1 license = 5 computers)
- Time-based subscriptions (monthly/yearly)

**How CodeVault Helps:**
1. TechCorp integrates CodeVault API into their sales system
2. When a customer subscribes, API creates a license automatically
3. License supports 5 machines (configured via `max_machines`)
4. License expires after subscription period
5. TechCorp monitors usage via dashboard
6. Webhooks notify TechCorp's CRM when licenses are validated

### Use Case 3: Software Vendor with Local Compilation

**Scenario:**  
DevShop doesn't want to upload proprietary code to cloud. They need local compilation.

**How CodeVault Helps:**
1. DevShop runs CodeVault server on internal network
2. Uses CLI tool for local compilation: `lw-compiler build`
3. Nuitka runs on their machines (not cloud)
4. License validation still works (public API endpoint)
5. Source code never leaves their environment

### Use Case 4: Free Trial with Conversion

**Scenario:**  
ToolMaker wants to offer a 14-day free trial of their Python app.

**How CodeVault Helps:**
1. Create license with `expires_at` = 14 days from now
2. Set `client_email` = customer email
3. Email notification sent automatically with license key
4. After 14 days, license auto-expires
5. Customer contacts ToolMaker to purchase
6. ToolMaker creates new license (no expiration or yearly)
7. Customer receives new key, replaces old one

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "Database connection failed"
**Solution:**
```bash
# Check DATABASE_URL in data/.env
# For development, use SQLite:
DATABASE_URL=sqlite:///../../data/license_wrapper.db

# For production, ensure PostgreSQL is running:
psql -h localhost -U lwuser -d license_wrapper
```

#### Issue: "CORS error" in browser
**Solution:**
```env
# In data/.env:
CORS_ALLOW_ALL=true  # Development only!
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# In production:
CORS_ALLOW_ALL=false
CORS_ORIGINS=https://yourdomain.com
```

#### Issue: Nuitka compilation fails
**Solution:**
```bash
# Install Nuitka:
pip install nuitka

# Install C compiler (Windows):
# Download Visual Studio Build Tools
# Or install MinGW64

# Test Nuitka:
python -m nuitka --version
```

#### Issue: Email notifications not working
**Solution:**
```env
# Check data/.env:
EMAIL_ENABLED=true
RESEND_API_KEY=re_your_actual_key  # Get from resend.com

# Or use SMTP:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

#### Issue: File upload fails (file too large)
**Solution:**
```python
# In server/main.py, adjust:
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
# Increase if needed (e.g., 500MB):
MAX_UPLOAD_SIZE = 500 * 1024 * 1024
```

#### Issue: CLI can't connect to server
**Solution:**
```bash
# Check API URL:
lw-compiler login
# API URL [http://localhost:8000/api/v1]:
# Enter your server URL

# Ensure server is running:
curl http://localhost:8000/api/v1/health
# Should return: {"status": "ok"}
```

### Debug Mode

Enable verbose logging:

**Backend:**
```python
# server/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend:**
```javascript
// src/services/api.js
const DEBUG = true;
if (DEBUG) console.log('API call:', endpoint, data);
```

---

## 📚 Additional Resources

### Documentation Files
- [`README.md`](../CodeVaultV1/README.md) - Quick start guide
- [`PROJECT_REFERENCE.md`](PROJECT_REFERENCE.md) - Quick reference
- [`cli/README.md`](../CodeVaultV1/cli/README.md) - CLI documentation
- [`reality-check/reality_check_report.md`](reality-check/reality_check_report.md) - Market analysis

### External Links
- Nuitka Documentation: https://nuitka.net/doc/
- FastAPI Documentation: https://fastapi.tiangolo.com/
- React Documentation: https://react.dev/
- Tauri Documentation: https://tauri.app/

### Support
- GitHub Issues: (Your repo URL)
- Email: support@yourdomain.com
- Discord: (Your server invite)

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

Built with:
- FastAPI by Sebastián Ramírez
- React by Meta
- Nuitka by Kay Hayen
- Tauri by Tauri Programme
- Tailwind CSS by Tailwind Labs

---

**Last Updated:** December 16, 2025  
**Version:** 1.0.0  
**Project Status:** ✅ Production-Ready

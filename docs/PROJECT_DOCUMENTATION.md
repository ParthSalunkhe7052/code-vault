# CodeVault - Project Documentation

> **Version:** 1.2.0
> **Last Updated:** December 28, 2025
> **Status:** Production-Ready (Web + CLI Architecture)

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Core Features](#-core-features)
3. [Architecture](#-architecture)
4. [Security](#-security-&--license-protection)
5. [CLI Tool](#-cli-tool)
6. [API Reference](#-api-reference)

---

## 🎯 Project Overview

**CodeVault** is a software monetization platform for Python and Node.js developers. It transforms raw scripts into secure, licensed executables that can be sold to customers.

### The CodeVault Workflow

1.  **Upload & Configure**: Developer creates a project on the Web Dashboard.
2.  **Generate Licenses**: Developer creates license keys (e.g., `LIC-1234`) with specific constraints (expiration, max machines).
3.  **Compile & Protect**: Developer uses the **CLI Tool** locally to wrap the code with license validation logic and compile it into a unique `.exe`.
   - **Python** uses Nuitka (compiles to C).
   - **Node.js** uses `pkg` + `javascript-obfuscator`.
4.  **Distribute**: The `.exe` is sent to the customer.
5.  **Validate**: When the customer runs the app, it checks the license against the CodeVault server.

---

## ✨ Core Features

### 🔐 License Protection
- **Hardware ID (HWID) Locking**: Binds license to CPU, Disk, and Motherboard serials.
- **Heartbeat Checks**: Periodic validation while the app is running.
- **Tamper Detection**: Verifies integrity of the license wrapper.

### 🛡️ Offline Security (New in v1.2)
- **Offline Leases**: The server issues a cryptographically signed "lease" valid for a configurable period (default 7 days).
- **No Internet Required**: Once activated, the app can run offline until the lease expires.
- **HMAC Signatures**: The wrapper verifies the lease signature locally using a secret key embedded during compilation.

### 🕵️ Code Obfuscation (New in v1.2)
- **JavaScript**: Automatically applies control-flow flattening, string encryption, and dead code injection using `javascript-obfuscator`.
- **Python**: Compiled to native machine code via Nuitka, making decompilation extremely difficult.

### 🎨 White-Labeling (New in v1.2)
- **Splash Screen**: Professional "Protected by CodeVault" loading screen on startup.
- **Activation Dialog**: Branded GUI for entering license keys if missing or invalid.

---

## 🏗️ Architecture

CodeVault uses a **Web + CLI** hybrid architecture.

### 1. Backend Server (`server/`)
- **FastAPI**: High-performance async Python framework.
- **PostgreSQL**: Robust relational database for licenses and users.
- **Redis**: Caching layer for high-speed validation.
- **Stripe**: Payment processing for monetization.
- **Resend**: Email delivery service.

### 2. Web Dashboard (`frontend/`)
- **React + Vite**: Fast, modern frontend.
- **Tailwind CSS**: Professional styling.
- **Features**: License management, analytics, project configuration.

### 3. CLI Compiler (`cli/`)
- **Python-based**: Runs locally on the developer's machine.
- **Orchestrator**: Manages Nuitka/pkg, injection, and obfuscation.
- **Interactive**: Easy-to-use wizard for building projects.

---

## 🔐 Security & License Protection

### Validation Process
1.  **Startup**: Wrapper reads local license key.
2.  **Check Local Lease**: If valid offline lease exists and matches HWID, allow run.
3.  **Online Check**: If no lease or expired, contact server.
4.  **Server Verification**: Server checks Key + HWID + Expiration.
5.  **Lease Renewal**: If valid, server returns success + new signed offline lease.

### Anti-Cracking Measures
- **Nuitka Compilation**: Python bytecode is eliminated.
- **Obfuscation**: JS logic is scrambled.
- **String Encryption**: API URLs and secrets are not stored in plain text.
- **Debugger Detection**: (Coming Soon) Detects if app is being debugged.

---

## 🛠️ CLI Tool

The `lw-compiler` is the heart of the build process. It supports:
- **Local Compilation**: builds `.exe` files on your machine.
- **Obfuscation**: Automatically protects Node.js code.
- **Build Reporting**: Syncs build history to your Web Dashboard.

### Commands Reference

#### `lw-compiler login`
Log in to your CodeVault account and save credentials locally.

**Usage:**
```bash
lw-compiler login
```

**Interactive prompts:**
- Email address
- Password

**Environment variables:**
- `LW_API_URL` - Override the default API server URL

**Notes:**
- Credentials and configuration are stored in `~/.lw_cli_config.json`
- The API URL defaults to `http://localhost:8000/api/v1`

---

#### `lw-compiler logout`
Log out and clear saved credentials.

**Usage:**
```bash
lw-compiler logout
```

---

#### `lw-compiler status`
Display current login status, API configuration, and check dependencies.

**Usage:**
```bash
lw-compiler status
```

**Shows:**
- Login status and user email
- API server URL
- Nuitka version and availability
- Node.js version and availability
- Python version

---

#### `lw-compiler projects`
List all projects in your account.

**Usage:**
```bash
lw-compiler projects
```

**Output includes:**
- Project name
- Project ID
- Project type (single file or multi-folder)

---

#### `lw-compiler licenses <project_id>`
List all licenses for a specific project.

**Usage:**
```bash
lw-compiler licenses <project_id>
```

**Arguments:**
- `project_id` (required) - The unique identifier of the project

**Output includes:**
- License key
- Status (active/inactive)
- Client name (if set)
- Expiration date (if set)

---

#### `lw-compiler build [project_id] [options]`
Build a project into a license-protected executable. Supports both server-based and local file builds.

**Usage:**
```bash
# Interactive mode (prompts for project selection)
lw-compiler build

# Build specific project from server
lw-compiler build <project_id>

# Build with specific license key
lw-compiler build <project_id> --license <license_key>

# Build local file without server
lw-compiler build /path/to/script.py
lw-compiler build /path/to/app.js
```

**Arguments:**
- `project_id` (optional) - Project ID from server OR path to local file (.py or .js)
  - If omitted, enters interactive mode
  - If a file path, performs local build without server communication

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `-l, --license <key>` | License key to embed in the executable | Generic mode (executable prompts user) |
| `--generic` | Build in generic mode (prompts user for license at runtime) | false |
| `--open` | Build without any license protection | false |
| `--language <lang>` | Force language selection: `python` or `nodejs` | Auto-detect |
| `--output <path>` | Custom output path for the executable | Desktop/output folder |
| `--api-url <url>` | Override API URL (local build only) | From config |
| `--demo` | Build in demo mode (local build only) | false |
| `--demo-duration <mins>` | Demo duration in minutes (local build only) | 60 |

**Build Modes:**

1. **Fixed License Mode** (default with `--license`)
   ```bash
   lw-compiler build <project_id> --license ABC-123-XYZ
   ```
   The license key is embedded in the executable.

2. **Generic Mode** (with `--generic` or no `--license`)
   ```bash
   lw-compiler build <project_id> --generic
   ```
   The executable prompts the user for a license key at runtime.

3. **Open Build Mode** (with `--open`)
   ```bash
   lw-compiler build <project_id> --open
   ```
   No license protection is added.

4. **Local Build Mode** (file path instead of project_id)
   ```bash
   lw-compiler build /path/to/script.py --license ABC-123
   lw-compiler build /path/to/app.js --output ./dist/app.exe
   ```
   Builds a local file without fetching from the server.

**Examples:**

```bash
# Interactive build (prompts for project and license)
lw-compiler build

# Build with embedded license key
lw-compiler build abc-123-def-456 --license MY-LICENSE-KEY-123

# Build with runtime license prompt (generic mode)
lw-compiler build abc-123-def-456 --generic

# Build without license protection
lw-compiler build abc-123-def-456 --open

# Build local Python script with custom output
lw-compiler build ./my_script.py --license MY-KEY --output ./dist/app.exe

# Force Node.js build for .js file
lw-compiler build abc-123-def-456 --language nodejs

# Build local file in demo mode
lw-compiler build ./app.py --demo --demo-duration 30
```

**Build Process:**
1. Fetches project configuration from server (or uses local file)
2. Downloads project bundle (for server builds)
3. Extracts source files
4. Injects license protection wrapper
5. Compiles with Nuitka (Python) or pkg (Node.js)
6. Copies output to Desktop or specified path

**Output:**
- Default: `~/Desktop/<project_name>.exe` (Windows) or `~/OneDrive/Desktop/` if OneDrive is active
- Custom: Path specified with `--output` flag
- File size and license mode are displayed after successful build
- Note: The CLI currently targets Windows executables (.exe)

---

### Configuration
The CLI reads from `config.json` inside project folders, but can be overridden by flags.

**Config file location:** `~/.lw_cli_config.json`

**Config file format:**
```json
{
  "api_key": "your-jwt-token",
  "api_url": "http://localhost:8000/api/v1",
  "email": "your@email.com",
  "user_name": "Your Name"
}
```

---

## 📡 API Reference

Base URL: `http://localhost:8000/api/v1`

### Authentication

All management endpoints (except `/license/validate`) require JWT authentication.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

The JWT token is obtained during login and stored in `~/.lw_cli_config.json`.

---

### Validation Endpoint (Public)

**POST** `/license/validate`

Validates a license key and returns activation status.

**Request Body:**
```json
{
  "license_key": "LIC-XXXX-XXXX-XXXX-XXXX",
  "hwid": "hardware-identifier-string",
  "nonce": "random-nonce-string",
  "timestamp": 1234567890
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `license_key` | string | Yes | The license key to validate |
| `hwid` | string | Yes | Hardware identifier for machine binding |
| `nonce` | string | Yes | Random string for replay protection |
| `timestamp` | integer | Yes | Unix timestamp for request validation |

**Response (200 OK):**
```json
{
  "valid": true,
  "license_key": "LIC-XXXX-XXXX-XXXX-XXXX",
  "status": "active",
  "expires_at": "2025-12-31T23:59:59Z",
  "offline_lease": {
    "allowed": true,
    "duration_hours": 168,
    "lease_token": "base64-encoded-hmac-token"
  }
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid license key format"
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "License key not found or inactive"
}
```

**Response (403 Forbidden):**
```json
{
  "detail": "Hardware ID mismatch"
}
```

**Error Codes:**
- `400` - Invalid request format or missing required fields
- `401` - License key invalid, expired, or not found
- `403` - Hardware binding mismatch or license suspended
- `429` - Too many validation requests (rate limited)
- `500` - Internal server error

---

### Management Endpoints (Auth Required)

#### List Projects

**GET** `/projects`

Returns all projects for the authenticated user.

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "projects": [
    {
      "id": "abc-123-def-456",
      "name": "My Application",
      "type": "multi-folder",
      "created_at": "2024-01-15T10:30:00Z",
      "license_count": 5,
      "build_count": 12
    }
  ]
}
```

**Error Codes:**
- `401` - Invalid or expired authentication token
- `500` - Internal server error

---

#### List Licenses

**GET** `/licenses?project_id=<project_id>`

Returns all licenses for a specific project.

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | Yes | The project ID to fetch licenses for |

**Response (200 OK):**
```json
{
  "licenses": [
    {
      "id": "lic-uuid-1",
      "license_key": "LIC-XXXX-XXXX-XXXX-XXXX",
      "status": "active",
      "client_name": "John Doe",
      "expires_at": "2025-12-31T23:59:59Z",
      "hwid": "bound-hardware-id",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Error Codes:**
- `400` - Missing or invalid project_id parameter
- `401` - Invalid or expired authentication token
- `404` - Project not found
- `500` - Internal server error

---

#### Create License

**POST** `/licenses`

Creates a new license for a project.

**Request Body:**
```json
{
  "project_id": "abc-123-def-456",
  "client_name": "John Doe",
  "expires_at": "2025-12-31T23:59:59Z",
  "max_activations": 1,
  "offline_lease_hours": 168
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | Yes | The project to create license for |
| `client_name` | string | No | Name of the license holder |
| `expires_at` | string | No | ISO 8601 expiration timestamp |
| `max_activations` | integer | No | Maximum hardware bindings (default: 1) |
| `offline_lease_hours` | integer | No | Offline lease duration in hours (default: 168) |

**Response (201 Created):**
```json
{
  "id": "lic-uuid-1",
  "license_key": "LIC-XXXX-XXXX-XXXX-XXXX",
  "project_id": "abc-123-def-456",
  "status": "active",
  "client_name": "John Doe",
  "expires_at": "2025-12-31T23:59:59Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Codes:**
- `400` - Invalid request parameters
- `401` - Invalid or expired authentication token
- `404` - Project not found
- `500` - Internal server error

---

#### Revoke License

**DELETE** `/licenses/{license_id}`

Revokes (deactivates) a license.

**Path Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `license_id` | string | Yes | The license ID to revoke |

**Response (200 OK):**
```json
{
  "message": "License revoked successfully",
  "license_id": "lic-uuid-1",
  "status": "inactive"
}
```

**Error Codes:**
- `401` - Invalid or expired authentication token
- `404` - License not found
- `500` - Internal server error

---

### Common Error Response Format

All endpoints return errors in this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "ERROR_CODE_CONSTANT",
  "timestamp": 1234567890
}
```

### Rate Limiting

- License validation endpoint: 60 requests per minute per IP
- Management endpoints: 300 requests per minute per user

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1234567890
```

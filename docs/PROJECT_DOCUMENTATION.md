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

### Commands

```bash
# Login to your account
lw-compiler login

# List your projects
lw-compiler projects

# Build a project interactively
lw-compiler build

# Build specific project with clear flags
lw-compiler build <project_id> --license <key> --output my_app.exe
```

### Configuration
The CLI reads from `config.json` inside project folders, but can be overridden by flags.

---

## 📡 API Reference

Base URL: `http://localhost:8000/api/v1`

### Validation Endpoint (Public)
**POST** `/license/validate`
```json
{
  "license_key": "LIC-...",
  "hwid": "...",
  "nonce": "...",
  "timestamp": 123456789
}
```

### Management Endpoints (Auth Required)
- **GET** `/projects`: List projects
- **POST** `/licenses`: Create license
- **DELETE** `/licenses/{id}`: Revoke license

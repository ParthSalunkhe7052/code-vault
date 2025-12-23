# Changelog

All notable changes to CodeVault (License Wrapper) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 23-12-2024

### Security

- Fixed XSS vulnerability in Login.jsx (URL-encode email in mailto href)
- Fixed information exposure in stripe_routes.py (generic error messages)
- Added LGTM annotations for validated path operations in:
  - `compile_helpers.py` (subprocess with path validation)
  - `storage_service.py` (file ops from validated helpers)
  - `nodejs_compiler.py` (tempfile.mkdtemp paths)

---

## [Previous] - 22-12-2024

### Added

- **Git Commander Workflow** (`.agent/workflows/git-commander.md`)
  - Senior DevOps Engineer workflow for safe GitHub syncing
  - Qodo local review integration
  - Security audit for secrets detection
  - Atomic commit strategy with Conventional Commits
  - Branch naming with international date format (DD-MM-YYYY)
  - CHANGELOG update step

- **Security Enforcer Agent** (`.qodo/agents/security-enforcer.toml`)
  - Reviews encryption modules
  - Flags raw localStorage usage without encryption
  - Enforces EncryptionProvider usage for sensitive data

- **CI/CD Pipeline** (`.github/workflows/main.yml`)
  - CodeQL security scanning for JavaScript and Python
  - Frontend lint and build checks
  - Backend Python checks
  - Dependency security audits (npm audit, pip-audit)
  - Triggers on push to main and all PRs

- **EncryptionProvider Utility** (`frontend/src/utils/EncryptionProvider.js`)
  - AES-GCM encryption using Web Crypto API
  - PBKDF2 key derivation (100,000 iterations)
  - `secureLocalStorage` wrapper for encrypted storage
  - Sensitive key detection utility

### Security

- Implemented encryption infrastructure for sensitive frontend data
- Added automated security scanning in CI/CD pipeline
- Created security-focused code review agent

---

## How to Use

### Git Commander
```bash
# Use when you have changes ready to push
/git-commander
```

### EncryptionProvider
```javascript
import { secureLocalStorage } from './utils/EncryptionProvider';

// Store encrypted
await secureLocalStorage.setItem('token', 'my-secret');

// Retrieve decrypted
const token = await secureLocalStorage.getItem('token');
```

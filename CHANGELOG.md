# Changelog

All notable changes to CodeVault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 29-01-2026 (Marketplace Pivot)

### Added ✨
- **Marketplace**: Full pivot to a Digital Goods Marketplace model.
- **Seller Tools**: Added `codevault publish` and `codevault earnings` to CLI.
- **Storefront**: New public store at `store.codevault.app`.
- **Dodo Payments**: Integration as Merchant of Record (MoR) for global payouts.
- **Seller Dashboard**: Real-time sales tracking and payout management.

### Changed 🔧
- **Pricing**: Shifted from SaaS subscription to Transaction Fee model.
- **Landing Page**: Completely redesigned for "Seller" and "Buyer" personas.
- **Documentation**: Updated guides to reflect the new marketplace workflow.

---

## [1.1.2] - 28-01-2026

### Fixed 🐛
- **CLI Login**: Fixed `login` command not respecting `LW_API_URL` environment variable, causing test failures and inconsistent behavior with other commands like `projects` and `licenses`

### Technical Details
- `cmd_login()` in `cli/commands/auth.py` now checks `LW_API_URL` env var first before falling back to config/default
- This ensures all CLI commands use consistent API URL resolution (env var > config > default)
- CLI test suite now passes all 10/10 tests

---

## [1.1.0] - 27-12-2024

### Fixed 🐛
- **Mission Control Map**: Fixed broken map by integrating GeoIP database and fixing silent failures in `license_routes.py`.
- **Localhost Geolocation**: Added "New York" dev coordinates for localhost testing.
- **Node.js builds**: Fixed `pkg` module resolution issues.

### Added ✨
- **Performance**: Parallelized Dashboard SQL queries using `asyncio.gather` (3-4x faster load).
- **Mock Data Generator**: Created `populate_mock_map.py` for instant map visualization.
- **CLI Aesthetics**: Redesigned `Run CLI.bat` and `Run Web App.bat` with Cyberpunk ASCII art and better UX.

### Changed 🔧
- **Branding**: Renamed references to "CodeVault" in documentation.
- **Architecture**: Clarified "Web + CLI" focus in `PROJECT_DOCUMENTATION.md`.
- **Code Hygiene**: Formatted codebase with `ruff` (20+ files) and cleaned up dead code.

---

## [1.1.1-pre] - 27-12-2024

### Fixed
- CLI: Removed unused import `get_nodejs_wrapper` in `lw_compiler.py` (ruff F401)
- CLI: Replaced bare `except:` with `except Exception:` in `wrappers.py` (2 locations)

### Changed
- Node.js builds: Using inline wrapper approach for better pkg compatibility
- CLI UX: Improved build progress indicators with elapsed time spinner

---

## [Unreleased] - 23-12-2024

### Added ✨
- **Mission Control Map**: Real-time license activation tracking with GeoIP integration
- **Dashboard Performance**: Parallelized SQL queries using `asyncio.gather` (3-4x faster load times)
- **Mock Data Generator**: `populate_mock_map.py` for instant map visualization in development
- **CLI Aesthetics**: Redesigned launcher scripts with Cyberpunk ASCII art and improved UX
- **Test Suite**: Comprehensive API endpoint tests and structure validation
- **Startup Checks**: Zombie job killer to mark stalled builds as failed on server restart

### Fixed 🐛
- **Map Geolocation**: Fixed broken map by properly integrating GeoLite2-City database
- **Localhost Coordinates**: Added NYC dev coordinates for localhost testing
- **Node.js Builds**: Resolved `pkg` module resolution issues
- **License Routes**: Fixed silent failures in geolocation lookup
- **Build Progress**: Fixed UI state loss when switching tabs
- **Security**: Log injection vulnerabilities with `sanitize_log_message` utility
- **Security**: XSS vulnerability in Login.jsx email mailto links

### Changed 🔧
- **Branding**: Updated all documentation references to "CodeVault"
- **Architecture**: Clarified Web + CLI focus in project documentation
- **Code Quality**: Formatted codebase with Ruff (79 files total)
- **Database**: Enhanced analytics queries for better performance
- **Email Service**: Improved error handling and reliability
- **Stripe Integration**: Better error messages and info exposure prevention
- **Tauri Desktop**: Marked as deprecated, focusing on Web + CLI model

### Security 🔒
- Added `sanitize_log_message` utility to prevent log injection
- Fixed information exposure in Stripe error messages  
- URL-encoded email in mailto href to prevent XSS
- Added LGTM annotations for validated path operations

---

## How to Use

### For Developers
```bash
# Run the web application
Run Web App.bat

# Run the CLI tool
Run CLI.bat

# Start backend server
python -m uvicorn server.main:app --reload
```

### For Contributors
See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.
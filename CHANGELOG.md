# Changelog

All notable changes to CodeVault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 27-12-2024

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

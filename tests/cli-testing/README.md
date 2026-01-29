# CodeVault CLI Testing Environment

A self-contained testing environment for the `lw-compiler` CLI tool. This allows automated testing without requiring a real backend server or database.

## Overview

The testing system consists of:

- **Mock Server** (`mock_server.py`) - A FastAPI server that simulates the CodeVault backend API
- **Fixtures** (`fixtures.py`) - Test data, accounts, and helper functions
- **Test Runner** (`test_runner.py`) - Main script that orchestrates and runs all tests
- **Test Projects** (`test_projects/`) - Sample projects for build testing

## Quick Start

### Prerequisites

1. Python 3.11+ installed
2. CodeVault CLI dependencies installed:
   ```bash
   cd CodeVaultV1/cli
   pip install -r requirements.txt
   ```

3. Testing dependencies:
   ```bash
   pip install fastapi uvicorn httpx
   ```

### Running Tests

From the `CodeVaultV1` directory:

```bash
# Run all tests with verbose output
python tests/cli-testing/test_runner.py --verbose

# Run specific test category
python tests/cli-testing/test_runner.py --test auth
python tests/cli-testing/test_runner.py --test projects
python tests/cli-testing/test_runner.py --test build

# Skip build tests (faster, useful for auth/project testing)
python tests/cli-testing/test_runner.py --verbose --skip-build

# Use a different port for mock server
python tests/cli-testing/test_runner.py --port 9000

# Run tests against an already-running mock server
python tests/cli-testing/test_runner.py --no-server
```

### Running Mock Server Standalone

For manual CLI testing:

```bash
# Start the mock server
python tests/cli-testing/mock_server.py

# In another terminal, set the API URL and use CLI
set LW_API_URL=http://127.0.0.1:8000  # Windows
export LW_API_URL=http://127.0.0.1:8000  # Linux/Mac

# Now use the CLI normally
python cli/lw_compiler.py login
python cli/lw_compiler.py projects list
```

## Test Accounts

The mock server comes with pre-configured test accounts:

| Email | Password | Tier | Description |
|-------|----------|------|-------------|
| `test@codevault.local` | `testpass123` | Free | Basic test account |
| `pro@codevault.local` | `propass123` | Pro | Pro tier account |
| `admin@codevault.local` | `adminpass123` | Admin | Admin account |

## Test Licenses

Pre-configured test licenses:

| License Key | Status | Type | HWID Bound |
|-------------|--------|------|------------|
| `CV-TEST-0001-AAAA-BBBB` | Active | Lifetime | No |
| `CV-TEST-0002-CCCC-DDDD` | Active | 30 days | No |
| `CV-EXPIRED-0001-XXXX-YYYY` | Expired | - | No |

## Directory Structure

```
tests/cli-testing/
├── mock_server.py      # FastAPI mock backend
├── fixtures.py         # Test data and helpers
├── test_runner.py      # Main test orchestrator
├── README.md           # This file
└── test_projects/      # Sample projects for build testing
    └── hello_world/
        ├── main.py           # Simple test application
        └── requirements.txt  # Dependencies (none)
```

## Test Categories

### Authentication Tests (`--test auth`)
- Login with valid credentials
- Login with invalid credentials
- Logout functionality
- Token persistence

### Project Tests (`--test projects`)
- List projects
- Create new project
- Get project details
- Delete project

### Build Tests (`--test build`)
- Build help command
- Build configuration
- Full build process (requires Nuitka)

### General Tests
- Version command
- Help command
- Invalid command handling

## Mock Server API Endpoints

The mock server implements these endpoints:

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Projects
- `GET /api/v1/projects` - List user's projects
- `POST /api/v1/projects` - Create new project
- `GET /api/v1/projects/{id}` - Get project details
- `DELETE /api/v1/projects/{id}` - Delete project

### Licenses
- `POST /api/v1/licenses/validate` - Validate a license
- `GET /api/v1/projects/{id}/licenses` - Get project licenses

### Builds
- `POST /api/v1/builds` - Create new build
- `GET /api/v1/builds/{id}` - Get build status

### Health
- `GET /health` - Server health check

## Extending the Tests

### Adding New Test Accounts

Edit `mock_server.py` and add to the `TEST_USERS` dictionary:

```python
TEST_USERS = {
    # ... existing users ...
    "new@codevault.local": {
        "id": 4,
        "email": "new@codevault.local",
        "password": "newpass123",
        "name": "New User",
        "subscription_tier": "enterprise"
    }
}
```

### Adding New Test Projects

Create a new directory under `test_projects/`:

```
test_projects/
└── my_new_project/
    ├── main.py
    ├── requirements.txt
    └── other_files.py
```

Then update `fixtures.py` to include the new project path.

### Adding New Test Cases

Edit `test_runner.py` and add new test functions:

```python
def test_my_new_feature():
    """Test description."""
    cli = CLIRunner()
    
    result = cli.run(["my-command", "--flag"])
    
    if result.returncode != 0:
        return False, f"Command failed: {result.stderr}"
    
    if "expected output" not in result.stdout:
        return False, "Expected output not found"
    
    return True, "Test passed"
```

Then add it to the appropriate test category in `run_tests()`.

## Troubleshooting

### "Connection refused" errors

The mock server isn't running. Either:
- Let the test runner start it automatically (default)
- Start it manually: `python tests/cli-testing/mock_server.py`

### "Module not found" errors

Install missing dependencies:
```bash
pip install fastapi uvicorn httpx python-jose passlib
```

### Token/auth issues

Clear any existing CLI credentials:
```bash
python cli/lw_compiler.py logout
```

Or manually delete the credential file (location varies by OS).

### Build tests failing

Build tests require Nuitka to be installed:
```bash
pip install nuitka
```

Use `--skip-build` to skip build tests if Nuitka isn't available.

## Notes

- The mock server uses in-memory storage; all data is reset when the server restarts
- Test tokens expire after 24 hours
- The `keyring` LSP warnings in `cli_config.py` are expected (conditional import)
- Build tests may take several minutes depending on system performance

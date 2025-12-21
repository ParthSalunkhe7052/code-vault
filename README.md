# Code Vault

A SaaS tool for wrapping Python and Node.js scripts with license protection and compiling to standalone executables.

## Features

- 🔐 **License Protection**: Embed license validation into your scripts
- 🖥️ **HWID Locking**: Bind licenses to specific machines
- 💓 **Heartbeat System**: Periodic license validation with offline grace period
- 🔨 **Nuitka Compilation**: Compile to native executables (prevents decompilation)
- ☁️ **Cloud Compilation**: Compile without local Nuitka installation *(Coming Soon)*
- 📊 **Dashboard**: Web UI for license management

## System Requirements

### For Python Compilation
- **Python 3.12+** - [Download](https://python.org)
- **Nuitka** - Auto-installed on first build

### For Node.js Compilation (Pro/Enterprise)
- **Node.js 18+** - [Download](https://nodejs.org)
- **npm** - Comes with Node.js
- **pkg** - Runs automatically via `npx`
- **javascript-obfuscator** - Optional, for code protection *(Coming Soon)*

### Desktop App
- Windows 10/11, macOS 10.15+, or Linux
- Python 3.12+ installed and in PATH

## Quick Start

### Installation


```bash
pip install license-wrapper
```

### Wrap a Script

```bash
# Wrap your Python script
license-wrapper wrap main.py \
    --license-key LIC-XXXX-XXXX-XXXX \
    --server-url https://api.license-wrapper.com \
    --output wrapped/

# Compile to executable
license-wrapper compile wrapped/ --platform windows
```

### Generate License Keys

```bash
license-wrapper keygen --prefix LIC --count 10
```

## How It Works

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   Your      │────▶│  License-Wrapper│────▶│  Protected  │
│   Script    │     │     (Wrap)      │     │    .exe     │
└─────────────┘     └─────────────────┘     └─────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  License Server │
                    │  (Validation)   │
                    └─────────────────┘
```

1. **Upload**: Freelancer uploads their Python script
2. **Configure**: Set license key and expiration
3. **Inject**: License checker is injected into the code
4. **Compile**: Nuitka compiles everything to native code
5. **Distribute**: Client receives protected .exe
6. **Validate**: Executable checks license on startup and periodically

## Security Features

### HWID Locking
- Collects CPU ID, motherboard serial, disk serial, and machine GUID
- Binds license to specific hardware
- Prevents unauthorized copying

### Replay Attack Prevention
- Cryptographic nonces prevent response replay
- Timestamp validation (5-minute window)
- HMAC-SHA256 response signatures

### Compilation Protection
- Nuitka compiles Python to C, then to machine code
- No Python bytecode in final binary
- Prevents decompilation with uncompyle6

### Offline Grace Period
- Cached license validation
- Configurable grace period (default 24 hours)
- Automatic recovery when online

## CLI Commands

```bash
# Wrap a script with license protection
license-wrapper wrap <script.py> [options]
  --license-key, -k    License key to embed
  --server-url, -s     License server URL
  --output, -o         Output directory
  --grace-period       Offline grace period in hours
  --product-name       Product name for executable
  --gui                GUI mode (no console window)

# Compile wrapped project
license-wrapper compile <project_dir> [options]
  --platform           Target platform (windows/linux/macos)
  --output-name        Output executable name

# Generate license keys
license-wrapper keygen [options]
  --prefix             Key prefix (default: LIC)
  --count              Number of keys to generate
  --segments           Number of key segments

# Analyze script dependencies
license-wrapper analyze <script.py>
```

## Project Structure

```
CodeVault/
├── cli/                    # CLI compiler tool
│   ├── lw_compiler.py      # Main CLI entry point
│   ├── lw-compiler.bat     # Windows launcher
│   └── README.md           # CLI documentation
├── server/
│   ├── main.py             # FastAPI license server
│   ├── email_service.py    # Email notifications
│   └── storage_service.py  # File storage (R2/local)
├── frontend/               # React web dashboard
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Page components
│       └── services/       # API client
├── src-tauri/              # Desktop app (Tauri)
├── Run Desktop App.bat     # Launcher script
└── docker-compose.yml
```

## Development

### Local Setup

```bash
# Clone repository
git clone https://github.com/ParthSalunkhe7052/code-vault
cd code-vault

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev,compile]"

# Start infrastructure
docker-compose up -d postgres redis

# Run API server
python server/main.py
```

### Running Tests

```bash
pytest tests/
```

## License Server API

### Validate License (Public)

```http
POST /api/v1/license/validate
Content-Type: application/json

{
  "license_key": "LIC-XXXX-XXXX-XXXX",
  "hwid": "a1b2c3d4...",
  "nonce": "random_string",
  "timestamp": 1701234567
}
```

### Manage Licenses (Authenticated)

```http
# Create license
POST /api/v1/licenses
X-API-Key: your-api-key

# List licenses
GET /api/v1/licenses
X-API-Key: your-api-key

# Revoke license
POST /api/v1/licenses/{id}/revoke
X-API-Key: your-api-key
```

## Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f license-api

# Compile a script
docker run -v ./input:/app/input -v ./output:/app/output \
    license-wrapper-compiler --config /app/input/build_config.json
```

## Pricing

| Feature | Free | Pro ($29/mo) | Enterprise ($99/mo) |
|---------|------|--------------|---------------------|
| Projects | 1 | 10 | Unlimited |
| Licenses/Project | 5 | 100 | Unlimited |
| Validations/Day | 100 | 10,000 | Unlimited |
| Binary Retention | 7 days | 30 days | 90 days |
| Support | Community | Priority | Dedicated |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📧 Email: support@license-wrapper.com
- 💬 Discord: [Join our server](https://discord.gg/license-wrapper)
- 📖 Docs: [docs.license-wrapper.com](https://docs.license-wrapper.com)

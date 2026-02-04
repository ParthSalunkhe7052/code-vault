# CodeVault Quick Start

## Running CodeVault Locally

### Option 1: One-Click Startup (Recommended)

Simply double-click the `Start-CodeVault.bat` file in the root directory. This will:

1. ✅ Check all prerequisites (Python, Node.js, npm)
2. ✅ Install dependencies if needed
3. ✅ Start the backend server (Port 8000)
4. ✅ Start the frontend dashboard (Port 5173)
5. ✅ Start the landing page (Port 3000)
6. ✅ Open the landing page in your browser

### Option 2: Manual Startup

#### Start Backend
```bash
cd server
python main.py
```

#### Start Frontend Dashboard
```bash
cd frontend
npm run dev
```

#### Start Landing Page
```bash
cd landing-page
npm run dev
```

### Accessing CodeVault

Once all services are running:

- **Landing Page:** http://localhost:3000
- **Frontend Dashboard:** http://localhost:5173
- **Backend API:** http://127.0.0.1:8000
- **API Documentation:** http://127.0.0.1:8000/docs

### Stopping CodeVault

To stop all services:
1. Close the Backend, Frontend, and Landing Page command windows
2. Or press `Ctrl+C` in each window

### Troubleshooting

**Port Already in Use:**
- The startup script automatically kills processes on ports 8000, 5173, and 3000
- If issues persist, manually check: `netstat -ano | findstr "8000 5173 3000"`

**Backend Fails to Start:**
- Ensure PostgreSQL is running (if using local database)
- Check `.env` file exists in the `server/` directory
- Verify all environment variables are set

**Frontend Build Errors:**
- Delete `node_modules/` and run: `npm install`
- Clear npm cache: `npm cache clean --force`

**Dependencies Not Installing:**
- For Python: Ensure `pip` is up to date: `python -m pip install --upgrade pip`
- For npm: Update npm: `npm install -g npm@latest`

### System Requirements

- **Python:** 3.11 or higher
- **Node.js:** 18.x or higher
- **npm:** 9.x or higher
- **PostgreSQL:** 14.x or higher (for production)
- **RAM:** Minimum 4GB, Recommended 8GB
- **OS:** Windows 10/11, macOS, or Linux

### Development Workflow

1. **First Time Setup:**
   - Clone the repository
   - Run `Start-CodeVault.bat`
   - Wait for all services to start
   - Access http://localhost:3000

2. **Daily Development:**
   - Run `Start-CodeVault.bat` each time you start working
   - Services will hot-reload on file changes
   - No need to restart unless you change dependencies

3. **Before Committing:**
   - Stop all services
   - Run tests (if available)
   - Check for linting errors

### Additional Resources

- **Setup Guide:** `DEPLOYMENT.md`
- **API Documentation:** http://127.0.0.1:8000/docs (when backend is running)
- **Contributing:** `CONTRIBUTING.md`
- **Changelog:** `CHANGELOG.md`
- **Google Cloud Build Migration:** `docs/GOOGLE_CLOUD_BUILD_MIGRATION.md`

### Support

If you encounter any issues:
1. Check the command windows for error messages
2. Review the `.env` file configuration
3. Ensure all prerequisites are installed
4. Contact the development team

---

**Quick Command Reference:**

```bash
# Start everything
.\Start-CodeVault.bat

# Install dependencies manually
cd server && pip install -r requirements.txt
cd frontend && npm install
cd landing-page && npm install

# Check service status
curl http://127.0.0.1:8000/api/v1/status    # Backend
curl http://localhost:5173                   # Frontend
curl http://localhost:3000                   # Landing Page
```

---

**Happy Coding!** 🚀

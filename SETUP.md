# Quick Setup Guide for CodeVault

## Backend Database Setup (Required)

CodeVault requires PostgreSQL. You have 2 options:

### Option 1: Use Neon (Free, Easiest - RECOMMENDED)

1. Go to https://neon.tech
2. Create a free account (no credit card needed)
3. Click "Create Project"
4. Copy the connection string (looks like: `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb`)
5. Open `server/.env` file
6. Replace line 13 with your connection string:
   ```
   DATABASE_URL=postgresql://your_connection_string_here
   ```
7. Save the file

### Option 2: Local PostgreSQL

1. Download PostgreSQL: https://www.postgresql.org/download/windows/
2. Install with default settings (remember your password!)
3. Open pgAdmin or command line
4. Create database:
   ```sql
   CREATE DATABASE codevault;
   ```
5. Open `server/.env`
6. Update line 13:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/codevault
   ```
7. Save the file

## Running CodeVault

Once database is configured:

1. **Double-click `Start-CodeVault.bat`**
2. Three windows will open (Backend, Frontend, Landing Page)
3. Browser will open automatically to http://localhost:3000

## Services

- **Landing Page:** http://localhost:3000
- **Frontend Dashboard:** http://localhost:5173  
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

## Troubleshooting

**Backend crashes immediately:**
- Check that `DATABASE_URL` is set in `server/.env`
- Test connection string by opening it in a PostgreSQL client

**"Connection refused" error:**
- Verify PostgreSQL is running (if using local)
- Check connection string is correct
- For Neon: make sure `?sslmode=require` is at the end

**Still not working?**
- Check the backend window for error messages
- The window stays open now so you can read errors
- Copy the error and search for solution

## Next Steps

Once running:
1. Go to http://localhost:5173 to access the dashboard
2. Create an account
3. Start creating projects and licenses!

---

**Need help?** Check the backend command window for specific error messages.

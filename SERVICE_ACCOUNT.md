# Test Account Credentials

## Enterprise Test Account
- **Email:** testuser2024@example.com
- **Password:** testpassword123
- **Plan:** Enterprise
- **Build Credits:** 999999

## Admin Account (for upgrading users)
- **Email:** parth.ajit7052@gmail.com
- **Password:** test (or your actual password)
- **Role:** Admin
- **Plan:** Enterprise

## Test Project
- **Project ID:** 33e5d8196a5c12bdc40a47780c72bab0
- **Name:** Test Cloud Build Project
- **Language:** Python

## Cloud Build Status

### Issues Found and Fixed:

1. **Feature Name Mismatch (CRITICAL)** - FIXED
   - Location: `server/routes/cloud_build_routes.py:49`
   - Problem: Router checked for feature `"cloud_builds"` but config uses `"cloud_compilation"`
   - Fix: Changed to `"cloud_compilation"`

2. **Import Path Error** - FIXED
   - Location: `server/routes/cloud_build_routes.py` (multiple places)
   - Problem: cloud_build_integration modules not in Python path
   - Fix: Changed sys.path to include `scripts/` folder

3. **Enterprise Plan Not in Admin Endpoint** - FIXED
   - Location: `server/routes/admin_routes.py`
   - Problem: Admin endpoint only allowed 'free', 'pro', 'business'
   - Fix: Added 'enterprise' to allowed plans

4. **Enterprise Branding Features** - FIXED
   - Location: `server/utils.py`
   - Problem: Enterprise not included in branding feature checks
   - Fix: Added 'enterprise' to is_pro, can_remove_branding, can_custom_branding

5. **cloudbuild.yaml Configuration** - NEEDS TESTING
   - Location: `scripts/cloudbuild.yaml`
   - Issue: Google Cloud Build API requires all substitutions to be declared
   - Status: Updated yaml with all required substitution variables

### Testing the Cloud Build

To test cloud builds:
1. Start the backend server: `cd server && python main.py`
2. Start frontend: `cd frontend && npm run dev`
3. Login with test account: testuser2024@example.com / testpassword123
4. Navigate to Build Settings
5. Create a project and try to build

### Current Issue
The cloud build is failing with Google Cloud Build API error about substitution variables. The cloudbuild.yaml needs further debugging to match what the Google Cloud Build API expects.

### Token for API Testing
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkMzgzZjlhMjFkZDRkMWYwNDk0MjZmODJjZTk5YjIwMiIsImVtYWlsIjoidGVzdHVzZXIyMDI0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzcwOTk5NTkxLCJpYXQiOjE3NzA5MTMxOTF9.BYFfgpm8bpeRkNdxqSd1FF30EDKF4j7qK6pepSlw87k
```

### Useful API Endpoints
- Get user info: GET /api/v1/auth/me
- List projects: GET /api/v1/projects
- Start cloud build: POST /api/v1/cloud-build/start
- Build status: GET /api/v1/cloud-build/{build_id}/status
- Update user plan: PUT /api/v1/admin/users/{user_id}/plan (body: {"plan": "enterprise"})

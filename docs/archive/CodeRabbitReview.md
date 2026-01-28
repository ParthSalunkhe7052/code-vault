# CodeRabbit Review Fixes Tracker

## ✅ COMPLETED FIXES

### Batch 1: email_service.py & requirements.txt
- [x] **email_service.py:13** - Fixed `from datetime import datetime` → `from datetime import datetime, timezone`
- [x] **email_service.py:129-155** - Added proper SMTP connection cleanup with try/finally
- [x] **email_service.py:174** - Fixed deprecated `asyncio.get_event_loop()` → `asyncio.get_running_loop()`
- [x] **email_service.py:437** - Fixed deprecated `datetime.utcnow()` → `datetime.now(timezone.utc)`
- [x] **requirements.txt:10** - Removed duplicate `pyjwt>=2.8.0` entry

### Batch 2: auth_routes.py & GitHub Actions
- [x] **auth_routes.py:165** - Added email normalization to admin-reset-password endpoint
- [x] **.github/workflows/main.yml:27** - Updated `actions/checkout@v3` → `@v4`
- [x] **.github/workflows/main.yml:30** - Updated `github/codeql-action/init@v2` → `@v3`
- [x] **.github/workflows/main.yml:35** - Updated `github/codeql-action/autobuild@v2` → `@v3`
- [x] **.github/workflows/main.yml:38** - Updated `github/codeql-action/analyze@v2` → `@v3`
- [x] **.github/workflows/main.yml:46** - Updated lint job `actions/checkout@v3` → `@v4`

### Batch 3: server/main.py (Security & Logic Fixes)
- [x] **main.py:148** - Fixed buggy `nuitka_available` check (was always true if Python installed)
- [x] **main.py:606-618** - Added Zip Slip vulnerability protection (path traversal validation)
- [x] **main.py:1062** - Removed duplicate `CLI_VERSION`, now imports from `config.py`

---

## 🔄 PENDING FIXES

In server/storage_service.py around lines 613 to 637, the test block 
uses project_id="test-project" which fails validation because get_safe_project_dir expects a 32-character hex PROJECT_ID_PATTERN; replace 
the hardcoded invalid id with a valid 32-char hex string (e.g. generate uuid4().hex or use "0123456789abcdef0123456789abcdef") or fetch a 
valid project id from config/env before calling upload_file so the local-storage test does not raise ValueError.



============================================================================
File: test_obfuscation_project_zip/index.js
Line: 126 to 127
Type: refactor_suggestion

Comment:
Return actual test results instead of hardcoded values.

Line 127 hardcodes true for testEnvironmentInfo results. The test should return its actual pass/fail status.




🔎 Suggested fix

Modify testEnvironmentInfo to return a boolean:

 function testEnvironmentInfo() {
     console.log('💻 TEST 5: Environment Information');
     console.log('   ├─ Node Version: ' + process.version);
     console.log('   ├─ Platform: ' + process.platform);
     console.log('   ├─ Architecture: ' + process.arch);
     console.log('   ├─ Process ID: ' + process.pid);
     console.log('   ├─ Working Directory: [REDACTED]');
     console.log('   └─ Status: ✅ PASSED');
     console.log('');
+    return true;
 }


Then in main():

-    testEnvironmentInfo();
-    results.push(true);
+    results.push(testEnvironmentInfo());

Prompt for AI Agent:
In test_obfuscation_project_zip/index.js around lines 126 to 127, the function currently returns a hardcoded true for testEnvironmentInfo; update it to compute and return the actual pass/fail boolean based on the environment checks it performs (e.g., validate required files, 
versions, or runtime conditions) instead of hardcoding true, and then in main() consume that returned boolean to set the test result (aggregate or short-circuit as needed) so the actual test outcome is propagated rather than always passing.



============================================================================
File: test_obfuscation_project_zip/index.js
Line: 28 to 34
Type: potential_issue

Comment:
Avoid logging secrets, even when masked.

Lines 30-31 log portions of SECRET_API_KEY and reference DATABASE_URL. Logging secrets (even partially) is a compliance risk as logs may be stored, monitored, or accessed by unauthorized parties.




🔎 Suggested approach

 function testSecretStorage() {
     console.log('📦 TEST 1: Secret Storage');
-    console.log('   ├─ API Key (first 10 chars): ' + SECRET_API_KEY.substring(0, 10) + '...');
-    console.log('   ├─ Database URL loaded: ' + (DATABASE_URL.length > 0 ? '✅ Yes' : '❌ No'));
+    console.log('   ├─ API Key configured: ' + (SECRET_API_KEY.length > 0 ? '✅ Yes' : '❌ No'));
+    console.log('   ├─ Database URL configured: ' + (DATABASE_URL.length > 0 ? '✅ Yes' : '❌ No'));
     console.log('   └─ Status: ✅ PASSED');
     console.log('');
 }

Prompt for AI Agent:
In test_obfuscation_project_zip/index.js around lines 28 to 34, remove the console logging that prints portions of SECRET_API_KEY and references DATABASE_URL; instead do not emit actual secret values to logs—log only non-sensitive metadata such as "SECRET_API_KEY present: true" or the env variable name and its presence/length (no substring or 
masked parts), or replace the log with a generic message like "sensitive configuration loaded" and ensure any diagnostic output uses fully redacted values or boolean checks so no secret characters are ever written to logs.



============================================================================
File: .github/workflows/main.yml
Line: 27 to 40
Type: potential_issue

Comment:
Update GitHub Actions to current versions.

Per static analysis, the actions used are outdated. actions/checkout@v3 and github/codeql-action/*@v2 are no longer supported on the latest GitHub Actions runners.




🔎 Proposed fix to update action versions

     steps:
     - name: Checkout repository
-      uses: actions/checkout@v3
+      uses: actions/checkout@v4

     - name: Initialize CodeQL
-      uses: github/codeql-action/init@v2
+      uses: github/codeql-action/init@v3
       with:
         languages: ${{ matrix.language }}

     - name: Autobuild
-      uses: github/codeql-action/autobuild@v2
+      uses: github/codeql-action/autobuild@v3

     - name: Perform CodeQL Analysis
-      uses: github/codeql-action/analyze@v2
+      uses: github/codeql-action/analyze@v3
       with:
         category: "/language:${{matrix.language}}"

Prompt for AI Agent:
.github/workflows/main.yml lines 27-40: the workflow references deprecated action versions (actions/checkout@v3 and github/codeql-action/*@v2); update them to supported major releases by changing actions/checkout@v3 to actions/checkout@v4 and github/codeql-action/init@v2, github/codeql-action/autobuild@v2, github/codeql-action/analyze@v2 to github/codeql-action/init@v3, github/codeql-action/autobuild@v3, github/codeql-action/analyze@v3 respectively, preserving the existing with: and uses: settings and the matrix.language interpolation.



============================================================================
File: server/storage_service.py
Line: 295 to 347
Type: potential_issue

Comment:
R2 deletion doesn't handle pagination for large projects.

list_objects_v2 returns at most 1000 objects. If a project has more files, some won't be deleted. Consider using a paginator or checking IsTruncated.




🔎 Proposed fix to handle pagination

         if self.use_r2 and self.client:
             # List and delete from R2
             try:
-                prefix = f"uploads/{project_id}/"
-                response = self.client.list_objects_v2(
-                    Bucket=self.bucket, Prefix=prefix
-                )
-
-                if "Contents" in response:
-                    for obj in response["Contents"]:
-                        self.client.delete_object(Bucket=self.bucket, Key=obj["Key"])
-                        deleted_count += 1
+                for prefix in [f"uploads/{project_id}/", f"builds/{project_id}/"]:
+                    paginator = self.client.get_paginator('list_objects_v2')
+                    for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
+                        if "Contents" in page:
+                            for obj in page["Contents"]:
+                                self.client.delete_object(Bucket=self.bucket, Key=obj["Key"])
+                                deleted_count += 1

Prompt for AI Agent:
In server/storage_service.py around lines 295 to 347, the R2 deletion block calls list_objects_v2 once and therefore misses objects when the result is paginated; change it to iterate all pages (either via client.get_paginator('list_objects_v2') or by looping with ContinuationToken/IsTruncated) for both the "uploads/{project_id}/" and "builds/{project_id}/" prefixes, delete objects found on each page, and increment deleted_count accordingly; ensure you handle missing "Contents" on a page and propagate or log ClientError as before.



============================================================================
File: test_obfuscation_project_zip/index.js
Line: 12 to 13
Type: potential_issue

Comment:
Remove hardcoded secrets and credentials.

Even in test code, hardcoding secrets and database credentials creates security risks. These values can leak into version control, logs, and error reports.

Use environment variables instead:



🔎 Proposed fix using environment variables

-const SECRET_API_KEY = 'sk_live_VERY_SECRET_KEY_12345';
-const DATABASE_URL = 'mongodb://admin:password123@localhost:27017/mydb';
+const SECRET_API_KEY = process.env.SECRET_API_KEY || 'sk_test_placeholder';
+const DATABASE_URL = process.env.DATABASE_URL || 'mongodb://localhost:27017/testdb';

Prompt for AI Agent:
In test_obfuscation_project_zip/index.js around lines 12 to 13, remove the hardcoded secrets/credentials and replace them with environment variables (e.g., process.env.DB_PASSWORD, process.env.API_KEY); add 
a short runtime check that throws or exits with a clear message if required env vars are missing so tests fail fast, and for local development recommend using a .env (loaded via dotenv) that is excluded from version control (.gitignore) to avoid committing secrets.



============================================================================
File: requirements.txt
Line: 10 to 18
Type: potential_issue

Comment:
Remove duplicate PyJWT dependency.

PyJWT appears twice in the requirements file:
- Line 10: pyjwt>=2.8.0 (CLI Tool section)
- Line 18: PyJWT>=2.8.0 (Server section)

These refer to the same package (package names are case-insensitive in pip). Keep only one entry to avoid confusion.




🔎 Proposed fix

Remove the duplicate entry and keep it in the appropriate section:   

 # License Core (injected into wrapped apps)
 requests>=2.28.0
 cryptography>=40.0.0
-pyjwt>=2.8.0

 # Server
 fastapi>=0.104.0
 uvicorn[standard]>=0.24.0
 pydantic[email]>=2.5.0
 python-multipart>=0.0.6
 bcrypt>=4.1.0
 PyJWT>=2.8.0

Prompt for AI Agent:
In requirements.txt around lines 10 to 18, there is a duplicate PyJWT entry (pyjwt>=2.8.0 at line 10 and PyJWT>=2.8.0 at line 18); remove 
one of them so the package appears only once (prefer keeping a single, consistently-cased entry in the Server section), and ensure sections remain properly separated and formatted after deletion.



============================================================================
File: docs/PROJECT_DOCUMENTATION.md
Line: 14 to 16
Type: potential_issue

Comment:
Fix invalid anchor links in Table of Contents.

The link fragments don't match the actual section headings. Markdown 
anchor links are generated by lowercasing, replacing spaces with hyphens, and removing special characters.




🔎 Proposed fix

-4. Security
-5. CLI Tool
-6. API Reference
+4. Security
+5. CLI Tool
+6. API Reference


Note: The anchor generation depends on the markdown processor. For the heading ## 🔐 Security & License Protection, most processors would 
generate #-security--license-protection (emoji prefix, ampersand removed). Verify by testing in your documentation renderer.

Prompt for AI Agent:
In docs/PROJECT_DOCUMENTATION.md around lines 14 to 16, the Table of 
Contents uses invalid anchor fragments that don’t match how markdown 
processors generate anchors (they lowercase, replace spaces with hyphens and strip/transform special characters and emoji); update each ToC link so it exactly matches the generated anchor for its heading (e.g., convert "Security" heading ## 🔐 Security & License Protection to the fragment that the renderer produces such as #-security--license-protection or the renderer-specific variant), apply the same transformation to the "CLI Tool" and "API Reference" links, and then verify the links by testing in the target markdown renderer.



============================================================================
File: cli/wrappers.py
Line: 924 to 927
Type: potential_issue

Comment:
Busy-wait fallback blocks the CPU and is inefficient.

The fallback wait mechanism uses a busy-wait loop (while (Date.now() 
- start
🔎 Proposed fix using setTimeout with blocking alternative

     } catch (e) {
-        // Fallback if spawnSync fails: just wait 10 seconds        
-        const start = Date.now();
-        while (Date.now() - start

Prompt for AI Agent:
In cli/wrappers.py around lines 924 to 927, replace the busy-wait loop that blocks the CPU for 10 seconds with a non-blocking sleep: remove the while(Date.now() - start < 10000) {} and use a proper async delay (e.g., a Promise-based setTimeout and await it, or time.sleep(10) 
if this is Python) so the event loop / thread isn’t pegged; if you switch to await ensure the enclosing function is async or otherwise use a callback-based setTimeout, and preserve existing error handling and control flow after the delay.



============================================================================
File: frontend/src/components/Layout.jsx
Line: 226
Type: potential_issue

Comment:
Minor typo: extra space before closing bracket.

There's an extraneous space in the closing tag.



Proposed fix

-
+

Prompt for AI Agent:
In frontend/src/components/Layout.jsx around line 226, the closing div tag contains an extraneous space before the closing angle bracket (""); remove the extra space so the tag is a proper "" and re-run the 
project's linter/formatter to ensure no other trivial spacing issues 
remain.



============================================================================
File: server/routes/auth_routes.py
Line: 172
Type: potential_issue

Comment:
Missing email normalization in admin-reset-password endpoint.        

The admin-reset-password endpoint queries the database with the raw email parameter without normalizing it (lowercase + strip), which is inconsistent with the register/login flows. This could cause lookups to fail for emails stored in lowercase.




🔎 Proposed fix

 @router.post("/admin-reset-password")
 async def admin_reset_password(
     email: str, new_password: str, admin_user: dict = Depends(get_current_admin_user)
 ):
     """Admin endpoint to reset any user's password (admin auth required)"""
+    # Normalize email to match stored format
+    email = email.lower().strip()
+
     if len(new_password)

Prompt for AI Agent:
In server/routes/auth_routes.py around line 172, the admin-reset-password endpoint currently queries users with the raw email parameter which can mismatch stored lowercase emails; normalize the incoming email by stripping whitespace and lowercasing it (e.g., email = email.strip().lower()) before any database lookup or further processing, and use that normalized value in the SELECT query and any subsequent logic to match register/login behavior.



============================================================================
File: requirements.txt
Line: 8
Type: potential_issue

Comment:
Update urllib3 to resolve three HIGH severity vulnerabilities in transitive dependencies.

The requests>=2.28.0 dependency brings in urllib3, which is affected 
by three confirmed HIGH severity vulnerabilities:

1. GHSA-2xpw-w6gg-jr37 (CVE-2025-66471): Highly compressed HTTP response bodies can be fully decompressed into an internal buffer even when only a small chunk is requested, causing excessive CPU and memory use.
2. GHSA-gm62-xv2j-4w53 (CVE-2025-66418): Unbounded decompression chains (e.g., gzip, zstd) allow a malicious server to craft many chained 
encodings causing denial of service.
3. GHSA-pq67-6m6q-mj2v (CVE-2025-50181): PoolManager-level configuration fails to reliably disable redirects when retries are disabled, leaving applications vulnerable to SSRF/open-redirect attacks.

All three affect urllib3 < 2.6.0 (third issue fixed in 2.5.0; first two in 2.6.0). Update requests to a version that depends on urllib3 ≥ 
2.6.0, or explicitly pin urllib3 to ≥ 2.6.0 in requirements.txt.     




============================================================================
File: cli/lw_compiler.py
Line: 1010 to 1012
Type: potential_issue

Comment:
Unreachable exception handler - timeout not implemented.

The TimeoutExpired exception at line 1010 can never be raised because:
1. subprocess.Popen doesn't accept a timeout parameter
2. The process.wait() at line 998 doesn't specify a timeout

The "10 minutes" timeout mentioned in the error message is not actually enforced.



Proposed fix to implement actual timeout

-        process.wait()
+        try:
+            process.wait(timeout=600)  # 10 minutes
+        except subprocess.TimeoutExpired:
+            process.kill()
+            process.wait()
+            print("[ERROR] Compilation timed out (10 minutes)", flush=True)
+            return False

         if process.returncode == 0:


And remove the unreachable except subprocess.TimeoutExpired block at 
lines 1010-1012.




============================================================================
File: server/email_service.py
Line: 172 to 175
Type: potential_issue

Comment:
Deprecated asyncio.get_event_loop() usage.

In Python 3.10+, asyncio.get_event_loop() is deprecated when called from a coroutine. Use asyncio.get_running_loop() instead.



🔎 Suggested fix

     async def send_async(self, message: EmailMessage) -> bool:      
         """Send email asynchronously."""
-        loop = asyncio.get_event_loop()
+        loop = asyncio.get_running_loop()
         return await loop.run_in_executor(_executor, self.send, message)

Prompt for AI Agent:
In server/email_service.py around lines 172 to 175, replace the deprecated asyncio.get_event_loop() call with asyncio.get_running_loop() when inside the coroutine; so obtain the running loop via asyncio.get_running_loop() and then await loop.run_in_executor(_executor, self.send, message) to run the blocking send in the executor (no other behavioral changes).



============================================================================
File: server/main.py
Line: 148
Type: potential_issue

Comment:
Nuitka availability check is always true if Python is installed.     

shutil.which("nuitka") or shutil.which("python") is not None will return True whenever Python is installed, even if Nuitka isn't. This doesn't accurately reflect Nuitka availability.



🔎 Suggested fix

     nodejs_available = shutil.which("pkg") is not None
-    nuitka_available = shutil.which("nuitka") or shutil.which("python") is not None
+    nuitka_available = shutil.which("nuitka") is not None


If the intent is to check if Nuitka can be installed (Python exists), make that explicit:
nuitka_installed = shutil.which("nuitka") is not None
python_available = shutil.which("python") is not None

Prompt for AI Agent:
In server/main.py around line 148, the expression shutil.which("nuitka") or shutil.which("python") is not None always evaluates true when 
Python is present, so it does not correctly detect whether Nuitka is 
installed; replace it with an explicit check such as setting nuitka_available = shutil.which("nuitka") is not None and, if you need to know whether Python exists separately, set python_available = shutil.which("python") is not None, then use those booleans where appropriate. 



============================================================================
File: server/main.py
Line: 1062
Type: potential_issue

Comment:
CLI_VERSION is duplicated from config.py.

CLI_VERSION = "1.0.0" is defined here but also in config.py (line 57). This could lead to version drift.



🔎 Suggested fix

-CLI_VERSION = "1.0.0"
+from config import CLI_VERSION


And remove the local definition, or ensure the config import includes CLI_VERSION.

Prompt for AI Agent:
In server/main.py around line 1062, the local constant CLI_VERSION = 
"1.0.0" duplicates the definition in config.py (line 57) and risks version drift; remove this local definition and instead import and use 
the canonical value from config.py (either add "from config import CLI_VERSION" at the module top or reference "config.CLI_VERSION" where 
used), or if config.py doesn't currently export it, add CLI_VERSION to config.py's public exports and then import it here.



============================================================================
File: server/compilers/templates/nodejs_license_wrapper.js
Line: 177 to 193
Type: potential_issue

Comment:
CLOCK_DRIFT_MAX constant is defined but never used.

Line 85 defines CLOCK_DRIFT_MAX = 60 * 60 (1 hour), but validateLease only checks if currentTime > lease.expires_at without accounting for clock drift. This could cause issues if the local clock is slightly 
ahead.



🔎 Suggested fix to apply clock drift tolerance

 function validateLease(licenseKey, hwid) {
     const lease = loadLease();
     if (!lease) return { valid: false, message: 'No lease found' }; 
     if (lease.hwid !== hwid) return { valid: false, message: 'HWID mismatch' };

     const keyHash = crypto.createHash('sha256').update(licenseKey).digest('hex');
     if (lease.license_key_hash !== keyHash) return { valid: false, message: 'License mismatch' };

     const currentTime = Math.floor(Date.now() / 1000);
-    if (currentTime > lease.expires_at) return { valid: false, message: 'Lease expired' };
+    if (currentTime > lease.expires_at + CLOCK_DRIFT_MAX) return { valid: false, message: 'Lease expired' };

     const remaining = lease.expires_at - currentTime;

Prompt for AI Agent:
In server/compilers/templates/nodejs_license_wrapper.js around lines 
177 to 193, the validateLease expiry check ignores the CLOCK_DRIFT_MAX constant defined earlier; update the expiry logic to use CLOCK_DRIFT_MAX as a tolerance so small local clock skew doesn't falsely mark a lease expired (e.g., treat the lease as expired only when currentTime > lease.expires_at + CLOCK_DRIFT_MAX or equivalently currentTime - 
CLOCK_DRIFT_MAX > lease.expires_at), and optionally log a warning when the lease is within the drift window; ensure you reference the existing CLOCK_DRIFT_MAX constant instead of hardcoding a value.



============================================================================
File: server/main.py
Line: 1040 to 1043
Type: potential_issue

Comment:
Fallback to first .exe file is a security concern.

If the expected output file doesn't exist, the code falls back to the first .exe found in the output directory. An attacker who can write 
to this directory could inject a malicious executable.



🔎 Suggested fix

Remove the fallback and require exact filename match:

         if not output_file.exists():
-            exe_files = list(output_dir.glob("*.exe"))
-            if exe_files:
-                output_file = exe_files[0]
-            else:
-                raise HTTPException(status_code=404, detail="Compiled file not found")
+            raise HTTPException(status_code=404, detail="Compiled file not found")


Or, if fallback is needed, validate that the found file was created by this job (e.g., check creation time, store expected filename in DB).




============================================================================
File: server/email_service.py
Line: 141 to 151
Type: potential_issue

Comment:
SMTP connection not properly closed on errors before server.quit().  

If an exception occurs after server.starttls() or server.login() but 
before server.quit(), the connection may be left open.



🔎 Suggested fix using context manager pattern

     def _send_via_smtp(self, message: EmailMessage) -> bool:        
         """Send email via SMTP."""
+        server = None
         try:
             msg = MIMEMultipart("alternative")
             msg["Subject"] = message.subject
             msg["From"] = f"{EMAIL_FROM_NAME} "
             msg["To"] = message.to

             if message.text_body:
                 msg.attach(MIMEText(message.text_body, "plain"))    
             msg.attach(MIMEText(message.html_body, "html"))

             if SMTP_USE_TLS:
                 server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                 server.starttls()
             else:
                 server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)     

             if SMTP_USER and SMTP_PASSWORD:
                 server.login(SMTP_USER, SMTP_PASSWORD)

             server.sendmail(EMAIL_FROM, message.to, msg.as_string())-            server.quit()
             return True
         except Exception as e:
             print(f"[Email] SMTP error: {e}")
             return False
+        finally:
+            if server:
+                try:
+                    server.quit()
+                except Exception:
+                    pass

Prompt for AI Agent:
In server/email_service.py around lines 141 to 151, the SMTP connection is created and quit manually so if an exception occurs after starttls() or login() the connection can be left open; replace the current manual open/quit flow with a context manager (use "with smtplib.SMTP(...)" and "with smtplib.SMTP_SSL(...)" as appropriate) so the server is automatically closed on exceptions, move starttls(), login() and 
sendmail() inside the with-block, and remove the explicit server.quit(); alternatively, wrap the existing code in try/finally and call server.quit()/server.close() in finally to guarantee closure.



============================================================================
File: server/main.py
Line: 606 to 610
Type: potential_issue

Comment:
ZipFile extraction without member validation is a security risk (Zip 
Slip vulnerability).

zip_ref.extractall(source_dir) can be exploited if the ZIP contains entries with ../ paths, potentially writing files outside source_dir. 



🔎 Suggested fix with path validation

         try:
             with zipfile.ZipFile(zip_path, "r") as zip_ref:
-                zip_ref.extractall(source_dir)
+                for member in zip_ref.namelist():
+                    # Validate member path to prevent Zip Slip      
+                    member_path = (source_dir / member).resolve()   
+                    if not str(member_path).startswith(str(source_dir.resolve())):
+                        raise HTTPException(
+                            status_code=400,
+                            detail=f"Invalid ZIP: contains path traversal attempt"
+                        )
+                zip_ref.extractall(source_dir)
         except zipfile.BadZipFile:
             raise HTTPException(status_code=400, detail="Invalid ZIP file")




============================================================================
File: cli/lw_compiler.py
Line: 768 to 787
Type: potential_issue

Comment:
Downgrading to axios 0.27.2 introduces confirmed security vulnerabilities.

The code automatically downgrades axios from v1.x to 0.27.2 for pkg compatibility, but this target version contains two known CVEs:       

- CVE-2023-45857 — Prototype Pollution (affects axios versions >0.8.1 and <0.28.0)
- CVE-2025-27152 — SSRF and credential leakage with absolute URLs (affects axios <0.30.0)

The modification to user's package.json happens with only a brief console message and no security warning. Either use a non-vulnerable version of axios (e.g., latest 1.x, ≥1.8.2, or ≥0.30.0) or prominently warn users about the security implications before modifying their dependencies.




============================================================================
File: server/email_service.py
Line: 437
Type: potential_issue

Comment:
Using datetime.utcnow() which is deprecated in Python 3.12+.

datetime.utcnow() is deprecated. Use datetime.now(datetime.timezone.utc) instead.



🔎 Suggested fix

+from datetime import datetime, timezone
+
 # In create_license_revoked_email:
-            {datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")}  
+            {datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")}

Prompt for AI Agent:
In server/email_service.py around line 437, the template uses datetime.utcnow() which is deprecated; replace it with datetime.now(datetime.timezone.utc) when formatting the timestamp and ensure the timezone 
object is imported or referenced (e.g., import datetime or from datetime import timezone) so the call becomes datetime.now(datetime.timezone.utc).strftime(...) to produce the same UTC formatted string without using deprecated API.



============================================================================
File: server/compilers/templates/nodejs_license_wrapper.js
Line: 495 to 603
Type: potential_issue

Comment:
Async promise executor is an anti-pattern.

The static analysis correctly flags new Promise(async (resolve, reject) => {...}). If an exception is thrown before the first await, it won't reject the promise—it will crash. Additionally, reject is never called in this function.



🔎 Refactor to async/await pattern

-    return new Promise(async (resolve, reject) => {
+    return new Promise((resolve, reject) => {
         const hwid = getHWID();
         const nonce = crypto.randomBytes(16).toString('hex');       
         const timestamp = Math.floor(Date.now() / 1000);

         // Parse URL
         let urlObj;
         try {
             urlObj = new URL(API_URL);
         } catch (e) {
-            await exitWithError(Invalid API URL: ${API_URL}\n\nThis 
is a configuration error. Please contact the application developer.);+            exitWithError(Invalid API URL: ${API_URL}\n\nThis is a configuration error. Please contact the application developer.);      
+            return; // exitWithError calls process.exit, but guard for clarity
         }


Alternatively, refactor the entire validateLicense function to be purely async/await without wrapping in new Promise:

async function validateLicense() {
    // ... validation logic using await directly ...
    // Use util.promisify for http request or a promise-based HTTP client
}




============================================================================
File: frontend/src/components/Skeleton.jsx
Line: 90 to 98
Type: potential_issue

Comment:
Avoid Math.random() in render - causes unstable skeleton heights.    

Using Math.random() directly in JSX means the bar heights will change on every re-render, causing visual inconsistency and potential layout shifts. Skeleton loaders should have stable, predictable layouts.  


🔎 Proposed fix using deterministic heights

-
-            {[...Array(12)].map((_, i) => (
-
-            ))}
-
+
+            {[40, 65, 30, 80, 55, 45, 70, 35, 60, 50, 75, 40].map((height, i) => (
+
+            ))}
+

Prompt for AI Agent:
In frontend/src/components/Skeleton.jsx around lines 90 to 98, the JSX uses Math.random() directly inside render which produces different 
bar heights on every re-render; instead compute deterministic heights once and reuse them (e.g., create an array of 12 height values using Math.random() inside a useMemo or useState initialized on mount, or 
use a fixed array of percentages or a seeded RNG) and then map over that stable array to set each Skeleton's style so heights remain stable across renders.



============================================================================
File: server/routes/compile_helpers.py
Line: 627 to 630
Type: potential_issue

Comment:
Potential issue: Missing backup existence check.

Unlike inject_license_into_single_file (line 474), this function doesn't check if backup_file already exists before renaming. If the injection runs multiple times, the backup will be overwritten with already-injected code, potentially causing double-wrapped license validation.


🔎 Proposed fix

     backup_file = project_dir / f"_original_{entry_file.name}"      
-    entry_file.rename(backup_file)
+    if not backup_file.exists():
+        entry_file.rename(backup_file)
+    else:
+        # Backup exists, restore original content before re-injection
+        original_content = backup_file.read_text(encoding="utf-8")  

     entry_file.write_text(wrapper_code, encoding="utf-8")

Prompt for AI Agent:
In server/routes/compile_helpers.py around lines 627 to 630, the code renames entry_file to backup_file without checking whether backup_file already exists; add the same existence guard used in inject_license_into_single_file (line ~474): before renaming, if backup_file.exists() raise an error or abort (or choose a non-destructive alternative 
such as not overwriting or creating a unique backup name), so you never overwrite an existing original backup; ensure the check happens before entry_file.rename(...) and handle/report the error consistently 
with the other function.



============================================================================
File: server/requirements.txt
Line: 1 to 30
Type: potential_issue

Comment:
Address HIGH severity transitive urllib3 vulnerabilities with a compatible approach.

Static analysis detected confirmed HIGH severity vulnerabilities in urllib3 =2.6.0 is incompatible: boto3 1.34.0 depends on botocore 1.34.x, which constrains urllib3 to <1.27, making urllib3 2.6.0 installation impossible.

Recommended actions (in priority order):
1. Check if a newer boto3/botocore version is available that relaxes 
the urllib3 constraint to support 2.6.0+.
2. If upgrading boto3 is not viable, apply the urllib3 workarounds: disable automatic content decompression in boto3 HTTP config (set preload_content=False) and validate response headers before manual decoding, plus disable redirects per-request where applicable.
3. Otherwise, accept the vulnerability risk until boto3/botocore compatibility improves.

Prompt for AI Agent:
server/requirements.txt lines 1-30: the transitive urllib3 =2.6.0 by 
updating the requirement to a newer boto3/botocore that relaxes the urllib3 constraint, and run tests; if upgrading boto3 is not viable, implement the recommended workarounds where boto3/botocore HTTP responses are used: configure HTTP requests to avoid urllib3 automatic decompression (use botocore/boto3 client configuration to stream responses / disable preload_content and manually validate Content-Encoding/Content-Length before decoding) and ensure redirects are disabled per-request where applicable; if neither upgrade nor workarounds are feasible, document and accept the risk until compatible boto3/botocore versions are available.



Review completed ✔
PS C:\Users\parth\OneDrive\Desktop\Code Vault> 
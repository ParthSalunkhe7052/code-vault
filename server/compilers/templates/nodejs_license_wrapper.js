const crypto = require('crypto');
const os = require('os');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const child_process = require('child_process');

// Configuration (Injected by compiler)
const LICENSE_KEY = '{{LICENSE_KEY}}';
const API_URL = '{{API_URL}}'; // e.g. https://api.codevault.com/api/v1/license/validate

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

// Wait for user to press Enter before exiting (so they can read errors)
function waitForKeypress(message = 'Press Enter to exit...') {
    return new Promise((resolve) => {
        console.log('\n' + message);

        // If we have a TTY, wait for keypress
        if (process.stdin.isTTY) {
            process.stdin.setRawMode(true);
            process.stdin.resume();
            process.stdin.once('data', () => {
                resolve();
            });
        } else {
            // No TTY - wait a few seconds so user can see the error in the window
            setTimeout(resolve, 5000);
        }
    });
}

// Sanitize message for safe logging (prevent log injection)
function sanitizeLogMessage(msg) {
    if (typeof msg !== 'string') return String(msg);
    // Remove control characters and limit length
    return msg.replace(/[\x00-\x1f\x7f]/g, '').substring(0, 1000);
}

// Exit with error message (waits for keypress first)
async function exitWithError(message, code = 1) {
    console.error('\n' + '='.repeat(50));
    console.error('  ❌ ERROR');
    console.error('='.repeat(50));
    // Security: Sanitize directly in output call (CodeQL-recognized pattern)
    console.error(sanitizeLogMessage(String(message)));
    console.error('='.repeat(50));
    await waitForKeypress();
    process.exit(code);
}

// Helper to get HWID
function getHWID() {
    try {
        const cpus = os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${os.hostname()}|${os.platform()}|${os.arch()}|${os.totalmem()}|${cpuModel}`;
        return crypto.createHash('sha256').update(info).digest('hex');
    } catch (e) {
        return 'unknown-hwid';
    }
}

// Get the directory where the executable is located
function getExeDir() {
    // For pkg-compiled executables, process.execPath points to the exe
    if (process.pkg) {
        return path.dirname(process.execPath);
    }
    return __dirname;
}

// Get the license key file path
function getLicenseKeyPath() {
    const exeDir = getExeDir();
    const keyPath = path.join(exeDir, 'license.key');
    
    // Test if we can write to this location
    try {
        const testFile = path.join(exeDir, '.cv_write_test');
        fs.writeFileSync(testFile, 'test');
        fs.unlinkSync(testFile);
        return keyPath;
    } catch (e) {
        // Fall back to user's home directory if exe dir is not writable
        console.log(`[CodeVault] Warning: Cannot write to ${exeDir}, using home directory`);
        const homeDir = os.homedir();
        const appDataDir = path.join(homeDir, '.codevault');
        try {
            if (!fs.existsSync(appDataDir)) {
                fs.mkdirSync(appDataDir, { recursive: true });
            }
            return path.join(appDataDir, 'license.key');
        } catch (err) {
            // Final fallback
            return path.join(homeDir, 'license.key');
        }
    }
}

// ============================================================
// LEASE CONFIGURATION
// ============================================================

const LEASE_DURATION = 24 * 60 * 60;  // 24 hours
const CLOCK_DRIFT_MAX = 60 * 60;       // 1 hour

function getLeasePath() {
    // Use same directory as license.key file
    const licensePath = getLicenseKeyPath();
    const leaseDir = path.dirname(licensePath);
    return path.join(leaseDir, 'license.lease');
}

function getMachineSecret() {
    const info = `${os.hostname()}|${os.platform()}|${os.arch()}|LW_SALT_2026`;
    return crypto.createHash('sha256').update(info).digest();
}

function encryptLease(leaseData) {
    try {
        const secret = getMachineSecret();
        const dataJson = Buffer.from(JSON.stringify(leaseData), 'utf-8');

        // Use AES-256-GCM
        const nonce = crypto.randomBytes(12);
        const cipher = crypto.createCipheriv('aes-256-gcm', secret, nonce);
        const encrypted = Buffer.concat([cipher.update(dataJson), cipher.final()]);
        const authTag = cipher.getAuthTag();

        return Buffer.concat([
            Buffer.from('AES:'),
            nonce,
            authTag,
            encrypted
        ]).toString('base64');
    } catch (e) {
        return null;
    }
}

function decryptLease(encryptedData) {
    try {
        const secret = getMachineSecret();
        const raw = Buffer.from(encryptedData, 'base64');

        if (raw.slice(0, 4).toString() === 'AES:') {
            const nonce = raw.slice(4, 16);
            const authTag = raw.slice(16, 32);
            const encrypted = raw.slice(32);

            const decipher = crypto.createDecipheriv('aes-256-gcm', secret, nonce);
            decipher.setAuthTag(authTag);
            const dataJson = Buffer.concat([decipher.update(encrypted), decipher.final()]);
            return JSON.parse(dataJson.toString('utf-8'));
        }
        return null;
    } catch (e) {
        return null;
    }
}

function createLease(licenseKey, hwid, serverTime) {
    return {
        license_key_hash: crypto.createHash('sha256').update(licenseKey).digest('hex'),
        hwid: hwid,
        expires_at: serverTime + LEASE_DURATION,
        server_time: serverTime,
        validated_at: Math.floor(Date.now() / 1000)
    };
}

function saveLease(leaseData) {
    try {
        const leasePath = getLeasePath();
        const encrypted = encryptLease(leaseData);
        if (encrypted) {
            fs.writeFileSync(leasePath, encrypted, 'utf-8');
            console.log('[License] Lease saved (24h offline access)');
            return true;
        }
    } catch (e) {
        // Ignore
    }
    return false;
}

function loadLease() {
    try {
        const leasePath = getLeasePath();
        if (fs.existsSync(leasePath)) {
            const encrypted = fs.readFileSync(leasePath, 'utf-8').trim();
            return decryptLease(encrypted);
        }
    } catch (e) {
        // Ignore
    }
    return null;
}

function validateLease(licenseKey, hwid) {
    const lease = loadLease();
    if (!lease) return { valid: false, message: 'No lease found' };
    if (lease.hwid !== hwid) return { valid: false, message: 'HWID mismatch' };

    const keyHash = crypto.createHash('sha256').update(licenseKey).digest('hex');
    if (lease.license_key_hash !== keyHash) return { valid: false, message: 'License mismatch' };

    const currentTime = Math.floor(Date.now() / 1000);
    if (currentTime > lease.expires_at) return { valid: false, message: 'Lease expired' };

    const remaining = lease.expires_at - currentTime;
    const hours = Math.floor(remaining / 3600);
    const mins = Math.floor((remaining % 3600) / 60);
    console.log(`[License] Offline lease valid (${hours}h ${mins}m remaining)`);
    return { valid: true, message: 'Valid' };
}

function deleteSavedLicenseAndLease() {
    try {
        const licensePath = getLicenseKeyPath();
        if (fs.existsSync(licensePath)) fs.unlinkSync(licensePath);
        const leasePath = getLeasePath();
        if (fs.existsSync(leasePath)) fs.unlinkSync(leasePath);
    } catch (e) { /* ignore */ }
}

// ============================================================
// LICENSE KEY PROMPTING
// ============================================================

// GUI Prompt using HTML dialog in default browser (modern, matches Python tkinter style)
function promptGUI() {
    return new Promise((resolve) => {
        const http = require('http');
        const querystring = require('querystring');
        
        let licenseKey = null;
        let server = null;

        // Find available port
        const getPort = () => {
            return new Promise((portResolve) => {
                const testServer = http.createServer();
                testServer.listen(0, '127.0.0.1', () => {
                    const port = testServer.address().port;
                    testServer.close(() => portResolve(port));
                });
            });
        };

        getPort().then(port => {
            // Create HTTP server for validation
            server = http.createServer(async (req, res) => {
                // CORS headers
                res.setHeader('Access-Control-Allow-Origin', '*');
                res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
                res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

                if (req.method === 'OPTIONS') {
                    res.writeHead(200);
                    res.end();
                    return;
                }

                if (req.url === '/' && req.method === 'GET') {
                    // Serve HTML dialog
                    const htmlContent = getHtmlDialog(API_URL, port);
                    res.writeHead(200, { 'Content-Type': 'text/html' });
                    res.end(htmlContent);
                } else if (req.url === '/validate' && req.method === 'POST') {
                    // Handle license validation
                    let body = '';
                    req.on('data', chunk => body += chunk);
                    req.on('end', async () => {
                        try {
                            const data = JSON.parse(body);
                            const key = data.license_key;

                            // Validate with server
                            const hwid = getHWID();
                            const nonce = crypto.randomBytes(16).toString('hex');
                            const timestamp = Math.floor(Date.now() / 1000);

                            const validationResult = await validateWithServer(key, hwid, nonce, timestamp);

                            if (validationResult.success) {
                                licenseKey = key;
                                res.writeHead(200, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ success: true, message: 'License activated successfully!' }));
                            } else {
                                res.writeHead(200, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ success: false, message: validationResult.message }));
                            }
                        } catch (e) {
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ success: false, message: 'Validation error' }));
                        }
                    });
                } else if (req.url === '/activation-complete' && req.method === 'POST') {
                    res.writeHead(200);
                    res.end();
                    // Close server after successful activation
                    setTimeout(() => {
                        server.close();
                        resolve(licenseKey);
                    }, 500);
                } else {
                    res.writeHead(404);
                    res.end();
                }
            });

            server.listen(port, '127.0.0.1', () => {
                console.log(`[CodeVault] License activation server started on port ${port}`);
                // Open browser
                const url = `http://127.0.0.1:${port}`;
                const start = os.platform() === 'win32' ? 'start' : os.platform() === 'darwin' ? 'open' : 'xdg-open';
                child_process.exec(`${start} ${url}`, (error) => {
                    if (error) {
                        console.error('[CodeVault] Failed to open browser:', error.message);
                        console.log(`[CodeVault] Please open this URL manually: ${url}`);
                    }
                });
            });

            // Timeout after 5 minutes
            setTimeout(() => {
                if (!licenseKey) {
                    server.close();
                    resolve(null);
                }
            }, 5 * 60 * 1000);
        }).catch(error => {
            console.error('[CodeVault] Failed to start license server:', error);
            resolve(null);
        });
    });
}

// Helper function to validate with server
function validateWithServer(key, hwid, nonce, timestamp) {
    return new Promise((resolve) => {
        try {
            const urlObj = new URL(API_URL);
            const postData = JSON.stringify({
                license_key: key,
                hwid: hwid,
                nonce: nonce,
                timestamp: timestamp,
                machine_name: os.hostname()
            });

            const hostname = urlObj.hostname === 'localhost' ? '127.0.0.1' : urlObj.hostname;
            const options = {
                hostname: hostname,
                port: urlObj.port || (urlObj.protocol === 'http:' ? 80 : 443),
                path: urlObj.pathname,
                method: 'POST',
                family: 4,
                timeout: 15000,
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            };

            const lib = urlObj.protocol === 'http:' ? require('http') : require('https');
            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {
                    try {
                        if (res.statusCode !== 200) {
                            resolve({ success: false, message: `Server error (HTTP ${res.statusCode})` });
                            return;
                        }
                        const response = JSON.parse(body);
                        if (response.status === 'valid') {
                            resolve({ success: true, message: 'License valid' });
                        } else {
                            resolve({ success: false, message: response.message || 'Invalid license' });
                        }
                    } catch (e) {
                        resolve({ success: false, message: 'Failed to parse server response' });
                    }
                });
            });

            req.on('error', (e) => {
                resolve({ success: false, message: `Connection error: ${e.message}` });
            });

            req.on('timeout', () => {
                req.destroy();
                resolve({ success: false, message: 'Connection timeout' });
            });

            req.write(postData);
            req.end();
        } catch (error) {
            resolve({ success: false, message: `Validation error: ${error.message}` });
        }
    });
}

// HTML dialog content
function getHtmlDialog(apiUrl, port) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>License Activation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(22, 33, 62, 0.9);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 100px rgba(233, 69, 96, 0.1);
            border: 1px solid rgba(233, 69, 96, 0.2);
        }
        .icon { font-size: 48px; text-align: center; margin-bottom: 20px; }
        h1 { color: #e94560; font-size: 24px; font-weight: 600; text-align: center; margin-bottom: 8px; }
        .subtitle { color: #aaaaaa; font-size: 14px; text-align: center; margin-bottom: 30px; }
        .brand { color: #64748b; font-size: 12px; text-align: center; margin-bottom: 20px; }
        label { display: block; color: #888888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        input[type="text"] {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            font-family: 'Consolas', 'Monaco', monospace;
            background: #0f0f23;
            border: 2px solid #2a2a4e;
            border-radius: 8px;
            color: #ffffff;
            transition: all 0.3s ease;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #e94560;
            box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.2);
        }
        button {
            width: 100%;
            padding: 14px 24px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #e94560 0%, #c73e54 100%);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(233, 69, 96, 0.4);
        }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .status {
            margin-top: 20px;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            text-align: center;
            display: none;
        }
        .status.error { display: block; background: rgba(233, 69, 96, 0.15); border: 1px solid rgba(233, 69, 96, 0.3); color: #e94560; }
        .status.success { display: block; background: rgba(0, 204, 102, 0.15); border: 1px solid rgba(0, 204, 102, 0.3); color: #00cc66; }
        .status.loading { display: block; background: rgba(74, 144, 217, 0.15); border: 1px solid rgba(74, 144, 217, 0.3); color: #4a90d9; }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(74, 144, 217, 0.3);
            border-top-color: #4a90d9;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .success-view { display: none; text-align: center; }
        .success-icon { font-size: 64px; animation: pulse 0.5s ease; }
        @keyframes pulse { 0% { transform: scale(0); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
        .success-message h2 { color: #00cc66; font-size: 22px; margin: 20px 0 10px; }
        .success-message p { color: #aaaaaa; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container" id="activationForm">
        <div class="brand">Protected by CodeVault</div>
        <div class="icon">🔐</div>
        <h1>License Activation</h1>
        <p class="subtitle">Enter your license key to activate this application</p>
        <form id="licenseForm">
            <label for="licenseKey">License Key</label>
            <input type="text" id="licenseKey" placeholder="LIC-XXXX-XXXX-XXXX" autocomplete="off" autofocus>
            <button type="submit" id="submitBtn">✓ Activate License</button>
        </form>
        <div class="status" id="status"></div>
    </div>
    <div class="container success-view" id="successView">
        <div class="success-icon">✅</div>
        <div class="success-message">
            <h2>License Activated!</h2>
            <p>You can close this window. The application will start automatically.</p>
        </div>
    </div>
    <script>
        const form = document.getElementById('licenseForm');
        const input = document.getElementById('licenseKey');
        const submitBtn = document.getElementById('submitBtn');
        const status = document.getElementById('status');
        const activationForm = document.getElementById('activationForm');
        const successView = document.getElementById('successView');

        function setStatus(message, type) {
            status.className = 'status ' + type;
            if (type === 'loading') {
                status.innerHTML = '<span class="spinner"></span>' + message;
            } else {
                status.textContent = message;
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const licenseKey = input.value.trim();
            if (!licenseKey) {
                setStatus('⚠️ Please enter a license key', 'error');
                return;
            }
            submitBtn.disabled = true;
            submitBtn.textContent = 'Validating...';
            setStatus('Connecting to license server...', 'loading');

            try {
                const response = await fetch('http://127.0.0.1:${port}/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ license_key: licenseKey })
                });
                const result = await response.json();
                if (result.success) {
                    setStatus('✅ ' + result.message, 'success');
                    activationForm.style.display = 'none';
                    successView.style.display = 'block';
                    fetch('http://127.0.0.1:${port}/activation-complete', { method: 'POST' }).catch(() => {});
                    setTimeout(() => window.close(), 2000);
                } else {
                    setStatus('❌ ' + result.message, 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '✓ Activate License';
                }
            } catch (error) {
                setStatus('❌ Connection error. Please try again.', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = '✓ Activate License';
            }
        });

        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
        });
    </script>
</body>
</html>`;
}

// Console prompt for license key
function promptConsole() {
    return new Promise((resolve) => {
        try {
            process.stdin.resume();

            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout,
                terminal: true
            });

            console.log('\n' + '='.repeat(50));
            console.log('  LICENSE KEY REQUIRED');
            console.log('  (Right-click to paste, or use Ctrl+V)');
            console.log('='.repeat(50));

            rl.question('Enter License Key: ', (answer) => {
                rl.close();
                const key = answer ? answer.trim() : null;
                resolve(key);
            });
        } catch (e) {
            console.error('[CodeVault] Console prompt error:', e.message);
            resolve(null);
        }
    });
}

// Main prompt function - ALWAYS use GUI on Windows to avoid console paste issues
async function promptForLicenseKey() {
    // On Windows, ALWAYS use GUI dialog
    // Console has issues with select mode (clicking pauses the app) and paste (Ctrl+V)
    if (os.platform() === 'win32') {
        console.log('[CodeVault] Opening license key dialog...');
        const key = await promptGUI();
        if (key) return key;

        // GUI failed - try console as fallback if we have a TTY
        if (process.stdin.isTTY) {
            console.log('[CodeVault] GUI dialog failed, falling back to console input...');
            return await promptConsole();
        }
        return null;
    }

    // Use console prompt
    return await promptConsole();
}

// Load license from file or prompt user
async function loadOrPromptLicense() {
    const licensePath = getLicenseKeyPath();

    console.log('[CodeVault] License file path:', licensePath);

    // Try to load from file first
    if (fs.existsSync(licensePath)) {
        try {
            const key = fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {
                console.log('[CodeVault] ✓ Loaded license from file.');
                return key;
            }
        } catch (e) {
            console.log('[CodeVault] Warning: Could not read license file:', e.message);
        }
    }

    // Prompt for license
    console.log('[CodeVault] No license key found. Please enter your license key.');
    const licenseKey = await promptForLicenseKey();

    if (!licenseKey) {
        await exitWithError('No license key provided.\n\nPlease run the application again and enter a valid license key.');
    }

    // Sconst licenseDir = path.dirname(licensePath);
        if (!fs.existsSync(licenseDir)) {
            fs.mkdirSync(licenseDir, { recursive: true });
        }
        ave license for future runs (atomic write to prevent race conditions)
    console.log('[CodeVault] Saving license key...');
    try {
        // Write to temp file first, then rename (atomic operation)
        const tempPath = licensePath + '.tmp.' + crypto.randomBytes(8).toString('hex');
        fs.writeFileSync(tempPath, licenseKey, { encoding: 'utf-8', mode: 0o600 });
        fs.renameSync(tempPath, licensePath);
        console.log('[CodeVault] ✓ License key saved to:', sanitizeLogMessage(licensePath));
    } catch (e) {
        const safeError = sanitizeLogMessage(e.message);
        console.error('[CodeVault] ⚠ Could not save license file:', safeError);
        console.error('[CodeVault] You may need to enter the license key again next time.');
        // Don't exit - continue with validation
    }

    return licenseKey;
}

// Delete saved license file (on validation failure)
function deleteSavedLicense() {
    try {
        const licensePath = getLicenseKeyPath();
        if (fs.existsSync(licensePath)) {
            fs.unlinkSync(licensePath);
            console.log('[CodeVault] License file removed due to validation failure.');
        }
    } catch (e) {
        // Ignore cleanup errors
    }
}

// ============================================================
// LICENSE VALIDATION
// ============================================================

async function validateLicense() {
    let currentLicenseKey = LICENSE_KEY;

    // DEMO mode - skip all validation
    if (currentLicenseKey === 'DEMO') {
        console.log('[CodeVault] Running in DEMO mode');
        return true;
    }

    // GENERIC_BUILD mode - prompt for license at runtime
    if (currentLicenseKey === 'GENERIC_BUILD') {
        currentLicenseKey = await loadOrPromptLicense();
    }

    console.log('[CodeVault] Validating license with server...');
    console.log('[CodeVault] Server URL:', API_URL);

    return new Promise(async (resolve, reject) => {
        const hwid = getHWID();
        const nonce = crypto.randomBytes(16).toString('hex');
        const timestamp = Math.floor(Date.now() / 1000);

        // Parse URL
        let urlObj;
        try {
            urlObj = new URL(API_URL);
        } catch (e) {
            await exitWithError(`Invalid API URL: ${API_URL}\n\nThis is a configuration error. Please contact the application developer.`);
        }

        const postData = JSON.stringify({
            license_key: currentLicenseKey,
            hwid: hwid,
            nonce: nonce,
            timestamp: timestamp,
            machine_name: os.hostname()
        });

        // CRITICAL: Replace 'localhost' with '127.0.0.1' to force IPv4
        // Windows DNS resolves 'localhost' to IPv6 (::1) first, causing ECONNREFUSED
        const hostname = urlObj.hostname === 'localhost' ? '127.0.0.1' : urlObj.hostname;

        const options = {
            hostname: hostname,
            port: urlObj.port || (urlObj.protocol === 'http:' ? 80 : 443),
            path: urlObj.pathname,
            method: 'POST',
            family: 4, // Force IPv4
            timeout: 15000, // 15 second timeout
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        console.log('[CodeVault] Connecting to:', `${urlObj.protocol}//${hostname}:${options.port}${options.path}`);

        const lib = urlObj.protocol === 'http:' ? require('http') : require('https');

        const req = lib.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', async () => {
                try {
                    if (res.statusCode !== 200) {
                        console.error('[CodeVault] Server returned HTTP', res.statusCode);
                        if (LICENSE_KEY === 'GENERIC_BUILD') {
                            deleteSavedLicense();
                        }
                        await exitWithError(`License validation failed.\n\nServer returned HTTP ${res.statusCode}\nResponse: ${body.substring(0, 200)}`);
                    }

                    const response = JSON.parse(body);

                    if (response.status === 'valid') {
                        console.log('[CodeVault] ✓ License validated successfully!');

                        // Create lease for offline use
                        const serverTime = response.server_time || response.timestamp || Math.floor(Date.now() / 1000);
                        const localTime = Math.floor(Date.now() / 1000);
                        const drift = Math.abs(localTime - serverTime);

                        if (drift <= CLOCK_DRIFT_MAX) {
                            const lease = createLease(currentLicenseKey, hwid, serverTime);
                            saveLease(lease);
                        } else {
                            console.log(`[CodeVault] Clock drift detected (${drift}s), lease not saved`);
                        }

                        resolve(true);
                    } else {
                        const errorMsg = response.message || 'License key is invalid or expired';
                        console.error('[CodeVault] License invalid:', errorMsg);
                        if (LICENSE_KEY === 'GENERIC_BUILD') {
                            deleteSavedLicense();
                        }
                        await exitWithError(`License validation failed.\n\n${errorMsg}\n\nPlease check your license key and try again.`);
                    }
                } catch (e) {
                    console.error('[CodeVault] Failed to parse server response');
                    await exitWithError(`Failed to parse license server response.\n\nResponse: ${body.substring(0, 200)}\n\nPlease contact the application developer.`);
                }
            });
        });

        // Handle connection errors - try offline lease first
        req.on('error', async (e) => {
            // Security: Sanitize error message to prevent log injection
            const safeErrorMessage = sanitizeLogMessage(e.message || 'Unknown error');
            console.error('[CodeVault] Connection error:', safeErrorMessage);
            console.log('[CodeVault] Server unreachable, checking offline lease...');

            // Try offline lease validation
            const leaseResult = validateLease(currentLicenseKey, hwid);
            if (leaseResult.valid) {
                console.log('[CodeVault] ✓ Running with valid offline lease');
                resolve(true);
                return;
            }

            // No valid lease - show error
            console.log(`[CodeVault] Offline lease invalid: ${leaseResult.message}`);

            let helpText = '';
            if (e.code === 'ECONNREFUSED') {
                helpText = `\nThe license server at ${API_URL} is not responding.\n\nPossible causes:\n1. The server is not running\n2. Firewall is blocking the connection\n3. Wrong server URL configured\n\nPlease ensure the license server is running and accessible.`;
            } else if (e.code === 'ETIMEDOUT' || e.code === 'ESOCKETTIMEDOUT') {
                helpText = `\nConnection to ${API_URL} timed out.\n\nPossible causes:\n1. Server is overloaded\n2. Network issues\n3. Firewall blocking connection\n\nPlease check your internet connection and try again.`;
            } else if (e.code === 'ENOTFOUND') {
                helpText = `\nCould not resolve hostname: ${urlObj.hostname}\n\nPossible causes:\n1. No internet connection\n2. DNS server issues\n3. Invalid server URL\n\nPlease check your internet connection.`;
            } else {
                helpText = `\nNetwork error: ${safeErrorMessage}\n\nPlease check your internet connection and try again.`;
            }

            await exitWithError(`Cannot connect to license server.${helpText}\n\nOffline lease: ${leaseResult.message}`);
        });

        // Handle timeout - try offline lease first
        req.on('timeout', async () => {
            req.destroy();
            console.log('[CodeVault] Connection timeout, checking offline lease...');

            // Try offline lease validation
            const leaseResult = validateLease(currentLicenseKey, hwid);
            if (leaseResult.valid) {
                console.log('[CodeVault] ✓ Running with valid offline lease');
                resolve(true);
                return;
            }

            // No valid lease - show error
            console.log(`[CodeVault] Offline lease invalid: ${leaseResult.message}`);
            const safeUrl = sanitizeLogMessage(API_URL);
            await exitWithError(`Connection to license server timed out.\n\nThe server at ${safeUrl} is not responding.\nPlease try again later.\n\nOffline lease: ${leaseResult.message}`);
        });

        // lgtm[js/file-access-to-http] - Intentional: license key from file sent for validation
        // This is the core purpose of the license wrapper - sending the stored key for server validation
        req.write(postData);
        req.end();
    });
}

// Export validation function
module.exports = validateLicense;

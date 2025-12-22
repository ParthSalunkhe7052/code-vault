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
    const safeMessage = sanitizeLogMessage(message);
    console.error('\n' + '='.repeat(50));
    console.error('  ❌ ERROR');
    console.error('='.repeat(50));
    console.error(safeMessage);
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
    return path.join(getExeDir(), 'license.key');
}

// ============================================================
// LICENSE KEY PROMPTING
// ============================================================

// GUI Prompt for Windows using VBScript (with better error handling)
function promptGUI() {
    return new Promise((resolve) => {
        const vbsScript = `
Option Explicit
Dim result
result = InputBox("Please enter your License Key to continue:", "License Required", "")
If IsEmpty(result) Then
    WScript.Echo ""
Else
    WScript.Echo result
End If
        `.trim();

        // Use crypto.randomBytes for secure, unpredictable temp file name
        const randomSuffix = crypto.randomBytes(16).toString('hex');
        const vbsPath = path.join(os.tmpdir(), `cv_input_${randomSuffix}.vbs`);

        console.log('[CodeVault] Opening license key dialog...');

        try {
            // Use exclusive create mode to prevent race conditions
            const fd = fs.openSync(vbsPath, fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY, 0o600);
            fs.writeSync(fd, vbsScript, 0, 'utf-8');
            fs.closeSync(fd);

            // Use spawnSync for more reliable execution
            const result = child_process.spawnSync('cscript', ['//Nologo', vbsPath], {
                encoding: 'utf-8',
                timeout: 120000  // 2 minute timeout
            });

            // Cleanup VBS file
            try { fs.unlinkSync(vbsPath); } catch (e) { }

            if (result.error) {
                console.error('[CodeVault] GUI prompt error:', result.error.message);
                resolve(null);
                return;
            }

            const key = (result.stdout || '').trim();
            if (key) {
                console.log('[CodeVault] License key received from dialog.');
                resolve(key);
            } else {
                console.log('[CodeVault] Dialog was cancelled or empty.');
                resolve(null);
            }

        } catch (e) {
            console.error('[CodeVault] Failed to show GUI dialog:', e.message);
            try { fs.unlinkSync(vbsPath); } catch (e2) { }
            resolve(null);
        }
    });
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

    // Save license for future runs (atomic write to prevent race conditions)
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

        // Handle connection errors
        req.on('error', async (e) => {
            console.error('[CodeVault] Connection error:', e.message);

            let helpText = '';
            if (e.code === 'ECONNREFUSED') {
                helpText = `\nThe license server at ${API_URL} is not responding.\n\nPossible causes:\n1. The server is not running\n2. Firewall is blocking the connection\n3. Wrong server URL configured\n\nPlease ensure the license server is running and accessible.`;
            } else if (e.code === 'ETIMEDOUT' || e.code === 'ESOCKETTIMEDOUT') {
                helpText = `\nConnection to ${API_URL} timed out.\n\nPossible causes:\n1. Server is overloaded\n2. Network issues\n3. Firewall blocking connection\n\nPlease check your internet connection and try again.`;
            } else if (e.code === 'ENOTFOUND') {
                helpText = `\nCould not resolve hostname: ${urlObj.hostname}\n\nPossible causes:\n1. No internet connection\n2. DNS server issues\n3. Invalid server URL\n\nPlease check your internet connection.`;
            } else {
                helpText = `\nNetwork error: ${e.message}\n\nPlease check your internet connection and try again.`;
            }

            await exitWithError(`Cannot connect to license server.${helpText}`);
        });

        // Handle timeout
        req.on('timeout', async () => {
            req.destroy();
            await exitWithError(`Connection to license server timed out.\n\nThe server at ${API_URL} is not responding.\nPlease try again later.`);
        });

        req.write(postData);
        req.end();
    });
}

// Export validation function
module.exports = validateLicense;

const crypto = require('crypto');
const os = require('os');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const child_process = require('child_process');

// Configuration (Injected by compiler)
const LICENSE_KEY = '{{LICENSE_KEY}}';
const API_URL = '{{API_URL}}'; // e.g. https://api.codevault.com/api/v1/license/validate

// Track temp files for cleanup
const tempFiles = new Set();

// Cleanup temp files on exit
process.on('exit', () => {
    for (const file of tempFiles) {
        try { fs.unlinkSync(file); } catch (e) { /* ignore */ }
    }
});

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

// Native GUI Prompt using PowerShell (matches Python tkinter style)
function promptNativeGUI() {
    return new Promise((resolve) => {
        // PowerShell script to create a native Windows Form dialog matching the Python tkinter style
        const psScript = `
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = 'License Activation'
$form.Size = New-Object System.Drawing.Size(470, 350)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.ColorTranslator]::FromHtml('#1a1a2e')
$form.ForeColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font('Segoe UI', 10)

# Branding label
$brandLabel = New-Object System.Windows.Forms.Label
$brandLabel.Text = 'Protected by CodeVault'
$brandLabel.Location = New-Object System.Drawing.Point(0, 20)
$brandLabel.Size = New-Object System.Drawing.Size(450, 20)
$brandLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#888888')
$brandLabel.TextAlign = 'MiddleCenter'
$brandLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$form.Controls.Add($brandLabel)

# Icon/Lock emoji panel
$iconLabel = New-Object System.Windows.Forms.Label
$iconLabel.Text = [char]0x1F512
$iconLabel.Location = New-Object System.Drawing.Point(0, 45)
$iconLabel.Size = New-Object System.Drawing.Size(450, 40)
$iconLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#e94560')
$iconLabel.TextAlign = 'MiddleCenter'
$iconLabel.Font = New-Object System.Drawing.Font('Segoe UI Emoji', 20)
$form.Controls.Add($iconLabel)

# Title label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'License Activation'
$titleLabel.Location = New-Object System.Drawing.Point(0, 90)
$titleLabel.Size = New-Object System.Drawing.Size(450, 30)
$titleLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#e94560')
$titleLabel.TextAlign = 'MiddleCenter'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($titleLabel)

# Subtitle label
$subtitleLabel = New-Object System.Windows.Forms.Label
$subtitleLabel.Text = 'Enter your license key to activate this application'
$subtitleLabel.Location = New-Object System.Drawing.Point(0, 125)
$subtitleLabel.Size = New-Object System.Drawing.Size(450, 25)
$subtitleLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml('#aaaaaa')
$subtitleLabel.TextAlign = 'MiddleCenter'
$subtitleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$form.Controls.Add($subtitleLabel)

# License key text box with border panel
$borderPanel = New-Object System.Windows.Forms.Panel
$borderPanel.Location = New-Object System.Drawing.Point(35, 165)
$borderPanel.Size = New-Object System.Drawing.Size(380, 42)
$borderPanel.BackColor = [System.Drawing.ColorTranslator]::FromHtml('#16213e')
$form.Controls.Add($borderPanel)

$textBox = New-Object System.Windows.Forms.TextBox
$textBox.Location = New-Object System.Drawing.Point(6, 6)
$textBox.Size = New-Object System.Drawing.Size(368, 30)
$textBox.Font = New-Object System.Drawing.Font('Consolas', 12)
$textBox.BackColor = [System.Drawing.ColorTranslator]::FromHtml('#0f0f23')
$textBox.ForeColor = [System.Drawing.Color]::White
$textBox.BorderStyle = 'None'
$textBox.CharacterCasing = 'Upper'
$borderPanel.Controls.Add($textBox)

# Activate button
$activateButton = New-Object System.Windows.Forms.Button
$activateButton.Text = [char]0x2714 + ' Activate License'
$activateButton.Location = New-Object System.Drawing.Point(35, 225)
$activateButton.Size = New-Object System.Drawing.Size(380, 45)
$activateButton.FlatStyle = 'Flat'
$activateButton.FlatAppearance.BorderSize = 0
$activateButton.BackColor = [System.Drawing.ColorTranslator]::FromHtml('#e94560')
$activateButton.ForeColor = [System.Drawing.Color]::White
$activateButton.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$activateButton.Cursor = 'Hand'

$activateButton.Add_Click({
    $key = $textBox.Text.Trim()
    if ($key -ne '') {
        $form.Tag = $key
        $form.DialogResult = 'OK'
        $form.Close()
    }
})
$form.Controls.Add($activateButton)

# Handle Enter key
$textBox.Add_KeyDown({
    if ($_.KeyCode -eq 'Enter') {
        $activateButton.PerformClick()
    }
})

$form.AcceptButton = $activateButton
$textBox.Focus()

$result = $form.ShowDialog()

if ($result -eq 'OK' -and $form.Tag) {
    Write-Output $form.Tag
}
`;

        // Execute PowerShell script
        const tempDir = os.tmpdir();
        const scriptPath = path.join(tempDir, `cv_license_${crypto.randomBytes(8).toString('hex')}.ps1`);
        tempFiles.add(scriptPath); // Track temp file

        try {
            fs.writeFileSync(scriptPath, psScript, 'utf-8');

            const ps = child_process.spawn('powershell.exe', [
                '-ExecutionPolicy', 'Bypass',
                '-NoProfile',
                '-NoLogo',
                '-File', scriptPath
            ], {
                stdio: ['pipe', 'pipe', 'pipe'],
                windowsHide: false
            });

            let output = '';
            let errorOutput = '';

            ps.stdout.on('data', (data) => {
                output += data.toString();
            });

            ps.stderr.on('data', (data) => {
                errorOutput += data.toString();
            });

            ps.on('close', (code) => {
                // Cleanup
                try { fs.unlinkSync(scriptPath); } catch (e) { /* ignore */ }
                tempFiles.delete(scriptPath);

                const licenseKey = output.trim();
                if (licenseKey && licenseKey.length > 0) {
                    resolve(licenseKey);
                } else {
                    resolve(null);
                }
            });

            ps.on('error', (err) => {
                console.error('[CodeVault] PowerShell error:', err.message);
                try { fs.unlinkSync(scriptPath); } catch (e) { /* ignore */ }
                tempFiles.delete(scriptPath);
                resolve(null);
            });

        } catch (err) {
            console.error('[CodeVault] Failed to create GUI dialog:', err.message);
            try { fs.unlinkSync(scriptPath); } catch (e) { /* ignore */ }
            tempFiles.delete(scriptPath);
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

// Main prompt function - ALWAYS use native GUI on Windows for best user experience
async function promptForLicenseKey() {
    // On Windows, use native PowerShell GUI dialog (matches Python tkinter style)
    if (os.platform() === 'win32') {
        console.log('[CodeVault] Opening license key dialog...');
        const key = await promptNativeGUI();
        if (key) return key;

        // GUI failed - try console as fallback if we have a TTY
        if (process.stdin.isTTY) {
            console.log('[CodeVault] GUI dialog failed, falling back to console input...');
            return await promptConsole();
        }
        return null;
    }

    // Use console prompt on non-Windows platforms
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
        // Ensure directory exists
        const licenseDir = path.dirname(licensePath);
        if (!fs.existsSync(licenseDir)) {
            fs.mkdirSync(licenseDir, { recursive: true });
        }
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

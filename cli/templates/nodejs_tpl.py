# Node.js License Wrapper Templates

NODEJS_WRAPPER_LEGACY = r"""// ============ LICENSE WRAPPER ============
const crypto = require('crypto');
const os = require('os');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Ed25519 public key for signature verification (embedded at build time)
const _LW_PUBLIC_KEY_PEM = `{public_key}`;

function _lw_buildSignatureMessage(data) {
    const features = JSON.stringify((data.features || []).slice().sort());
    const variables = JSON.stringify(data.variables || {});
    return [
        data.status || '',
        data.expires_at != null ? String(data.expires_at) : '',
        features,
        variables,
        data.client_nonce || data.nonce || '',
        data.server_nonce || '',
        data.timestamp != null ? String(data.timestamp) : '',
        data.server_time != null ? String(data.server_time) : '',
    ].join('|');
}

function _lw_getExeDir() {
    if (process.pkg) {
        return path.dirname(process.execPath);
    }
    return __dirname;
}

function _lw_getLicenseKeyPath() {
    return path.join(_lw_getExeDir(), 'license.key');
}

// Lease configuration
const _LW_LEASE_DURATION = 24 * 60 * 60;  // 24 hours in seconds
const _LW_CLOCK_DRIFT_MAX = 60 * 60;       // 1 hour max drift

function _lw_getLeasePath() {
    return path.join(_lw_getExeDir(), 'license.lease');
}

function _lw_getMachineSecret() {
    const info = `${os.hostname()}|${os.platform()}|${os.arch()}|LW_SALT_2026`;
    return crypto.createHash('sha256').update(info).digest();
}



function _lw_encryptLease(leaseData) {
    try {
        const secret = _lw_getMachineSecret();
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

function _lw_decryptLease(encryptedData) {
    try {
        const secret = _lw_getMachineSecret();
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

function _lw_createLease(licenseKey, hwid, serverTime, duration = _LW_LEASE_DURATION) {
    return {
        license_key_hash: crypto.createHash('sha256').update(licenseKey).digest('hex'),
        hwid: hwid,
        expires_at: serverTime + duration,
        server_time: serverTime,
        validated_at: Math.floor(Date.now() / 1000)
    };
}

function _lw_saveLease(leaseData) {
    try {
        const leasePath = _lw_getLeasePath();
        const encrypted = _lw_encryptLease(leaseData);
        if (encrypted) {
            fs.writeFileSync(leasePath, encrypted, 'utf-8');
            console.log('[License Wrapper] Lease saved (24h offline access)');
            return true;
        }
    } catch (e) {
        console.log(`[License Wrapper] Could not save lease: ${e.message}`);
    }
    return false;
}

function _lw_loadLease() {
    try {
        const leasePath = _lw_getLeasePath();
        if (fs.existsSync(leasePath)) {
            const encrypted = fs.readFileSync(leasePath, 'utf-8').trim();
            return _lw_decryptLease(encrypted);
        }
    } catch (e) {
        console.log(`[License Wrapper] Could not load lease: ${e.message}`);
    }
    return null;
}

function _lw_validateLease(licenseKey, hwid) {
    const lease = _lw_loadLease();
    if (!lease) {
        return { valid: false, message: 'No lease found' };
    }
    
    if (lease.hwid !== hwid) {
        return { valid: false, message: 'HWID mismatch' };
    }
    
    const keyHash = crypto.createHash('sha256').update(licenseKey).digest('hex');
    if (lease.license_key_hash !== keyHash) {
        return { valid: false, message: 'License mismatch' };
    }
    
    const currentTime = Math.floor(Date.now() / 1000);
    if (currentTime > lease.expires_at) {
        return { valid: false, message: 'Lease expired' };
    }
    
    const remaining = lease.expires_at - currentTime;
    const hours = Math.floor(remaining / 3600);
    const mins = Math.floor((remaining % 3600) / 60);
    console.log(`[License Wrapper] Offline lease valid (${hours}h ${mins}m remaining)`);
    return { valid: true, message: 'Valid' };
}

function _lw_deleteSavedLicenseAndLease() {
    try {
        const licensePath = _lw_getLicenseKeyPath();
        if (fs.existsSync(licensePath)) {
            fs.unlinkSync(licensePath);
        }
        const leasePath = _lw_getLeasePath();
        if (fs.existsSync(leasePath)) {
            fs.unlinkSync(leasePath);
        }
        console.log('License and lease files removed.');
    } catch (e) {
        // Ignore errors
    }
}

function _lw_promptForLicenseKey() {
    return new Promise((resolve) => {
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        console.log('\n' + '='.repeat(50));
        console.log('  LICENSE KEY REQUIRED');
        console.log('='.repeat(50));
        
        rl.question('Enter License Key: ', (answer) => {
            rl.close();
            const key = answer ? answer.trim() : null;
            resolve(key);
        });
    });
}

async function _lw_loadOrPromptLicense() {
    const licensePath = _lw_getLicenseKeyPath();
    
    if (fs.existsSync(licensePath)) {
        try {
            const key = fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {
                console.log(`[License Wrapper] Loaded license from ${licensePath}`);
                return key;
            }
        } catch (e) {
            console.log(`[License Wrapper] Warning: Could not read license file: ${e.message}`);
        }
    }
    
    console.log('[License Wrapper] No license key found. Please enter your license key.');
    const licenseKey = await _lw_promptForLicenseKey();
    
    if (!licenseKey) {
        console.log('\n[ERROR] No license key provided. Exiting...');
        process.exit(1);
    }
    
    try {
        fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[License Wrapper] License key saved to ${licensePath}`);
    } catch (e) {
        console.log(`[License Wrapper] Warning: Could not save license file: ${e.message}`);
    }
    
    return licenseKey;
}

function _lw_deleteSavedLicense() {
    try {
        const licensePath = _lw_getLicenseKeyPath();
        if (fs.existsSync(licensePath)) {
            fs.unlinkSync(licensePath);
            console.log('License file removed. Please try again with a valid key.');
        }
    } catch (e) {
        // Ignore cleanup errors
    }
}

async function _lw_validate() {
    let LICENSE_KEY = "{license_key}";
    const SERVER_URL = "{server_url}";
    
    if (LICENSE_KEY === "DEMO") {
        console.log("[License Wrapper] Running in DEMO mode");
        return true;
    }
    
    if (LICENSE_KEY === "GENERIC_BUILD") {
        LICENSE_KEY = await _lw_loadOrPromptLicense();
    }
    
    return new Promise((resolve, reject) => {
        const cpus = os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${os.hostname()}|${os.platform()}|${os.arch()}|${os.totalmem()}|${cpuModel}`;
        const hwid = crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
        
        try {
            const urlObj = new URL(SERVER_URL + "/api/v1/license/validate");
            const postData = JSON.stringify({
                license_key: LICENSE_KEY,
                hwid: hwid,
                machine_name: os.hostname(),
                timestamp: Math.floor(Date.now() / 1000),
                nonce: crypto.randomBytes(16).toString('hex')
            });
            
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            };
            
            const lib = urlObj.protocol === 'http:' ? http : https;
            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {
                    if (res.statusCode === 200) {
                        try {
                            const result = JSON.parse(body);
                            // Verify Ed25519 signature if public key is available
                            if (result.signature && _LW_PUBLIC_KEY_PEM && _LW_PUBLIC_KEY_PEM.trim() !== '') {
                                try {
                                    const msg = _lw_buildSignatureMessage(result);
                                    const sigBuf = Buffer.from(result.signature, 'base64');
                                    const ok = crypto.verify(null, Buffer.from(msg, 'utf-8'),
                                        { key: _LW_PUBLIC_KEY_PEM, format: 'pem', type: 'spki' }, sigBuf);
                                    if (!ok) {
                                        console.error('[ERROR] Server response signature invalid');
                                        _lw_pauseAndExit(1);
                                        return;
                                    }
                                } catch (sigErr) {
                                    console.error('[WARN] Signature check failed:', sigErr.message);
                                }
                            }
                            if (result.status === 'valid') {
                                console.log("[OK] License validated online");
                                
                                // SEC4: Start heartbeat
                                _lw_startHeartbeat(LICENSE_KEY, hwid, SERVER_URL, {heartbeat_interval});

                                // MON2: Capture floating session token
                                _LW_SESSION_TOKEN = (result.variables || {})["_cv_session_token"];
                                if (_LW_SESSION_TOKEN) {
                                    process.on('exit', () => {
                                        _lw_releaseSession(LICENSE_KEY, SERVER_URL, hwid, _LW_SESSION_TOKEN);
                                    });
                                }

                                // Check clock drift and create lease
                                const serverTime = result.server_time || result.timestamp || Math.floor(Date.now() / 1000);
                                const localTime = Math.floor(Date.now() / 1000);
                                const drift = Math.abs(localTime - serverTime);
                                if (drift <= _LW_CLOCK_DRIFT_MAX) {
                                    const lease = _lw_createLease(LICENSE_KEY, hwid, serverTime);
                                    _lw_saveLease(lease);
                                } else {
                                    console.log(`[License Wrapper] Clock drift detected (${drift}s), lease not saved`);
                                }
                                resolve(true);
                            } else {
                                console.error('\n' + '='.repeat(50));
                                console.error('  [ERROR] LICENSE INVALID');
                                console.error('='.repeat(50));
                                console.error(`${result.message || 'License key is invalid or expired.'}`);
                                console.error('='.repeat(50));
                                if ("{license_key}" === "GENERIC_BUILD") {
                                    _lw_deleteSavedLicenseAndLease();
                                }
                                _lw_pauseAndExit(1);
                            }
                        } catch (e) {
                            console.error('\n' + '='.repeat(50));
                            console.error('  [ERROR] RESPONSE ERROR');
                            console.error('='.repeat(50));
                            console.error('Failed to parse server response.');
                            console.error('='.repeat(50));
                            _lw_pauseAndExit(1);
                        }
                    } else {
                        console.error('\n' + '='.repeat(50));
                        console.error('  [ERROR] SERVER ERROR');
                        console.error('='.repeat(50));
                        console.error(`License server returned HTTP ${res.statusCode}.`);
                        console.error('='.repeat(50));
                        if ("{license_key}" === "GENERIC_BUILD") {
                            _lw_deleteSavedLicenseAndLease();
                        }
                        _lw_pauseAndExit(1);
                    }
                });
            });
            
            req.on('error', (e) => {
                console.error(`[WARN] Connection error: ${e.message || 'Unknown network error'}`);
                console.log('[License Wrapper] Checking offline lease...');
                
                // Try offline lease
                const leaseResult = _lw_validateLease(LICENSE_KEY, hwid);
                if (leaseResult.valid) {
                    console.log('[OK] Running with valid offline lease');
                    resolve(true);
                } else {
                    console.error('\n' + '='.repeat(50));
                    console.error('  [ERROR] OFFLINE - LICENSE REQUIRED');
                    console.error('='.repeat(50));
                    console.error(`Cannot validate license offline: ${leaseResult.message}`);
                    console.error('Please connect to the internet to validate your license.');
                    console.error('='.repeat(50));
                    _lw_pauseAndExit(1);
                }
            });
            
            req.write(postData);
            req.end();
            
        } catch (e) {
            console.error('\n' + '='.repeat(50));
            console.error('  [ERROR] VALIDATION ERROR');
            console.error('='.repeat(50));
            console.error(e.message || e);
            console.error('='.repeat(50));
            _lw_pauseAndExit(1);
        }
    });
}

function _lw_pauseAndExit(code) {
    if (process.platform === 'win32') {
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        rl.question('\nPress Enter to exit...', () => {
            rl.close();
            process.exit(code);
        });
    } else {
        process.exit(code);
    }
}

// Bootstrap
_lw_validate().then(() => {
    // Load original application
    try {
        console.log("[License Wrapper] Starting application...");
        require('./{target_file}');
    } catch (e) {
        console.error('\n[ERROR] Runtime Error:', e);
        _lw_pauseAndExit(1);
    }
}).catch(e => {
    console.error(e);
    _lw_pauseAndExit(1);
});
"""

NODEJS_WRAPPER_PREFIX = r'''// ============ LICENSE WRAPPER - DO NOT REMOVE ============
// CRITICAL: Wrap everything in try-catch to catch module load errors
try {
// Use stderr for immediate output (stdout might buffer in pkg)
process.stderr.write('[DEBUG] License wrapper loading...\n');

// ============ LEASE CONFIGURATION ============
// This flag controls whether offline lease validation is enabled
const _LW_LEASE_ENABLED = {lease_enabled};

function _lw_showErrorAndWait(type, error) {
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('  [ERROR] ' + type + '\n');
    process.stderr.write('='.repeat(60) + '\n');
    process.stderr.write('\nError: ' + (error.message || error) + '\n');
    if (error.stack) {
        process.stderr.write('\nStack trace:\n');
        process.stderr.write(error.stack + '\n');
    }

    // Context-specific troubleshooting
    process.stderr.write('\n' + '-'.repeat(60) + '\n');
    process.stderr.write('TROUBLESHOOTING:\n');
    process.stderr.write('-'.repeat(60) + '\n');
    if (type.includes('LICENSE INVALID')) {
        process.stderr.write('- Check your license key for typos\n');
        process.stderr.write('- Ensure the license is active and not expired\n');
        process.stderr.write('- Verify you are connected to the internet\n');
    } else if (type.includes('CONNECTION') || type.includes('OFFLINE')) {
        process.stderr.write('- Check your internet connection\n');
        process.stderr.write('- Try connecting to a different network\n');
        process.stderr.write('- If offline mode is desired, contact support\n');
    } else if (type.includes('SERVER ERROR')) {
        process.stderr.write('- The license server may be temporarily unavailable\n');
        process.stderr.write('- Try again in a few minutes\n');
        process.stderr.write('- Check with support for server status\n');
    } else if (type.includes('VALIDATION') || type.includes('RESPONSE')) {
        process.stderr.write('- This may be a bug in the license wrapper\n');
        process.stderr.write('- Please report this error with full details\n');
    } else {
        process.stderr.write('- Please take a screenshot of this entire error\n');
        process.stderr.write('- Include information about what you were doing\n');
        process.stderr.write('- Contact support with the error details\n');
    }

    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('Press any key to exit...\n');
    process.stderr.write('='.repeat(60) + '\n');

    // Use child_process.spawnSync to pause (works in pkg-compiled executables)
    try {
        if (process.platform === 'win32') {
            require('child_process').spawnSync('cmd', ['/c', 'pause'], {
                stdio: 'inherit'
            });
        } else {
            require('child_process').spawnSync('bash', ['-c', 'read -n 1 -p "Press any key..."'], {
                stdio: 'inherit'
            });
        }
    } catch (e) {
        // Fallback if spawnSync fails: just wait 10 seconds
        const start = Date.now();
        while (Date.now() - start < 10000) {}
    }
    process.exit(1);
}

// Catch uncaught exceptions (sync errors)
process.on('uncaughtException', (error) => {
    _lw_showErrorAndWait('UNCAUGHT EXCEPTION', error);
});

// Catch unhandled promise rejections (async errors)
process.on('unhandledRejection', (reason, promise) => {
    _lw_showErrorAndWait('UNHANDLED REJECTION', reason);
});

// ============ LICENSE WRAPPER CORE ============
process.stderr.write('[DEBUG] Loading modules...\n');
const _lw_crypto = require('crypto');
const _lw_os = require('os');
const _lw_https = require('https');
const _lw_http = require('http');
const _lw_fs = require('fs');
const _lw_path = require('path');
const _lw_readline = require('readline');

// Global session tracking for floating licenses (MON2)
let _LW_SESSION_TOKEN = null;

// ============ Ed25519 SIGNATURE VERIFICATION ============
// The public key is embedded at build time. Only the server holds the private key.
// This prevents attackers from forging validation responses even if they extract
// this key from the binary — public keys can verify but cannot sign.
const _LW_PUBLIC_KEY_PEM = `{public_key}`;

function _lw_buildSignatureMessage(data) {
    const features = JSON.stringify((data.features || []).slice().sort());
    const variables = JSON.stringify(data.variables || {});
    return [
        data.status || '',
        data.expires_at != null ? String(data.expires_at) : '',
        features,
        variables,
        data.client_nonce || data.nonce || '',
        data.server_nonce || '',
        data.timestamp != null ? String(data.timestamp) : '',
        data.server_time != null ? String(data.server_time) : '',
    ].join('|');
}

function _lw_verifyEd25519Signature(responseData, signatureB64) {
    if (!_LW_PUBLIC_KEY_PEM || _LW_PUBLIC_KEY_PEM.trim() === '') {
        // No public key embedded — fall back to trusting server response (legacy HMAC mode)
        return true;
    }
    try {
        const message = _lw_buildSignatureMessage(responseData);
        const signatureBuffer = Buffer.from(signatureB64, 'base64');
        const isValid = _lw_crypto.verify(
            null, // Ed25519 doesn't use a separate hash algorithm
            Buffer.from(message, 'utf-8'),
            { key: _LW_PUBLIC_KEY_PEM, format: 'pem', type: 'spki' },
            signatureBuffer
        );
        return isValid;
    } catch (e) {
        process.stderr.write(`[License Wrapper] Signature verification error: ${e.message}\n`);
        return false;
    }
}

function _lw_getExeDir() {
    if (process.pkg) {
        return _lw_path.dirname(process.execPath);
    }
    return __dirname;
}

function _lw_getBinaryHash() {
    try {
        // In pkg-compiled binaries, process.execPath is the path to the .exe
        const path = process.execPath;
        const hash = _lw_crypto.createHash('sha256');
        const fileBuffer = _lw_fs.readFileSync(path);
        hash.update(fileBuffer);
        return hash.digest('hex');
    } catch (e) {
        return null;
    }
}

function _lw_getLicenseKeyPath() {
    return _lw_path.join(_lw_getExeDir(), 'license.key');
}

// Lease configuration (only used if _LW_LEASE_ENABLED is true)
const _LW_LEASE_DURATION = 24 * 60 * 60;
const _LW_CLOCK_DRIFT_MAX = 60 * 60;

function _lw_getLeasePath() {
    return _lw_path.join(_lw_getExeDir(), 'license.lease');
}

function _lw_getMachineSecret() {
    const info = `${_lw_os.hostname()}|${_lw_os.platform()}|${_lw_os.arch()}|LW_SALT_2026`;
    return _lw_crypto.createHash('sha256').update(info).digest();
}



function _lw_encryptLease(leaseData) {
    const secret = _lw_getMachineSecret();
    const dataJson = Buffer.from(JSON.stringify(leaseData), 'utf-8');

    // Try AES-256-GCM first
    try {
        const nonce = _lw_crypto.randomBytes(12);
        const cipher = _lw_crypto.createCipheriv('aes-256-gcm', secret, nonce);
        const encrypted = Buffer.concat([cipher.update(dataJson), cipher.final()]);
        const authTag = cipher.getAuthTag();

        return Buffer.concat([
            Buffer.from('AES:'),
            nonce,
            authTag,
            encrypted
        ]).toString('base64');
    } catch (aesError) {
        console.log('[License Wrapper] AES encryption unavailable');
        return null;
    }
}

function _lw_decryptLease(encryptedData) {
    try {
        const secret = _lw_getMachineSecret();
        const raw = Buffer.from(encryptedData, 'base64');

        if (raw.slice(0, 4).toString() === 'AES:') {
            const nonce = raw.slice(4, 16);
            const authTag = raw.slice(16, 32);
            const encrypted = raw.slice(32);

            const decipher = _lw_crypto.createDecipheriv('aes-256-gcm', secret, nonce);
            decipher.setAuthTag(authTag);
            const dataJson = Buffer.concat([decipher.update(encrypted), decipher.final()]);
            return JSON.parse(dataJson.toString('utf-8'));
        }
        return null;
    } catch (e) {
        console.error('[License Wrapper] Decryption error:', e.message);
        return null;
    }
}

function _lw_createLease(licenseKey, hwid, serverTime, duration = _LW_LEASE_DURATION) {
    return {
        license_key_hash: _lw_crypto.createHash('sha256').update(licenseKey).digest('hex'),
        hwid: hwid,
        expires_at: serverTime + duration,
        server_time: serverTime,
        validated_at: Math.floor(Date.now() / 1000)
    };
}

function _lw_saveLease(leaseData) {
    // Only save lease if lease mode is enabled
    if (!_LW_LEASE_ENABLED) return false;
    try {
        const leasePath = _lw_getLeasePath();
        const encrypted = _lw_encryptLease(leaseData);
        if (encrypted) {
            _lw_fs.writeFileSync(leasePath, encrypted, 'utf-8');
            console.log('[License Wrapper] Lease saved (24h offline access)');
            return true;
        }
    } catch (e) {
        // Ignore
    }
    return false;
}

function _lw_loadLease() {
    // Only load lease if lease mode is enabled
    if (!_LW_LEASE_ENABLED) return null;
    try {
        const leasePath = _lw_getLeasePath();
        if (_lw_fs.existsSync(leasePath)) {
            const encrypted = _lw_fs.readFileSync(leasePath, 'utf-8').trim();
            return _lw_decryptLease(encrypted);
        }
    } catch (e) {
        // Ignore
    }
    return null;
}

function _lw_validateLease(licenseKey, hwid) {
    // Only validate lease if lease mode is enabled
    if (!_LW_LEASE_ENABLED) return { valid: false, message: 'Offline mode not enabled for this build' };
    const lease = _lw_loadLease();
    if (!lease) return { valid: false, message: 'No lease found' };
    if (lease.hwid !== hwid) return { valid: false, message: 'HWID mismatch' };
    const keyHash = _lw_crypto.createHash('sha256').update(licenseKey).digest('hex');
    if (lease.license_key_hash !== keyHash) return { valid: false, message: 'License mismatch' };
    const currentTime = Math.floor(Date.now() / 1000);
    if (currentTime > lease.expires_at) return { valid: false, message: 'Lease expired' };
    const remaining = lease.expires_at - currentTime;
    const hours = Math.floor(remaining / 3600);
    const mins = Math.floor((remaining % 3600) / 60);
    console.log(`[License Wrapper] Offline lease valid (${hours}h ${mins}m remaining)`);
    return { valid: true, message: 'Valid' };
}

function _lw_startHeartbeat(licenseKey, hwid, serverUrl, intervalMs) {
    setInterval(async () => {
        try {
            const urlObj = new URL(serverUrl + "/api/v1/license/heartbeat");
            const postData = JSON.stringify({
                license_key: licenseKey,
                hwid: hwid,
                timestamp: Math.floor(Date.now() / 1000),
                nonce: _lw_crypto.randomBytes(16).toString('hex')
            });
            
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            };
            
            const lib = urlObj.protocol === 'http:' ? _lw_http : _lw_https;
            const req = lib.request(options);
            req.on('error', () => {});
            req.write(postData);
            req.end();
        } catch (e) {}
    }, intervalMs);
}

function _lw_releaseSession(licenseKey, serverUrl, hwid, token) {
    if (!token) return;
    try {
        // Use sync execution via powershell or bash to ensure it completes before exit
        const postData = JSON.stringify({
            license_key: licenseKey,
            hwid: hwid,
            session_token: token
        });
        
        const url = serverUrl + "/api/v1/license/release";
        
        if (process.platform === 'win32') {
            require('child_process').spawnSync('powershell', [
                '-Command', 
                `Invoke-RestMethod -Method Post -Uri "${url}" -ContentType "application/json" -Body '${postData}'`
            ]);
        } else {
            require('child_process').spawnSync('curl', [
                '-X', 'POST', 
                '-H', 'Content-Type: application/json',
                '-d', postData,
                url
            ]);
        }
    } catch (e) {
        // Ignore
    }
}

function _lw_deleteSavedLicenseAndLease() {
    try {
        const licensePath = _lw_getLicenseKeyPath();
        if (_lw_fs.existsSync(licensePath)) _lw_fs.unlinkSync(licensePath);
        const leasePath = _lw_getLeasePath();
        if (_lw_fs.existsSync(leasePath)) _lw_fs.unlinkSync(leasePath);
    } catch (e) { /* ignore */ }
}


function _lw_promptForLicenseKey() {
    return new Promise((resolve) => {
        // Try PowerShell GUI dialog on Windows (supports copy-paste)
        if (process.platform === 'win32') {
            try {
                const { spawnSync } = require('child_process');
                // PowerShell script with inline WinForms for modern dark-themed dialog
                const psScript = `
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = "License Activation Required"
$form.Size = New-Object System.Drawing.Size(480, 280)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(17, 24, 39)
$form.ForeColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$form.TopMost = $true

$iconPanel = New-Object System.Windows.Forms.Panel
$iconPanel.Size = New-Object System.Drawing.Size(80, 280)
$iconPanel.Location = New-Object System.Drawing.Point(0, 0)
$iconPanel.BackColor = [System.Drawing.Color]::FromArgb(99, 102, 241)
$form.Controls.Add($iconPanel)

$iconLabel = New-Object System.Windows.Forms.Label
$iconLabel.Text = [char]0x1F512
$iconLabel.Font = New-Object System.Drawing.Font("Segoe UI Emoji", 28)
$iconLabel.Size = New-Object System.Drawing.Size(80, 60)
$iconLabel.Location = New-Object System.Drawing.Point(0, 90)
$iconLabel.TextAlign = 'MiddleCenter'
$iconLabel.ForeColor = [System.Drawing.Color]::White
$iconPanel.Controls.Add($iconLabel)

$brandLabel = New-Object System.Windows.Forms.Label
$brandLabel.Text = "Protected by CodeVault"
$brandLabel.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$brandLabel.Size = New-Object System.Drawing.Size(360, 20)
$brandLabel.Location = New-Object System.Drawing.Point(100, 5)
$brandLabel.ForeColor = [System.Drawing.Color]::FromArgb(100, 116, 139)
$form.Controls.Add($brandLabel)

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "License Key Required"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.Size = New-Object System.Drawing.Size(360, 35)
$titleLabel.Location = New-Object System.Drawing.Point(100, 25)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(243, 244, 246)
$form.Controls.Add($titleLabel)

$descLabel = New-Object System.Windows.Forms.Label
$descLabel.Text = "Please enter your license key to activate this application."
$descLabel.Size = New-Object System.Drawing.Size(360, 25)
$descLabel.Location = New-Object System.Drawing.Point(100, 60)
$descLabel.ForeColor = [System.Drawing.Color]::FromArgb(156, 163, 175)
$form.Controls.Add($descLabel)

$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.Size = New-Object System.Drawing.Size(340, 35)
$inputBox.Location = New-Object System.Drawing.Point(100, 100)
$inputBox.Font = New-Object System.Drawing.Font("Consolas", 12)
$inputBox.BackColor = [System.Drawing.Color]::FromArgb(31, 41, 55)
$inputBox.ForeColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$inputBox.BorderStyle = 'FixedSingle'
$form.Controls.Add($inputBox)

$hintLabel = New-Object System.Windows.Forms.Label
$hintLabel.Text = "Format: LIC-XXXX-XXXX-XXXX"
$hintLabel.Size = New-Object System.Drawing.Size(340, 20)
$hintLabel.Location = New-Object System.Drawing.Point(100, 138)
$hintLabel.ForeColor = [System.Drawing.Color]::FromArgb(107, 114, 128)
$hintLabel.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$form.Controls.Add($hintLabel)

$activateBtn = New-Object System.Windows.Forms.Button
$activateBtn.Text = "Activate"
$activateBtn.Size = New-Object System.Drawing.Size(120, 38)
$activateBtn.Location = New-Object System.Drawing.Point(320, 180)
$activateBtn.BackColor = [System.Drawing.Color]::FromArgb(99, 102, 241)
$activateBtn.ForeColor = [System.Drawing.Color]::White
$activateBtn.FlatStyle = 'Flat'
$activateBtn.FlatAppearance.BorderSize = 0
$activateBtn.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$activateBtn.Add_Click({
    if ($inputBox.Text.Trim() -ne "") {
        $form.Tag = $inputBox.Text.Trim()
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    }
})
$form.Controls.Add($activateBtn)

$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = "Cancel"
$cancelBtn.Size = New-Object System.Drawing.Size(100, 38)
$cancelBtn.Location = New-Object System.Drawing.Point(210, 180)
$cancelBtn.BackColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$cancelBtn.ForeColor = [System.Drawing.Color]::FromArgb(209, 213, 219)
$cancelBtn.FlatStyle = 'Flat'
$cancelBtn.FlatAppearance.BorderSize = 0
$cancelBtn.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$cancelBtn.Add_Click({
    $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Close()
})
$form.Controls.Add($cancelBtn)

$form.AcceptButton = $activateBtn
$form.CancelButton = $cancelBtn
$inputBox.Select()
$result = $form.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::OK -and $form.Tag) {
    Write-Output $form.Tag
} else {
    Write-Output ""
}
`.trim();

                const result = spawnSync('powershell', [
                    '-ExecutionPolicy', 'Bypass', '-NoProfile', '-NonInteractive', '-Command', psScript
                ], { encoding: 'utf-8', windowsHide: false }); // windowsHide: false to allow dialog to show on top? Actually true is fine for the shell.

                const key = (result.stdout || '').trim();
                if (key) {
                    resolve(key);
                    return;
                }
            } catch (e) {
                console.log('[License Wrapper] GUI dialog failed, using console input');
            }
        }
        
        // Fallback to console input
        const rl = _lw_readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        console.log('[License Wrapper] No license key found. Please enter your license key.');
        rl.question('Enter License Key: ', (answer) => {
            rl.close();
            const key = answer ? answer.trim() : null;
            resolve(key);
        });
    });
}

async function _lw_loadOrPromptLicense() {
    const licensePath = _lw_getLicenseKeyPath();
    
    if (_lw_fs.existsSync(licensePath)) {
        try {
            const key = _lw_fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {
                console.log(`[License Wrapper] Loaded license from ${licensePath}`);
                return key;
            }
        } catch (e) {
            console.log(`[License Wrapper] Warning: Could not read license file: ${e.message}`);
        }
    }
    
    const licenseKey = await _lw_promptForLicenseKey();
    
    if (!licenseKey) {
        _lw_showErrorAndWait('LICENSE REQUIRED', new Error('No license key was provided.\n\nPlease run the application again and enter a valid license key.'));
    }
    
    try {
        _lw_fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[License Wrapper] License key saved to ${licensePath}`);
    } catch (e) {
        console.log(`[License Wrapper] Warning: Could not save license file: ${e.message}`);
    }
    
    return licenseKey;
}

function _lw_deleteSavedLicense() {
    try {
        const licensePath = _lw_getLicenseKeyPath();
        if (_lw_fs.existsSync(licensePath)) {
            _lw_fs.unlinkSync(licensePath);
            console.log('License file removed. Please try again with a valid key.');
        }
    } catch (e) {
        // Ignore cleanup errors
    }
}

async function _lw_validate() {
    let LICENSE_KEY = "{license_key}";
    const SERVER_URL = "{server_url}";
    
    if (LICENSE_KEY === "DEMO") {
        console.log("[License Wrapper] Running in DEMO mode");
        return true;
    }
    
    if (LICENSE_KEY === "GENERIC_BUILD") {
        LICENSE_KEY = await _lw_loadOrPromptLicense();
    }
    
    return new Promise((resolve, reject) => {
        const cpus = _lw_os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${_lw_os.hostname()}|${_lw_os.platform()}|${_lw_os.arch()}|${_lw_os.totalmem()}|${cpuModel}`;
        const hwid = _lw_crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
        
        try {
            const urlObj = new URL(SERVER_URL + "/api/v1/license/validate");
            const postData = JSON.stringify({
                license_key: LICENSE_KEY,
                hwid: hwid,
                machine_name: _lw_os.hostname(),
                timestamp: Math.floor(Date.now() / 1000),
                nonce: _lw_crypto.randomBytes(16).toString('hex'),
                binary_hash: _lw_getBinaryHash()
            });
            
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            };
            
            const lib = urlObj.protocol === 'http:' ? _lw_http : _lw_https;
            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {
                    if (res.statusCode === 200) {
                        try {
                            const result = JSON.parse(body);
                            // Verify Ed25519 signature to prevent forged responses
                            if (result.signature && !_lw_verifyEd25519Signature(result, result.signature)) {
                                _lw_showErrorAndWait('SIGNATURE INVALID', new Error('Server response signature verification failed.\n\nThis may indicate a tampered response or misconfigured server.\nPlease contact the application developer.'));
                                return;
                            }
                            if (result.status === 'valid') {
                                console.log("[OK] License validated online");
                                
                                // SEC4: Start heartbeat
                                _lw_startHeartbeat(LICENSE_KEY, hwid, SERVER_URL, {heartbeat_interval});

                                // MON2: Capture floating session token
                                _LW_SESSION_TOKEN = (result.variables || {})["_cv_session_token"];
                                if (_LW_SESSION_TOKEN) {
                                    process.on('exit', () => {
                                        _lw_releaseSession(LICENSE_KEY, SERVER_URL, hwid, _LW_SESSION_TOKEN);
                                    });
                                }

                                // Check clock drift and create lease
                                const serverTime = result.server_time || result.timestamp || Math.floor(Date.now() / 1000);
                                const localTime = Math.floor(Date.now() / 1000);
                                const drift = Math.abs(localTime - serverTime);
                                if (drift <= _LW_CLOCK_DRIFT_MAX) {
                                    const lease = _lw_createLease(LICENSE_KEY, hwid, serverTime);
                                    _lw_saveLease(lease);
                                } else {
                                    console.log(`[License Wrapper] Clock drift detected (${drift}s), lease not saved`);
                                }
                                resolve(true);
                            } else {
                                if ("{license_key}" === "GENERIC_BUILD") {
                                    _lw_deleteSavedLicenseAndLease();
                                }
                                _lw_showErrorAndWait('LICENSE INVALID', new Error(result.message || 'License key is invalid or expired.\n\nPlease check your license key and try again.'));
                            }
                        } catch (e) {
                            _lw_showErrorAndWait('RESPONSE ERROR', new Error('Failed to parse server response.\n\nPlease contact the application developer.'));
                        }
                    } else {
                        if ("{license_key}" === "GENERIC_BUILD") {
                            _lw_deleteSavedLicenseAndLease();
                        }
                        _lw_showErrorAndWait('SERVER ERROR', new Error(`License server returned HTTP ${res.statusCode}.\n\nPlease try again later or contact support.`));
                    }
                });
            });
            
            req.on('error', (e) => {
                console.error(`[WARN] Connection error: ${e.message || 'Unknown network error'}`);

                // Only attempt offline lease validation if lease mode is enabled
                if (_LW_LEASE_ENABLED) {
                    console.log('[License Wrapper] Checking offline lease...');
                    const leaseResult = _lw_validateLease(LICENSE_KEY, hwid);
                    if (leaseResult.valid) {
                        console.log('[OK] Running with valid offline lease');
                        resolve(true);
                        return;
                    } else {
                        _lw_showErrorAndWait('OFFLINE - LICENSE REQUIRED', new Error(`Cannot validate license offline.\n\n${leaseResult.message}\n\nPlease connect to the internet to validate your license.`));
                    }
                } else {
                    // Lease mode disabled - requires online validation
                    _lw_showErrorAndWait('CONNECTION REQUIRED', new Error('This application requires an internet connection to validate the license.\n\nPlease check your internet connection and try again.'));
                }
            });
            
            req.write(postData);
            req.end();
            
        } catch (e) {
            _lw_showErrorAndWait('VALIDATION ERROR', e);
        }
    });
}

// Wrap everything in async IIFE to use await
(async () => {
    try {
        process.stderr.write('[DEBUG] Starting license validation...\n');
        await _lw_validate();
        process.stderr.write('[DEBUG] Validation complete, starting application...\n');
        // ============ END LICENSE WRAPPER - APP CODE BELOW ============

'''

NODEJS_WRAPPER_SUFFIX = r"""
// ============ LICENSE WRAPPER CLEANUP ============
    } catch (e) {
        _lw_showErrorAndWait('APPLICATION ERROR', e);
    }
})().catch(e => {
    _lw_showErrorAndWait('STARTUP ERROR', e);
});

} catch (globalError) {
    // CRITICAL: Catch any error during module loading/setup
    process.stderr.write('\n='.repeat(60) + '\n');
    process.stderr.write('  [ERROR] CRITICAL STARTUP ERROR\n');
    process.stderr.write('='.repeat(60) + '\n');
    process.stderr.write('\nError: ' + (globalError.message || globalError) + '\n');
    if (globalError.stack) {
        process.stderr.write('\nStack trace:\n' + globalError.stack + '\n');
    }
    process.stderr.write('\n='.repeat(60) + '\n');
    process.stderr.write('Press any key to exit...\n');
    process.stderr.write('='.repeat(60) + '\n');
    require('child_process').spawnSync('cmd', ['/c', 'pause'], {stdio: 'inherit'});
    process.exit(1);
}
"""

// ============ LICENSE WRAPPER TEMPLATE - DO NOT EDIT DIRECTLY ============
// Unified template for CodeVault license protection
// Uses $PLACEHOLDER format for string.Template substitution
// =========================================================================

const UNIFIED_NODEJS_WRAPPER = `
// ============ LICENSE WRAPPER - DO NOT REMOVE ============
const _$PREFIX_fs = require('fs');
const _$PREFIX_path = require('path');
const _$PREFIX_os = require('os');
const _$PREFIX_crypto = require('crypto');
const _$PREFIX_https = require('https');
const _$PREFIX_http = require('http');
const { execSync } = require('child_process');

// ============ CONFIGURATION PLACEHOLDERS (filled during build) ============
const _$PREFIX_LICENSE_KEY = "$LICENSE_KEY";
const _$PREFIX_PRODUCT_ID = "$PRODUCT_ID";
const _$PREFIX_HWID_ENABLED = $HWID_ENABLED;
const _$PREFIX_LEASE_ENABLED = $LEASE_ENABLED;
const _$PREFIX_SECRET_KEY = "$SECRET_KEY";
const _$PREFIX_API_BASE = "$API_BASE";
const _$PREFIX_FUNC_PREFIX = "$FUNC_PREFIX";

// Constants
const _$PREFIX_LEASE_DURATION = 24 * 60 * 60 * 1000;
const _$PREFIX_CLOCK_DRIFT_MAX = 60 * 60 * 1000;
const _$PREFIX_VERSION = "2.0.0";

function _$PREFIX_xorDecrypt(data, key) {
    const result = [];
    const keyBytes = Buffer.from(key, 'utf8');
    for (let i = 0; i < data.length; i++) {
        result.push(data[i] ^ keyBytes[i % keyBytes.length]);
    }
    return Buffer.from(result);
}

function _$PREFIX_verifySignature(data, signature, secret) {
    try {
        const expected = _$PREFIX_crypto.createHmac('sha256', secret)
            .update(data)
            .digest('hex');
        return _$PREFIX_crypto.timingSafeEqual(
            Buffer.from(signature.toLowerCase()),
            Buffer.from(expected.toLowerCase())
        );
    } catch (e) {
        return false;
    }
}

function _$PREFIX_showError(title, message, details) {
    console.log('\\n' + '='.repeat(60));
    console.log('  [X] ' + title);
    console.log('='.repeat(60));
    console.log('\\n' + message);
    if (details) {
        console.log('\\nDetails: ' + details);
    }
    console.log('\\n' + '-'.repeat(60));
    console.log('TROUBLESHOOTING:');
    console.log('-'.repeat(60));
    if (title.includes('LICENSE INVALID')) {
        console.log('- Check that license.key file exists next to executable');
        console.log('- Verify your license key is valid and not expired');
        console.log('- Contact support if you believe this is an error');
    } else if (title.includes('HWID')) {
        console.log('- This license is tied to a specific machine');
        console.log('- Contact support to transfer license to new machine');
    } else if (title.includes('OFFLINE') || title.includes('LEASE')) {
        console.log('- System time may be incorrect - check system clock');
        console.log('- Connect to internet at least once every 24 hours');
        console.log('- Delete license.key to force re-validation');
    } else {
        console.log('- Check your internet connection');
        console.log('- Verify firewall allows the application');
        console.log('- Try running as administrator');
    }
    console.log('='.repeat(60));
    process.exit(1);
}

function _$PREFIX_getHWID() {
    try {
        const interfaces = _$PREFIX_os.networkInterfaces();
        let mac = '';
        for (const name of Object.keys(interfaces)) {
            for (const iface of interfaces[name]) {
                if (!iface.internal && iface.mac) {
                    mac = iface.mac;
                    break;
                }
            }
            if (mac) break;
        }
        const info = _$PREFIX_os.hostname() + '|' + _$PREFIX_os.platform() + '|' + _$PREFIX_os.arch() + '|' + mac;
        return _$PREFIX_crypto.createHash('sha256').update(info).digest('hex').slice(0, 32);
    } catch (e) {
        console.log('[License] Warning: Could not generate HWID:', e.message);
        return 'unknown-hwid';
    }
}

function _$PREFIX_getLicenseKeyPath() {
    try {
        if (process.pkg) {
            return _$PREFIX_path.join(_$PREFIX_path.dirname(process.execPath), 'license.key');
        }
        return _$PREFIX_path.join(__dirname, 'license.key');
    } catch (e) {
        return 'license.key';
    }
}

function _$PREFIX_loadLicenseFile() {
    try {
        const keyPath = _$PREFIX_getLicenseKeyPath();
        if (!_$PREFIX_fs.existsSync(keyPath)) {
            return null;
        }
        const encrypted = _$PREFIX_fs.readFileSync(keyPath);
        const decrypted = _$PREFIX_xorDecrypt(encrypted, _$PREFIX_SECRET_KEY);
        return JSON.parse(decrypted.toString('utf8'));
    } catch (e) {
        console.log('[License] Failed to load license file:', e.message);
        return null;
    }
}

function _$PREFIX_saveLicenseFile(data) {
    try {
        const keyPath = _$PREFIX_getLicenseKeyPath();
        const jsonStr = JSON.stringify(data);
        const encrypted = _$PREFIX_xorDecrypt(Buffer.from(jsonStr, 'utf8'), _$PREFIX_SECRET_KEY);
        _$PREFIX_fs.writeFileSync(keyPath, encrypted);
        return true;
    } catch (e) {
        console.log('[License] Failed to save license file:', e.message);
        return false;
    }
}

function _$PREFIX_validateOnline(licenseKey, hwid) {
    return new Promise((resolve, reject) => {
        const validationData = {
            license_key: licenseKey,
            hwid: hwid,
            product_id: _$PREFIX_PRODUCT_ID,
            version: _$PREFIX_VERSION
        };
        
        const url = new URL(_$PREFIX_API_BASE + '/validate');
        const postData = JSON.stringify(validationData);
        
        const options = {
            hostname: url.hostname,
            port: url.port || (url.protocol === 'https:' ? 443 : 80),
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            },
            timeout: 30000
        };
        
        const protocol = url.protocol === 'https:' ? _$PREFIX_https : _$PREFIX_http;
        
        const req = protocol.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    resolve({ valid: false, error: 'Invalid response' });
                }
            });
        });
        
        req.on('error', (e) => {
            resolve({ valid: false, error: e.message });
        });
        
        req.on('timeout', () => {
            req.destroy();
            resolve({ valid: false, error: 'Request timeout' });
        });
        
        req.write(postData);
        req.end();
    });
}

function _$PREFIX_validateOffline(licenseData, hwid) {
    if (!_$PREFIX_LEASE_ENABLED) {
        return { valid: false, error: 'Offline validation not enabled' };
    }
    
    if (!licenseData) {
        return { valid: false, error: 'No license data' };
    }
    
    if (licenseData.key !== _$PREFIX_LICENSE_KEY) {
        return { valid: false, error: 'License key mismatch' };
    }
    
    if (_$PREFIX_HWID_ENABLED) {
        const storedHWID = licenseData.hwid;
        if (storedHWID && storedHWID !== hwid) {
            return { valid: false, error: 'HWID mismatch' };
        }
    }
    
    const leaseUntil = licenseData.lease_until || 0;
    const currentTime = Date.now();
    
    if (currentTime > leaseUntil + _$PREFIX_CLOCK_DRIFT_MAX) {
        return { valid: false, error: 'Offline lease expired. Connect to internet to renew.' };
    }
    
    return { valid: true, offline: true };
}

function _$PREFIX_promptLicenseDialog() {
    const platform = _$PREFIX_os.platform();
    
    try {
        if (platform === 'win32') {
            const psScript = [
                'Add-Type -AssemblyName System.Windows.Forms',
                '[System.Windows.Forms.MessageBox]::Show("Please enter your license key to continue. Contact support@codevault.io if you need assistance.", "License Required", "OK", "Information")',
                '$result = [Microsoft.VisualBasic.Interaction]::InputBox("Enter your license key:", "License Key", "")',
                'Write-Output $result'
            ].join('; ');
            
            const result = execSync('powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "' + psScript + '"', {
                encoding: 'utf8',
                timeout: 60000
            });
            return result.trim();
        } else if (platform === 'darwin') {
            const script = 'display dialog "Enter your license key:" default answer "" with title "License Required" buttons {"Cancel", "OK"} default button "OK"';
            const result = execSync('osascript -e \'' + script + '\'', {
                encoding: 'utf8',
                timeout: 60000
            });
            const match = result.match(/text returned:(.+)/);
            return match ? match[1].trim() : null;
        } else {
            try {
                const result = execSync('zenity --entry --title="License Required" --text="Enter your license key:"', {
                    encoding: 'utf8',
                    timeout: 30000
                });
                return result.trim();
            } catch (e) {
                try {
                    execSync('dialog --msgbox "License Required. Please enter your license key in the console." 10 50', {
                        timeout: 10000
                    });
                } catch (e2) {}
            }
        }
    } catch (e) {
        console.log('[License] Dialog failed:', e.message);
    }
    
    const readline = require('readline');
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    
    return new Promise((resolve) => {
        rl.question('Enter license key: ', (answer) => {
            rl.close();
            resolve(answer.trim());
        });
    });
}

async function _$PREFIX_main() {
    console.log('[License] License Wrapper v' + _$PREFIX_VERSION);
    console.log('[License] Product: ' + _$PREFIX_PRODUCT_ID);
    
    const hwid = _$PREFIX_getHWID();
    console.log('[License] HWID: ' + hwid);
    
    const licenseData = _$PREFIX_loadLicenseFile();
    
    if (licenseData) {
        const result = _$PREFIX_validateOffline(licenseData, hwid);
        if (result.valid) {
            console.log('[License] Valid (offline)');
            return;
        }
    }
    
    console.log('[License] Validating online...');
    
    let licenseKey = _$PREFIX_LICENSE_KEY;
    if (licenseKey === 'GENERIC_BUILD' || !licenseKey) {
        licenseKey = await _$PREFIX_promptLicenseDialog();
    }
    
    if (!licenseKey) {
        _$PREFIX_showError('LICENSE REQUIRED', 'No license key provided.');
    }
    
    const result = await _$PREFIX_validateOnline(licenseKey, hwid);
    
    if (!result.valid) {
        const errorMsg = result.error || 'Unknown error';
        _$PREFIX_showError('LICENSE INVALID', 'Validation failed: ' + errorMsg);
    }
    
    if (_$PREFIX_LEASE_ENABLED) {
        const leaseUntil = Date.now() + _$PREFIX_LEASE_DURATION;
        const newLicenseData = {
            key: licenseKey,
            hwid: _$PREFIX_HWID_ENABLED ? hwid : null,
            validated_at: Date.now(),
            lease_until: leaseUntil,
            product_id: _$PREFIX_PRODUCT_ID
        };
        _$PREFIX_saveLicenseFile(newLicenseData);
        console.log('[License] Valid (online, lease until ' + new Date(leaseUntil).toLocaleString() + ')');
    } else {
        console.log('[License] Valid (online)');
    }
}

(async () => {
    await _$PREFIX_main();
    
    // ============ USER APPLICATION CODE BELOW ============
    $USER_CODE
})();
`;

module.exports = { UNIFIED_NODEJS_WRAPPER };

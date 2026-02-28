#!/usr/bin/env python3
"""
CodeVault Cloud Build Runner for Node.js
Standalone script to execute pkg builds in CI/CD environments.
Supports single-file and project-based Node.js builds.
License protection: Uses PREFIX/SUFFIX pattern to properly wrap user code.
"""

import os
import sys
import json
import logging
import subprocess
import argparse
import re
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [NodeRunner] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


LICENSE_WRAPPER_PREFIX = r"""// ============ CODEVAULT LICENSE WRAPPER - DO NOT REMOVE ============
// DEBUG: File-based logging FIRST (before anything can fail)
(function() {
    try {
        var _cv_debug_fs = require('fs');
        var _cv_debug_path = require('path');
        var _cv_exeDir = process.pkg ? _cv_debug_path.dirname(process.execPath) : __dirname;
        var _cv_logFile = _cv_debug_path.join(_cv_exeDir, 'codevault_debug.log');
        global._cv_log = function(msg) {
            try {
                var timestamp = new Date().toISOString();
                _cv_debug_fs.appendFileSync(_cv_logFile, '[' + timestamp + '] ' + msg + '\n');
            } catch(e) {}
        };
        global._cv_logFile = _cv_logFile;
        _cv_log('=== APPLICATION START ===');
        _cv_log('Version: 2026-02-21-v2');
        _cv_log('execPath: ' + process.execPath);
        _cv_log('cwd: ' + process.cwd());
        _cv_log('platform: ' + process.platform);
        _cv_log('pkg: ' + !!process.pkg);
        _cv_log('node: ' + process.version);
    } catch(e) {
        // If debug logging fails, continue anyway
    }
})();

// CRITICAL: Wrap everything in try-catch to catch module load errors
try {
if (typeof _cv_log === 'function') _cv_log('Entering main try block');
process.stderr.write('[CodeVault] Starting... (v2026-02-21-v2)\n');

// ============ ERROR HANDLERS (SET UP FIRST) ============
function _cv_showErrorAndWait(type, error) {
    if (typeof _cv_log === 'function') _cv_log('ERROR: ' + type + ' - ' + (error.message || String(error)));
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('  [ERROR] ' + type + '\n');
    process.stderr.write('='.repeat(60) + '\n');
    process.stderr.write('\nError: ' + (error.message || String(error)) + '\n');
    if (error.stack) {
        process.stderr.write('\nStack trace:\n');
        process.stderr.write(error.stack + '\n');
        if (typeof _cv_log === 'function') _cv_log('Stack: ' + error.stack);
    }
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('Press any key to exit...\n');
    process.stderr.write('Log file: ' + (global._cv_logFile || 'N/A') + '\n');
    process.stderr.write('='.repeat(60) + '\n');
    try {
        if (process.platform === 'win32') {
            require('child_process').spawnSync('cmd', ['/c', 'pause'], {stdio: 'inherit'});
        } else {
            require('child_process').spawnSync('bash', ['-c', 'read -n 1 -p "Press any key..."'], {stdio: 'inherit'});
        }
    } catch (e) {
        var start = Date.now();
        while (Date.now() - start < 10000) {}
    }
    process.exit(1);
}

process.on('uncaughtException', function(error) {
    _cv_showErrorAndWait('UNCAUGHT EXCEPTION', error);
});

process.on('unhandledRejection', (reason, promise) => {
    _cv_showErrorAndWait('UNHANDLED REJECTION', reason);
});

// ============ CONFIGURATION ============
process.stderr.write('[CodeVault] Loading configuration...\n');
const _cv_LICENSE_KEY = "{license_key}";
const _cv_SERVER_URL = "{server_url}";
const _cv_APP_NAME = "{app_name}";
const _cv_LICENSE_MODE = "{license_mode}";
const _cv_DEMO_DURATION = {demo_duration};
const _cv_LEASE_ENABLED = {lease_enabled};

// Fallback URLs if primary server is unreachable
const _cv_FALLBACK_URLS = [
    "https://code-vault-b66848f67c75.herokuapp.com/api/v1/license/validate"
];

// ============ MODULES ============
const _cv_crypto = require('crypto');
const _cv_os = require('os');
const _cv_https = require('https');
const _cv_http = require('http');
const _cv_fs = require('fs');
const _cv_path = require('path');
const _cv_readline = require('readline');

// ============ UTILITY FUNCTIONS ============
function _cv_getExeDir() {
    if (process.pkg) {
        return _cv_path.dirname(process.execPath);
    }
    return __dirname;
}

function _cv_getLicenseKeyPath() {
    return _cv_path.join(_cv_getExeDir(), 'license.key');
}

function _cv_getLeasePath() {
    return _cv_path.join(_cv_getExeDir(), 'license.lease');
}

function _cv_getMachineSecret() {
    const info = `${_cv_os.hostname()}|${_cv_os.platform()}|${_cv_os.arch()}|CV_SALT_2026`;
    return _cv_crypto.createHash('sha256').update(info).digest();
}

function _cv_getHWID() {
    const components = [];
    
    try {
        const networkInterfaces = _cv_os.networkInterfaces();
        const macs = [];
        for (const name of Object.keys(networkInterfaces)) {
            for (const iface of networkInterfaces[name]) {
                if (!iface.internal && iface.mac && iface.mac !== '00:00:00:00:00:00') {
                    macs.push(iface.mac.toLowerCase());
                }
            }
        }
        if (macs.length > 0) {
            macs.sort();
            components.push('mac:' + macs[0]);
        }
    } catch (e) {}
    
    try {
        const cpus = _cv_os.cpus();
        if (cpus && cpus.length > 0 && cpus[0].model) {
            components.push('cpu:' + cpus[0].model.substring(0, 32));
        }
    } catch (e) {}
    
    if (process.platform === 'win32') {
        try {
            const { execSync } = require('child_process');
            try {
                const diskOutput = execSync('wmic diskdrive get serialnumber', { encoding: 'utf8', timeout: 5000 });
                const lines = diskOutput.trim().split('\n');
                if (lines.length > 1) {
                    const diskSerial = lines[1].trim();
                    if (diskSerial && diskSerial !== 'SerialNumber') {
                        components.push('disk:' + diskSerial);
                    }
                }
            } catch (e) {}
        } catch (e) {}
    }
    
    if (components.length > 0) {
        return _cv_crypto.createHash('sha256').update(components.join('|')).digest('hex').substring(0, 32);
    }
    
    const cpus = _cv_os.cpus();
    const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
    const info = `${_cv_os.hostname()}|${_cv_os.platform()}|${_cv_os.arch()}|${_cv_os.totalmem()}|${cpuModel}`;
    return _cv_crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
}

// ============ LEASE FUNCTIONS ============
const _cv_LEASE_DURATION = 24 * 60 * 60;
const _cv_CLOCK_DRIFT_MAX = 60 * 60;

function _cv_encryptLease(leaseData) {
    try {
        const secret = _cv_getMachineSecret();
        const dataJson = Buffer.from(JSON.stringify(leaseData), 'utf-8');
        const nonce = _cv_crypto.randomBytes(12);
        const cipher = _cv_crypto.createCipheriv('aes-256-gcm', secret, nonce);
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

function _cv_decryptLease(encryptedData) {
    try {
        const secret = _cv_getMachineSecret();
        const raw = Buffer.from(encryptedData, 'base64');
        if (raw.slice(0, 4).toString() === 'AES:') {
            const nonce = raw.slice(4, 16);
            const authTag = raw.slice(16, 32);
            const encrypted = raw.slice(32);
            const decipher = _cv_crypto.createDecipheriv('aes-256-gcm', secret, nonce);
            decipher.setAuthTag(authTag);
            const dataJson = Buffer.concat([decipher.update(encrypted), decipher.final()]);
            return JSON.parse(dataJson.toString('utf-8'));
        }
        return null;
    } catch (e) {
        return null;
    }
}

function _cv_saveLease(leaseData) {
    if (!_cv_LEASE_ENABLED) return false;
    try {
        const leasePath = _cv_getLeasePath();
        const encrypted = _cv_encryptLease(leaseData);
        if (encrypted) {
            _cv_fs.writeFileSync(leasePath, encrypted, 'utf-8');
            process.stderr.write('[CodeVault] Lease saved (24h offline access)\n');
            return true;
        }
    } catch (e) {}
    return false;
}

function _cv_loadLease() {
    if (!_cv_LEASE_ENABLED) return null;
    try {
        const leasePath = _cv_getLeasePath();
        if (_cv_fs.existsSync(leasePath)) {
            const encrypted = _cv_fs.readFileSync(leasePath, 'utf-8').trim();
            return _cv_decryptLease(encrypted);
        }
    } catch (e) {}
    return null;
}

function _cv_validateLease(licenseKey, hwid) {
    if (!_cv_LEASE_ENABLED) return {valid: false, message: 'Offline mode not enabled'};
    const lease = _cv_loadLease();
    if (!lease) return {valid: false, message: 'No lease found'};
    if (lease.hwid !== hwid) return {valid: false, message: 'HWID mismatch'};
    const keyHash = _cv_crypto.createHash('sha256').update(licenseKey).digest('hex');
    if (lease.license_key_hash !== keyHash) return {valid: false, message: 'License mismatch'};
    const currentTime = Math.floor(Date.now() / 1000);
    if (currentTime > lease.expires_at) return {valid: false, message: 'Lease expired'};
    const remaining = lease.expires_at - currentTime;
    const hours = Math.floor(remaining / 3600);
    const mins = Math.floor((remaining % 3600) / 60);
    process.stderr.write('[CodeVault] Offline lease valid (' + hours + 'h ' + mins + 'm remaining)\n');
    return {valid: true, message: 'Valid'};
}

// ============ LICENSE PROMPT ============
function _cv_promptForLicenseKey() {
    return new Promise((resolve) => {
        if (process.platform === 'win32') {
            try {
                const {spawnSync} = require('child_process');
                const psScript = `
Add-Type -AssemblyName System.Windows.Forms
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
                ], {encoding: 'utf-8', windowsHide: false});
                const key = (result.stdout || '').trim();
                if (key) {
                    resolve(key);
                    return;
                }
            } catch (e) {
                process.stderr.write('[CodeVault] GUI dialog failed, using console input\n');
            }
        }
        const rl = _cv_readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        process.stderr.write('\n' + '='.repeat(60) + '\n');
        process.stderr.write('  LICENSE KEY REQUIRED\n');
        process.stderr.write('  App: ' + _cv_APP_NAME + '\n');
        process.stderr.write('='.repeat(60) + '\n');
        process.stderr.write('\nEnter your license key: ');
        rl.question('', (answer) => {
            rl.close();
            resolve(answer ? answer.trim() : null);
        });
    });
}

function _cv_loadOrPromptLicense() {
    const licensePath = _cv_getLicenseKeyPath();
    if (_cv_fs.existsSync(licensePath)) {
        try {
            const key = _cv_fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {
                process.stderr.write('[CodeVault] Loaded license from file\n');
                return key;
            }
        } catch (e) {}
    }
    return _cv_promptForLicenseKey().then(key => {
        if (!key) {
            _cv_showErrorAndWait('LICENSE REQUIRED', new Error('No license key was provided.'));
        }
        try {
            _cv_fs.writeFileSync(licensePath, key, 'utf-8');
            process.stderr.write('[CodeVault] License key saved\n');
        } catch (e) {}
        return key;
    });
}

// ============ ONLINE VALIDATION ============
function _cv_validateOnline(licenseKey, hwid) {
    return _cv_validateWithUrl(licenseKey, hwid, _cv_SERVER_URL);
}

function _cv_validateWithUrl(licenseKey, hwid, serverUrl, fallbackIndex) {
    if (typeof fallbackIndex === 'undefined') fallbackIndex = 0;
    return new Promise((resolve) => {
        try {
            const urlObj = new URL(serverUrl);
            const postData = JSON.stringify({
                license_key: licenseKey,
                hwid: hwid,
                machine_name: _cv_os.hostname(),
                timestamp: Math.floor(Date.now() / 1000),
                nonce: _cv_crypto.randomBytes(16).toString('hex')
            });
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port || 443,
                path: urlObj.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                },
                timeout: 15000
            };
            const lib = urlObj.protocol === 'http:' ? _cv_http : _cv_https;
            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    try {
                        if (res.statusCode !== 200) {
                            // Try fallback if available
                            if (fallbackIndex < _cv_FALLBACK_URLS.length) {
                                process.stderr.write('[CodeVault] Primary server returned ' + res.statusCode + ', trying fallback...\n');
                                _cv_validateWithUrl(licenseKey, hwid, _cv_FALLBACK_URLS[fallbackIndex], fallbackIndex + 1).then(resolve);
                                return;
                            }
                            resolve({valid: false, error: 'HTTP ' + res.statusCode});
                            return;
                        }
                        const result = JSON.parse(body);
                        if (result.status === 'valid') {
                            const serverTime = result.server_time || result.timestamp || Math.floor(Date.now() / 1000);
                            const localTime = Math.floor(Date.now() / 1000);
                            const drift = Math.abs(localTime - serverTime);
                            if (drift <= _cv_CLOCK_DRIFT_MAX) {
                                const lease = {
                                    license_key_hash: _cv_crypto.createHash('sha256').update(licenseKey).digest('hex'),
                                    hwid: hwid,
                                    expires_at: serverTime + _cv_LEASE_DURATION,
                                    server_time: serverTime,
                                    validated_at: localTime
                                };
                                _cv_saveLease(lease);
                            }
                            resolve({valid: true});
                        } else {
                            resolve({valid: false, error: result.message || 'Invalid license'});
                        }
                    } catch (e) {
                        resolve({valid: false, error: 'Failed to parse response'});
                    }
                });
            });
            req.on('error', (err) => {
                // Try fallback if available
                if (fallbackIndex < _cv_FALLBACK_URLS.length) {
                    process.stderr.write('[CodeVault] Primary server unreachable (' + err.message + '), trying fallback...\n');
                    _cv_validateWithUrl(licenseKey, hwid, _cv_FALLBACK_URLS[fallbackIndex], fallbackIndex + 1).then(resolve);
                    return;
                }
                resolve({valid: false, error: err.message, offline: true});
            });
            req.on('timeout', () => {
                req.destroy();
                // Try fallback if available
                if (fallbackIndex < _cv_FALLBACK_URLS.length) {
                    process.stderr.write('[CodeVault] Primary server timeout, trying fallback...\n');
                    _cv_validateWithUrl(licenseKey, hwid, _cv_FALLBACK_URLS[fallbackIndex], fallbackIndex + 1).then(resolve);
                    return;
                }
                resolve({valid: false, error: 'Timeout', offline: true});
            });
            req.write(postData);
            req.end();
        } catch (e) {
            // Try fallback if available
            if (fallbackIndex < _cv_FALLBACK_URLS.length) {
                process.stderr.write('[CodeVault] Primary URL error, trying fallback...\n');
                _cv_validateWithUrl(licenseKey, hwid, _cv_FALLBACK_URLS[fallbackIndex], fallbackIndex + 1).then(resolve);
                return;
            }
            resolve({valid: false, error: e.message});
        }
    });
}

// ============ DEMO MODE ============
function _cv_checkDemoExpiry() {
    try {
        const exeDir = _cv_getExeDir();
        const demoFile = _cv_path.join(exeDir, '.demo_' + _cv_APP_NAME.replace(/[^a-zA-Z0-9]/g, '_'));
        if (_cv_fs.existsSync(demoFile)) {
            const data = _cv_fs.readFileSync(demoFile, 'utf8').trim();
            const startTime = parseInt(data);
            if (!isNaN(startTime)) {
                const elapsed = Date.now() - startTime;
                const maxDuration = _cv_DEMO_DURATION * 60 * 1000;
                if (elapsed > maxDuration) {
                    return {expired: true, remaining: 0};
                }
                return {expired: false, remaining: maxDuration - elapsed};
            }
        }
        _cv_fs.writeFileSync(demoFile, Date.now().toString());
        return {expired: false, remaining: _cv_DEMO_DURATION * 60 * 1000};
    } catch (e) {
        return {expired: false, remaining: _cv_DEMO_DURATION * 60 * 1000};
    }
}

// ============ DELETE LICENSE FILES ============
function _cv_deleteLicenseFiles() {
    try {
        const licensePath = _cv_getLicenseKeyPath();
        if (_cv_fs.existsSync(licensePath)) _cv_fs.unlinkSync(licensePath);
        const leasePath = _cv_getLeasePath();
        if (_cv_fs.existsSync(leasePath)) _cv_fs.unlinkSync(leasePath);
    } catch (e) {}
}

// ============ MAIN VALIDATION ============
async function _cv_validateLicense() {
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('  CODEVAULT LICENSE\n');
    process.stderr.write('  App: ' + _cv_APP_NAME + '\n');
    process.stderr.write('  Mode: ' + _cv_LICENSE_MODE.toUpperCase() + '\n');
    process.stderr.write('='.repeat(60) + '\n');
    
    let licenseKey = _cv_LICENSE_KEY;
    const hwid = _cv_getHWID();
    
    if (_cv_LICENSE_MODE === 'demo') {
        process.stderr.write('[CodeVault] Demo mode: ' + _cv_DEMO_DURATION + ' minutes trial\n');
        const demoStatus = _cv_checkDemoExpiry();
        if (demoStatus.expired) {
            _cv_showErrorAndWait('DEMO EXPIRED', new Error('Demo period has expired.\n\nPlease purchase a license at https://codevault.app'));
        }
        const remainingMin = Math.round(demoStatus.remaining / 60000);
        process.stderr.write('[CodeVault] Demo time remaining: ' + remainingMin + ' minutes\n');
        return true;
    }
    
    if (licenseKey === 'GENERIC_BUILD') {
        licenseKey = await _cv_loadOrPromptLicense();
    }
    
    process.stderr.write('[CodeVault] Validating license with server...\n');
    const result = await _cv_validateOnline(licenseKey, hwid);
    
    if (result.valid) {
        process.stderr.write('[CodeVault] License validated successfully!\n');
        return true;
    }
    
    if (result.offline && _cv_LEASE_ENABLED) {
        process.stderr.write('[CodeVault] Server unreachable, checking offline lease...\n');
        const leaseResult = _cv_validateLease(licenseKey, hwid);
        if (leaseResult.valid) {
            process.stderr.write('[CodeVault] Running with valid offline lease\n');
            return true;
        }
        _cv_showErrorAndWait('OFFLINE - LICENSE REQUIRED', new Error('Cannot validate license offline.\n\n' + leaseResult.message + '\n\nPlease connect to the internet.'));
    }
    
    if (licenseKey === 'GENERIC_BUILD') {
        _cv_deleteLicenseFiles();
    }
    _cv_showErrorAndWait('LICENSE INVALID', new Error(result.error || 'License key is invalid or expired.\n\nPlease check your license key and try again.'));
}

// ============ STARTUP ============
(async () => {
    try {
        if (typeof _cv_log === 'function') _cv_log('Starting license validation');
        process.stderr.write('[CodeVault] Validating license...\n');
        var valid = await _cv_validateLicense();
        if (!valid) {
            if (typeof _cv_log === 'function') _cv_log('License validation returned false');
            process.exit(1);
        }
        if (typeof _cv_log === 'function') _cv_log('License valid, starting user code');
        process.stderr.write('[CodeVault] License valid, starting application...\n');
        process.stderr.write('='.repeat(60) + '\n\n');
        // ============ USER CODE STARTS HERE ============

"""

LICENSE_WRAPPER_SUFFIX = r"""
        // ============ USER CODE ENDS HERE ============
        if (typeof _cv_log === 'function') _cv_log('User code completed successfully');
    } catch (e) {
        if (typeof _cv_log === 'function') _cv_log('User code threw error: ' + (e.message || String(e)));
        _cv_showErrorAndWait('APPLICATION ERROR', e);
    }
})().catch(function(e) {
    if (typeof _cv_log === 'function') _cv_log('Async IIFE rejected: ' + (e.message || String(e)));
    _cv_showErrorAndWait('STARTUP ERROR', e);
});
} catch (globalError) {
    if (typeof _cv_log === 'function') _cv_log('GLOBAL ERROR: ' + (globalError.message || String(globalError)));
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('  [ERROR] CRITICAL STARTUP ERROR\n');
    process.stderr.write('='.repeat(60) + '\n');
    process.stderr.write('\nError: ' + (globalError.message || String(globalError)) + '\n');
    if (globalError.stack) {
        process.stderr.write('\nStack trace:\n' + globalError.stack + '\n');
    }
    process.stderr.write('\n' + '='.repeat(60) + '\n');
    process.stderr.write('Press any key to exit...\n');
    process.stderr.write('Log file: ' + (global._cv_logFile || 'N/A') + '\n');
    process.stderr.write('='.repeat(60) + '\n');
    try {
        if (process.platform === 'win32') {
            require('child_process').spawnSync('cmd', ['/c', 'pause'], {stdio: 'inherit'});
        } else {
            require('child_process').spawnSync('bash', ['-c', 'read -n 1 -p "Press any key..."'], {stdio: 'inherit'});
        }
    } catch (e) {
        var start = Date.now();
        while (Date.now() - start < 10000) {}
    }
    process.exit(1);
}
"""


class NodeJSBuilder:
    """Build Node.js projects using @yao-pkg/pkg with proper license wrapping."""

    def __init__(self, config: dict, source_dir: Path):
        self.config = config
        self.source_dir = source_dir
        self.project_name = config.get("project_name", "app")
        self.output_name = config.get("output_name", "app")
        self.entry_file = config.get("entry_file", "index.js")
        self.license_key = config.get("license_key", "GENERIC_BUILD")
        self.license_mode = config.get("license_mode", "generic")
        self.demo_duration = config.get("demo_duration", 60)
        self.target_platforms = config.get("target_platforms", ["windows"])
        self.api_url = config.get("api_url", "")
        self.skip_obfuscation = config.get("skip_obfuscation", True)
        self.enable_lease = config.get("enable_lease", False)
        self._resolved_entry_file = None

    def _find_entry_file(self) -> Optional[str]:
        """Find and validate the entry file, handling various path formats."""
        possible_paths = [
            self.entry_file,
            self.entry_file.replace("node_app/", "").replace("node_app\\", ""),
            self.entry_file.replace("src/", "").replace("src\\", ""),
        ]

        for path in possible_paths:
            full_path = self.source_dir / path
            if full_path.exists():
                self._resolved_entry_file = path
                logger.info(f"Found entry file at: {path}")
                return path

        js_files = list(self.source_dir.glob("*.js"))
        if js_files:
            for priority in ["index.js", "main.js", "app.js"]:
                for f in js_files:
                    if f.name == priority:
                        self._resolved_entry_file = f.name
                        logger.info(f"Using auto-detected entry file: {f.name}")
                        return f.name

            self._resolved_entry_file = js_files[0].name
            logger.info(f"Using first JS file as entry: {js_files[0].name}")
            return js_files[0].name

        logger.error("No JavaScript entry file found!")
        return None

    def validate_js_syntax(self, js_file: Path) -> Tuple[bool, str]:
        """Validate JavaScript syntax using Node.js --check flag.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = subprocess.run(
                ["node", "--check", str(js_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, ""

            error_msg = result.stderr or result.stdout or "Unknown syntax error"
            return False, error_msg.strip()
        except subprocess.TimeoutExpired:
            return False, "Syntax check timed out"
        except FileNotFoundError:
            logger.warning("Node.js not found for syntax check, skipping validation")
            return True, ""
        except Exception as e:
            logger.warning(f"Syntax check failed: {e}")
            return True, ""

    def prepare_package_json(self) -> bool:
        """Prepare package.json for pkg, creating if needed."""
        package_json_path = self.source_dir / "package.json"

        if package_json_path.exists():
            try:
                with open(package_json_path, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not parse existing package.json: {e}")
                pkg_data = {}
        else:
            pkg_data = {}

        entry = self._resolved_entry_file or self._find_entry_file()
        if not entry:
            logger.error("Cannot prepare package.json without entry file")
            return False

        pkg_data["name"] = pkg_data.get(
            "name", self.output_name.lower().replace("-", "_").replace(" ", "_")
        )
        pkg_data["version"] = pkg_data.get("version", "1.0.0")
        pkg_data["main"] = "_cv_bootstrap.js"
        pkg_data["bin"] = "_cv_bootstrap.js"
        pkg_data["private"] = True

        pkg_data["pkg"] = {
            "outputPath": "build_output",
            "targets": ["node20-win-x64", "node20-linux-x64"],
            "assets": pkg_data.get("pkg", {}).get("assets", []),
        }

        try:
            with open(package_json_path, "w", encoding="utf-8") as f:
                json.dump(pkg_data, f, indent=2)
            logger.info(f"Created/updated package.json with main: {entry}")
            logger.info(
                f"Package content: name={pkg_data['name']}, private={pkg_data['private']}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to write package.json: {e}")
            return False

    def inject_license_protection(self) -> bool:
        """Inject license protection by creating a bootstrap file that loads the user code."""
        if not self._resolved_entry_file:
            self._find_entry_file()

        if not self._resolved_entry_file:
            logger.error("Entry file not found, skipping license protection")
            return False

        entry_path = self.source_dir / self._resolved_entry_file

        if not entry_path.exists():
            logger.error(f"Entry file not found: {self._resolved_entry_file}")
            return False

        try:
            # Generate wrapped code using PREFIX + dynamic import + SUFFIX pattern
            prefix = self._generate_prefix()
            suffix = LICENSE_WRAPPER_SUFFIX
            
            entry_import_path = str(self._resolved_entry_file).replace('\\', '/')
            if not entry_import_path.startswith('./') and not entry_import_path.startswith('../'):
                entry_import_path = './' + entry_import_path

            # Properly wrap user code by dynamic import/require
            bootstrap_code = f"""{prefix}
        // Load user code
        try {{
            require('{entry_import_path}');
        }} catch (e) {{
            if (e.code === 'ERR_REQUIRE_ESM') {{
                // Fallback to dynamic import for ESM
                await import('{entry_import_path}');
            }} else {{
                throw e;
            }}
        }}
{suffix}"""

            bootstrap_path = self.source_dir / "_cv_bootstrap.js"
            bootstrap_path.write_text(bootstrap_code, encoding="utf-8")

            # CRITICAL: Validate the WRAPPED code syntax too!
            logger.info("Validating bootstrap code syntax...")
            is_valid_wrapped, wrapped_error = self.validate_js_syntax(bootstrap_path)
            if not is_valid_wrapped:
                logger.error(f"Bootstrap code has syntax errors:")
                logger.error(wrapped_error)
                return False
                
            logger.info("Wrapped code syntax validation passed")
            logger.info("Injected license protection via _cv_bootstrap.js")
            return True

        except Exception as e:
            logger.error(f"Failed to inject license protection: {e}")
            return False

    def _generate_prefix(self) -> str:
        """Generate license wrapper PREFIX with configuration values."""
        prefix = LICENSE_WRAPPER_PREFIX

        # Escape values for JavaScript string literals
        def escape_js_string(s: str) -> str:
            return (
                s.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
            )

        prefix = prefix.replace("{license_key}", escape_js_string(self.license_key))
        prefix = prefix.replace("{server_url}", escape_js_string(self.api_url))
        prefix = prefix.replace("{app_name}", escape_js_string(self.project_name))
        prefix = prefix.replace("{license_mode}", self.license_mode or "generic")
        prefix = prefix.replace("{demo_duration}", str(self.demo_duration or 60))
        prefix = prefix.replace(
            "{lease_enabled}", "true" if self.enable_lease else "false"
        )

        return prefix

    def install_dependencies(self) -> bool:
        """Install npm dependencies."""
        package_json_path = self.source_dir / "package.json"

        if not package_json_path.exists():
            logger.warning("No package.json found, skipping npm install")
            return True

        try:
            logger.info("Installing npm dependencies...")
            result = subprocess.run(
                ["npm", "install", "--quiet"],
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                logger.warning(f"npm install stderr: {result.stderr}")
                logger.info(f"npm install stdout: {result.stdout}")
            else:
                logger.info("Dependencies installed successfully")

            return True
        except subprocess.TimeoutExpired:
            logger.error("npm install timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

    def run_obfuscation(self) -> bool:
        """Run JavaScript obfuscation on source files (with syntax validation)."""
        if self.skip_obfuscation:
            logger.info("Skipping obfuscation (disabled in config)")
            return True

        logger.info("Installing JavaScript Obfuscator...")

        try:
            result = subprocess.run(
                ["npm", "install", "-g", "javascript-obfuscator", "--quiet"],
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.warning(f"Failed to install obfuscator: {result.stderr}")
                logger.info("Continuing without obfuscation")
                return True

            logger.info("Obfuscating JavaScript files...")

            js_files = []
            for js_file in self.source_dir.rglob("*.js"):
                if "node_modules" in str(js_file):
                    continue
                if js_file.name.startswith("."):
                    continue
                if ".github" in str(js_file):
                    continue
                js_files.append(js_file)

            if not js_files:
                logger.warning("No JavaScript files found to obfuscate")
                return True

            obfuscate_args = [
                "--compact",
                "true",
                "--rename-globals",
                "false",  # Changed to false for better compatibility
                "--string-array",
                "true",
                "--string-array-threshold",
                "0.75",
                "--string-array-encoding",
                "base64",  # Changed from rc4 for compatibility
                "--string-array-shuffle",
                "true",
                "--identifier-names-generator",
                "hexadecimal",
                "--control-flow-flattening",
                "false",  # Disable to reduce parse errors
                "--dead-code-injection",
                "false",  # Disable to reduce parse errors
                "--self-defending",
                "false",  # Disable to avoid runtime issues
                "--ignore-imports",
                "true",
            ]

            for js_file in js_files:
                original_content = js_file.read_text(encoding="utf-8")

                # Skip files that already have license wrapper (they're complex enough)
                if "CODEVAULT LICENSE WRAPPER" in original_content:
                    logger.info(
                        f"Skipping obfuscation for {js_file.name} (contains license wrapper)"
                    )
                    continue

                cmd = [
                    "npx",
                    "javascript-obfuscator",
                    str(js_file),
                    "--output",
                    str(js_file),
                ] + obfuscate_args

                result = subprocess.run(
                    cmd,
                    cwd=str(self.source_dir),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    logger.warning(
                        f"Failed to obfuscate {js_file.name}, keeping original"
                    )
                    js_file.write_text(original_content, encoding="utf-8")
                else:
                    logger.info(f"Obfuscated: {js_file.name}")

            logger.info("Obfuscation complete")
            return True

        except subprocess.TimeoutExpired:
            logger.warning("Obfuscation timed out, continuing without obfuscation")
            return True
        except Exception as e:
            logger.warning(f"Obfuscation error: {e}, continuing without obfuscation")
            return True

    def build_targets(self) -> dict:
        """Build for all target platforms."""
        results = {}

        target_map = {
            "windows": "node20-win-x64",
            "linux": "node20-linux-x64",
            "macos": "node20-macos-x64",
        }

        for platform in self.target_platforms:
            pkg_target = target_map.get(platform)
            if not pkg_target:
                logger.warning(f"Unknown platform: {platform}")
                continue

            logger.info(f"Building for {platform} ({pkg_target})...")
            success = self._build_single_target(pkg_target, platform)
            results[platform] = "completed" if success else "failed"

        return results

    def _build_single_target(self, pkg_target: str, platform: str) -> bool:
        """Build for a single target platform."""
        output_dir = self.source_dir / f"build_output_{platform}"
        output_dir.mkdir(parents=True, exist_ok=True)

        if platform == "windows":
            output_filename = f"{self.output_name}.exe"
        else:
            output_filename = self.output_name

        full_output_path = output_dir / output_filename

        cmd = [
            "npx",
            "@yao-pkg/pkg",
            ".",
            "--target",
            pkg_target,
            "--output",
            str(full_output_path),
            "--compress",
            "GZip",
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        result = None
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )

            logger.info(f"pkg stdout: {result.stdout}")

            if result.stderr:
                logger.info(f"pkg stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"pkg build failed with code {result.returncode}")
                logger.error(f"Full stdout: {result.stdout}")
                logger.error(f"Full stderr: {result.stderr}")
                return False

            if full_output_path.exists():
                size_kb = full_output_path.stat().st_size / 1024
                logger.info(f"Build complete: {output_filename} ({size_kb:.1f} KB)")
                return True
            else:
                logger.error(f"Output not found at: {full_output_path}")
                logger.info(f"Directory contents: {list(output_dir.iterdir())}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Build timed out (600s)")
            return False
        except Exception as e:
            logger.error(f"Build exception: {e}")
            if result:
                logger.error(f"Last stdout: {result.stdout}")
                logger.error(f"Last stderr: {result.stderr}")
            return False

    def run(self) -> bool:
        """Execute the full build process."""
        logger.info(f"Starting Node.js build for: {self.project_name}")
        logger.info(f"Source directory: {self.source_dir}")
        logger.info(f"Initial entry file config: {self.entry_file}")
        logger.info(f"Output name: {self.output_name}")
        logger.info(f"Target platforms: {self.target_platforms}")

        logger.info(
            f"Directory contents: {[f.name for f in self.source_dir.iterdir()]}"
        )

        entry = self._find_entry_file()
        if not entry:
            logger.error("Could not find entry file - aborting build")
            return False

        logger.info(f"Resolved entry file: {entry}")

        if not self.prepare_package_json():
            return False

        # Inject license protection with proper wrapping
        if not self.inject_license_protection():
            logger.error("License protection injection failed - aborting build")
            return False

        if not self.install_dependencies():
            logger.warning("Dependency installation had issues, continuing anyway")

        if not self.run_obfuscation():
            logger.warning("Obfuscation failed, continuing without")

        results = self.build_targets()

        success = any(s == "completed" for s in results.values())

        if success:
            logger.info("Build completed successfully")
        else:
            logger.error("All builds failed")
            for platform, status in results.items():
                logger.error(f"  {platform}: {status}")

        return success


def main():
    parser = argparse.ArgumentParser(description="CodeVault Node.js Build Runner")
    parser.add_argument("--config", required=True, help="JSON config string")
    parser.add_argument("--source", required=True, help="Source directory path")

    args = parser.parse_args()

    try:
        config = json.loads(args.config)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid config JSON: {e}")
        sys.exit(1)

    source_dir = Path(args.source)
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)

    builder = NodeJSBuilder(config, source_dir)
    success = builder.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

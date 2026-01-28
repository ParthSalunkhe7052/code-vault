// === CodeVault License Validation ===
// This wrapper is injected at the top of the user's Node.js entry file.
// Placeholders: __LICENSE_KEY__, __API_URL__
const os = require('os');
const crypto = require('crypto');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CV_LICENSE_KEY = '__LICENSE_KEY__';
const CV_API_URL = '__API_URL__';

function getHWID() {
  const cpus = os.cpus()[0]?.model || 'unknown';
  const networkInterfaces = os.networkInterfaces();
  const mac = Object.values(networkInterfaces).flat().find(i => !i.internal && i.mac)?.mac || '00:00:00:00:00:00';
  return crypto.createHash('sha256').update(cpus + '|' + mac).digest('hex');
}

function getLicenseKeyPath() {
  const exeDir = process.pkg ? path.dirname(process.execPath) : __dirname;
  return path.join(exeDir, 'license.key');
}

function loadSavedKey() {
  try {
    const keyPath = getLicenseKeyPath();
    if (fs.existsSync(keyPath)) {
      return fs.readFileSync(keyPath, 'utf8').trim();
    }
  } catch (e) {}
  return null;
}

function saveKey(key) {
  try {
    fs.writeFileSync(getLicenseKeyPath(), key, 'utf8');
  } catch (e) {}
}

async function validateLicense(key) {
  if (!CV_API_URL) return true;
  
  const hwid = getHWID();
  const nonce = crypto.randomBytes(16).toString('hex');
  const timestamp = Math.floor(Date.now() / 1000);
  
  const payload = JSON.stringify({
    license_key: key,
    hwid: hwid,
    nonce: nonce,
    timestamp: timestamp,
    machine_name: os.hostname()
  });
  
  return new Promise((resolve, reject) => {
    const url = new URL(CV_API_URL);
    const protocol = url.protocol === 'https:' ? https : http;
    
    const req = protocol.request({
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: 15000
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          // FIX: Check status === 'valid' instead of valid === true
          if (res.statusCode === 200 && response.status === 'valid') {
            console.log('[CodeVault] License validated successfully');
            resolve(true);
          } else {
            console.error('[CodeVault] License validation failed:', response.message || 'Invalid license');
            resolve(false);
          }
        } catch (e) {
          console.error('[CodeVault] License validation error:', e.message);
          resolve(false);
        }
      });
    });
    
    req.on('error', (e) => {
      console.error('[CodeVault] License server unreachable:', e.message);
      resolve(false);
    });
    
    req.on('timeout', () => {
      req.destroy();
      console.error('[CodeVault] License validation timed out');
      resolve(false);
    });
    
    req.write(payload);
    req.end();
  });
}

async function licenseCheck() {
  let key = CV_LICENSE_KEY;
  
  // Generic build - try saved key or prompt
  if (!key || key === 'GENERIC_BUILD') {
    const savedKey = loadSavedKey();
    if (savedKey) {
      console.log('[CodeVault] Found saved license, validating...');
      if (await validateLicense(savedKey)) {
        return true;
      }
      console.log('[CodeVault] Saved license invalid.');
    }
    
    // Prompt for key (console only for Node.js)
    const readline = require('readline');
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    
    key = await new Promise(resolve => {
      console.log('\n' + '='.repeat(50));
      console.log('  LICENSE REQUIRED');
      console.log('='.repeat(50));
      rl.question('\nEnter license key: ', answer => {
        rl.close();
        resolve(answer.trim());
      });
    });
    
    if (!key) {
      console.error('[CodeVault] No license key provided.');
      process.exit(1);
    }
    
    if (await validateLicense(key)) {
      saveKey(key);
      console.log('[CodeVault] License activated!');
      return true;
    } else {
      console.error('[CodeVault] Invalid license key.');
      process.exit(1);
    }
  }
  
  // Fixed key mode
  if (await validateLicense(key)) {
    return true;
  }
  
  console.error('[CodeVault] Embedded license is invalid.');
  process.exit(1);
}

// === End CodeVault ===

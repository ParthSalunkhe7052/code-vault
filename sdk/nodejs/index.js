const crypto = require('crypto');
const os = require('os');
const https = require('https');
const http = require('http');

class CodeVaultClient {
    constructor(licenseKey, serverUrl, publicKeyPem = null) {
        this.licenseKey = licenseKey;
        this.serverUrl = serverUrl.replace(/\/$/, '');
        this.publicKeyPem = publicKeyPem;
        this.sessionToken = null;
        this.features = [];
        this.variables = {};
        this._heartbeatInterval = null;

        // Auto-release on exit
        process.on('exit', () => this.releaseSync());
    }

    _getHwid() {
        const cpus = os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${os.hostname()}|${os.platform()}|${os.arch()}|${os.totalmem()}|${cpuModel}`;
        return crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
    }

    _verifySignature(result) {
        if (!this.publicKeyPem) return true;
        if (!result.signature) return false;

        try {
            const features = JSON.stringify((result.features || []).slice().sort());
            const variables = JSON.stringify(result.variables || {});
            const msg = [
                result.status || '',
                result.expires_at != null ? String(result.expires_at) : '',
                features,
                variables,
                result.client_nonce || result.nonce || '',
                result.server_nonce || '',
                result.timestamp != null ? String(result.timestamp) : '',
                result.server_time != null ? String(result.server_time) : '',
            ].join('|');

            const sigBuf = Buffer.from(result.signature, 'base64');
            return crypto.verify(
                null,
                Buffer.from(msg, 'utf-8'),
                { key: this.publicKeyPem, format: 'pem', type: 'spki' },
                sigBuf
            );
        } catch (e) {
            return false;
        }
    }

    async validate() {
        const hwid = this._getHwid();
        const postData = JSON.stringify({
            license_key: this.licenseKey,
            hwid: hwid,
            machine_name: os.hostname(),
            timestamp: Math.floor(Date.now() / 1000),
            nonce: crypto.randomBytes(16).toString('hex')
        });

        const url = new URL(`${this.serverUrl}/api/v1/license/validate`);
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        return new Promise((resolve, reject) => {
            const lib = url.protocol === 'https:' ? https : http;
            const req = lib.request(url, options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    if (res.statusCode === 200) {
                        try {
                            const result = JSON.parse(body);
                            if (!this._verifySignature(result)) {
                                return reject(new Error('Server response signature invalid'));
                            }

                            if (result.status === 'valid') {
                                this.features = result.features || [];
                                this.variables = result.variables || {};
                                this.sessionToken = this.variables['_cv_session_token'];

                                const interval = result.heartbeat_interval || 300;
                                this._startHeartbeat(interval * 1000);
                                resolve(true);
                            } else {
                                resolve(false);
                            }
                        } catch (e) {
                            reject(e);
                        }
                    } else {
                        reject(new Error(`Server returned ${res.statusCode}`));
                    }
                });
            });

            req.on('error', reject);
            req.write(postData);
            req.end();
        });
    }

    _startHeartbeat(ms) {
        if (this._heartbeatInterval) return;
        this._heartbeatInterval = setInterval(() => {
            this._sendHeartbeat().catch(() => {});
        }, ms);
    }

    async _sendHeartbeat() {
        const postData = JSON.stringify({
            license_key: this.licenseKey,
            hwid: this._getHwid(),
            timestamp: Math.floor(Date.now() / 1000),
            nonce: crypto.randomBytes(16).toString('hex')
        });

        const url = new URL(`${this.serverUrl}/api/v1/license/heartbeat`);
        const options = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        };

        const lib = url.protocol === 'https:' ? https : http;
        const req = lib.request(url, options);
        req.write(postData);
        req.end();
    }

    releaseSync() {
        if (!this.sessionToken) return;
        if (this._heartbeatInterval) clearInterval(this._heartbeatInterval);

        const postData = JSON.stringify({
            license_key: this.licenseKey,
            hwid: this._getHwid(),
            session_token: this.sessionToken
        });

        // Use sync spawn to ensure release happens before process dies
        const url = `${this.serverUrl}/api/v1/license/release`;
        try {
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
        } catch (e) {}
    }
}

module.exports = { CodeVaultClient };

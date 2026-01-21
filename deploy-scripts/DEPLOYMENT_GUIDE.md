# 🚀 Digital Ocean Deployment Guide for CodeVault

This guide walks through deploying CodeVault backend to your Digital Ocean droplet at **165.227.76.219**.

---

## 📋 Prerequisites Checklist

- [x] Digital Ocean droplet created (165.227.76.219)
- [x] Ubuntu 22.04 LTS installed
- [x] SSH key generated locally (`~/.ssh/id_ed25519`)
- [x] Domain purchased (parth7.me)
- [ ] Droplet is powered ON and accessible
- [ ] SSH key added to droplet
- [ ] Git repository cloned on droplet

---

## 🔧 Part 1: Fix SSH Access (CURRENT BLOCKER)

### Issue: SSH Connection Refused

**Status:** ❌ `ssh root@165.227.76.219` → Connection refused

### Solution Steps:

#### Option A: Via Digital Ocean Console (Recommended)

1. **Log into Digital Ocean Dashboard**
   - Go to: https://cloud.digitalocean.com/droplets
   - Find your droplet

2. **Check Droplet Status**
   - Ensure it shows **"Active"** (green indicator)
   - If OFF: Click "Power On"

3. **Access via Console**
   - Click on droplet name
   - Click **"Console"** button (top right)
   - This opens a web-based terminal

4. **Add Your SSH Key**
   ```bash
   # In the console, run:
   mkdir -p ~/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICSxx7HT31lAUYDz37YIbfMw1NIWpxev/G1vuB9RqUbU parth.ajit7052@gmail.com" >> ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

5. **Verify SSH is Running**
   ```bash
   systemctl status ssh
   # If not running:
   systemctl start ssh
   systemctl enable ssh
   ```

#### Option B: Rebuild Droplet with SSH Key

1. In Digital Ocean Dashboard → Droplet Settings
2. Click **"Destroy"** (backup first if needed)
3. Create new droplet:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic - $12/month (2GB RAM, 1 CPU)
   - **Region:** Choose closest to you
   - **Authentication:** SSH Key → Add your public key:
     ```
     ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICSxx7HT31lAUYDz37YIbfMw1NIWpxev/G1vuB9RqUbU
     ```
4. Note the new IP address (might change)

---

## 🌐 Part 2: Configure DNS (Namecheap)

### Steps to Add Subdomain:

1. **Log into Namecheap**
   - Go to: https://www.namecheap.com/myaccount/login/
   - Navigate to **Domain List** → **parth7.me** → **Manage**

2. **Configure Advanced DNS**
   - Click **"Advanced DNS"** tab
   - Click **"Add New Record"**

3. **Add API Subdomain**
   - **Type:** `A Record`
   - **Host:** `api.codevault`
   - **Value:** `165.227.76.219` (your droplet IP)
   - **TTL:** `Automatic` (or 300 seconds)
   - Click **"Save All Changes"**

4. **Add Root Subdomain (Optional)**
   - **Type:** `A Record`
   - **Host:** `codevault`
   - **Value:** `165.227.76.219`
   - **TTL:** `Automatic`

5. **Wait for DNS Propagation**
   - Usually takes 5-30 minutes
   - Check with: `nslookup api.codevault.parth7.me`

### Expected DNS Configuration:

```
api.codevault.parth7.me  →  165.227.76.219  (A Record)
codevault.parth7.me      →  Vercel IP        (CNAME or A Record)
```

---

## ⚙️ Part 3: Server Setup (Automated Script)

### Step 1: Transfer Setup Script

Once SSH is working, transfer the setup script:

```bash
# From your local machine:
scp -i ~/.ssh/id_ed25519 deploy-scripts/setup-server.sh root@165.227.76.219:/root/
```

### Step 2: Run Setup Script

```bash
# SSH into droplet:
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219

# Run setup script:
cd /root
chmod +x setup-server.sh
./setup-server.sh
```

**What this script does:**
- ✅ Updates system packages
- ✅ Installs Docker & Docker Compose
- ✅ Installs Nginx
- ✅ Installs Certbot (for SSL)
- ✅ Configures firewall (UFW)
- ✅ Creates helper scripts (deploy-codevault, codevault-logs, codevault-status)
- ✅ Sets up log rotation

**Duration:** ~10-15 minutes

---

## 📦 Part 4: Deploy Application

### Step 1: Clone Repository (if not already done)

```bash
# SSH into droplet:
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219

# Clone repository:
cd /root
git clone https://github.com/Parth7052/CodeVault.git codevault
cd codevault/CodeVaultV1
```

### Step 2: Create Production .env File

```bash
# Create config directory:
mkdir -p /etc/codevault

# Upload .env file from local:
# Exit SSH first (Ctrl+D), then from local:
scp -i ~/.ssh/id_ed25519 deploy-scripts/production.env root@165.227.76.219:/etc/codevault/.env
```

### Step 3: Deploy Application

```bash
# SSH back in:
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219

# Run deployment script:
deploy-codevault
```

**What this does:**
- Pulls latest code from GitHub
- Builds Docker image
- Stops old container (if any)
- Starts new container with production config
- Mounts persistent uploads directory

### Step 4: Verify Container is Running

```bash
# Check status:
codevault-status

# View logs:
codevault-logs

# Check health endpoint:
curl http://localhost:8000/api/v1/health
```

**Expected output:**
```json
{"status": "healthy", "database": "connected"}
```

---

## 🔒 Part 5: Configure Nginx & SSL

### Step 1: Upload Nginx Configuration

```bash
# From local machine:
scp -i ~/.ssh/id_ed25519 deploy-scripts/nginx-codevault.conf root@165.227.76.219:/etc/nginx/sites-available/codevault
```

### Step 2: Enable Site

```bash
# SSH into droplet:
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219

# Create symbolic link:
ln -s /etc/nginx/sites-available/codevault /etc/nginx/sites-enabled/

# Remove default site:
rm /etc/nginx/sites-enabled/default

# Test configuration:
nginx -t

# Reload Nginx:
systemctl reload nginx
```

### Step 3: Obtain SSL Certificate

**IMPORTANT:** DNS must be configured first (Part 2)!

```bash
# Request SSL certificate:
certbot --nginx -d api.codevault.parth7.me

# Follow prompts:
# - Enter email: parth.ajit7052@gmail.com
# - Agree to terms: Yes
# - Share email with EFF: No (optional)
# - Redirect HTTP to HTTPS: Yes
```

**Certbot will:**
- ✅ Verify domain ownership
- ✅ Generate SSL certificate
- ✅ Auto-configure Nginx for HTTPS
- ✅ Set up auto-renewal

### Step 4: Verify SSL

```bash
# Test HTTPS:
curl https://api.codevault.parth7.me/api/v1/health

# Check SSL certificate:
openssl s_client -connect api.codevault.parth7.me:443 -servername api.codevault.parth7.me < /dev/null
```

---

## 🔄 Part 6: Update Frontend & Redeploy

### Step 1: Verify Backend .env (Already Updated)

The `production.env` file already has:
```bash
PUBLIC_API_URL=https://api.codevault.parth7.me
CORS_ORIGINS=https://codevault.parth7.me,https://api.codevault.parth7.me
```

### Step 2: Frontend Already Configured

Your `frontend/.env.production` already has:
```bash
VITE_API_URL=https://api.codevault.parth7.me/api/v1
```

### Step 3: Redeploy Frontend on Vercel

**Option A: Via Git Push (Automatic)**
```bash
cd CodeVaultV1/frontend
git add .env.production
git commit -m "Update production API URL"
git push origin main
```

Vercel will auto-deploy (if GitHub integration is set up).

**Option B: Via Vercel CLI**
```bash
cd CodeVaultV1/frontend
npm install -g vercel
vercel --prod
```

**Option C: Via Vercel Dashboard**
1. Go to https://vercel.com/dashboard
2. Find your project
3. Click **"Redeploy"**

---

## ✅ Part 7: Post-Deployment Verification

### Backend Health Check

```bash
# From anywhere:
curl https://api.codevault.parth7.me/api/v1/health
```

**Expected:**
```json
{
  "status": "healthy",
  "database": "connected",
  "storage": "r2",
  "email": "enabled"
}
```

### Frontend Check

1. Visit: https://codevault.parth7.me
2. Open browser console (F12)
3. Check for API connection errors
4. Try logging in with test account

### Full Integration Test

1. **Register/Login**
   - Create account or login
   
2. **Verify Tier**
   - Check dashboard shows correct tier
   
3. **Create Project**
   - Upload sample code
   - Verify uploads work
   
4. **Generate License**
   - Create a license key
   - Verify database write
   
5. **Test Build** (if applicable)
   - Trigger a build
   - Check logs for progress

---

## 🛠️ Useful Commands Reference

### On Droplet:

```bash
# Deploy/redeploy application
deploy-codevault

# View real-time logs
codevault-logs

# Check application status
codevault-status

# Restart container
docker restart codevault-backend

# Enter container shell
docker exec -it codevault-backend bash

# View Nginx logs
tail -f /var/log/nginx/codevault-error.log
tail -f /var/log/nginx/codevault-access.log

# Check firewall status
ufw status

# Check SSL certificate expiry
certbot certificates
```

---

## 🔧 Troubleshooting

### Issue: DNS Not Resolving

**Check:**
```bash
nslookup api.codevault.parth7.me
```

**Fix:** Wait up to 30 minutes for propagation, or flush DNS:
```bash
# Windows:
ipconfig /flushdns

# Linux/Mac:
sudo systemd-resolve --flush-caches
```

---

### Issue: Nginx 502 Bad Gateway

**Cause:** Docker container not running or port mismatch

**Check:**
```bash
docker ps | grep codevault
curl http://localhost:8000/api/v1/health
```

**Fix:**
```bash
deploy-codevault
```

---

### Issue: SSL Certificate Error

**Cause:** DNS not configured or Certbot failed

**Check:**
```bash
certbot certificates
nginx -t
```

**Fix:**
```bash
# Re-run Certbot:
certbot --nginx -d api.codevault.parth7.me --force-renewal
```

---

### Issue: CORS Errors in Frontend

**Cause:** CORS_ORIGINS mismatch

**Check backend .env:**
```bash
cat /etc/codevault/.env | grep CORS_ORIGINS
```

**Should be:**
```bash
CORS_ORIGINS=https://codevault.parth7.me,https://api.codevault.parth7.me
```

**Fix:**
```bash
nano /etc/codevault/.env
# Update CORS_ORIGINS
# Save and restart:
docker restart codevault-backend
```

---

## 📊 Monitoring

### Check Resource Usage

```bash
# System resources:
htop

# Docker stats:
docker stats codevault-backend

# Disk usage:
df -h
```

### View Application Logs

```bash
# Last 100 lines:
docker logs --tail 100 codevault-backend

# Follow logs:
docker logs -f codevault-backend

# Search logs:
docker logs codevault-backend 2>&1 | grep ERROR
```

---

## 🔄 Updates & Maintenance

### Deploy New Version

```bash
ssh root@165.227.76.219
deploy-codevault
```

### Backup Data

```bash
# Backup uploads:
tar -czf codevault-uploads-$(date +%Y%m%d).tar.gz /opt/codevault/uploads

# Backup database (from Neon dashboard)
# Database is hosted on Neon, backups managed there
```

### Update SSL Certificate

```bash
# Auto-renewal is configured, but to force renewal:
certbot renew --force-renewal
systemctl reload nginx
```

---

## 🎯 Next Steps After Deployment

1. **Configure Stripe Webhook**
   - Go to Stripe Dashboard
   - Add webhook: `https://api.codevault.parth7.me/api/v1/webhook/stripe`
   - Copy webhook secret
   - Update `/etc/codevault/.env` with `STRIPE_WEBHOOK_SECRET`
   - Restart: `docker restart codevault-backend`

2. **Set Up Monitoring**
   - Consider UptimeRobot for uptime monitoring
   - Set up alerts for downtime

3. **Switch to Stripe Live Keys** (when ready)
   - Update `.env` with live keys
   - Test thoroughly before going live

4. **Set Up Backups**
   - Configure automated backups for `/opt/codevault/uploads`
   - Enable Neon database backups

---

**Status:** 🟡 Waiting for SSH access to be resolved

**Next Action:** Fix SSH connection as described in Part 1

---

*Last Updated: January 21, 2026*

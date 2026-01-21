# 🚀 CodeVault Deployment - Quick Start

## 📊 Current Status

- ✅ **Local Development**: Working
- ✅ **Deployment Scripts**: Created
- ✅ **Configuration Files**: Ready
- ✅ **SSH Key**: Generated
- ❌ **Droplet Access**: **BLOCKED** - Connection refused
- ⏳ **DNS Configuration**: Pending
- ⏳ **SSL Certificate**: Pending

---

## 🔴 IMMEDIATE ACTION REQUIRED

### Fix SSH Access to Droplet

**Your droplet at `165.227.76.219` is not accessible.**

**Steps to fix:**

1. **Check Digital Ocean Dashboard**
   - Visit: https://cloud.digitalocean.com/droplets
   - Verify droplet is **ON** (green "Active" status)
   - If OFF: Click "Power On"

2. **Use Web Console** (fastest method)
   - Click on droplet name
   - Click **"Console"** button (top right)
   - This opens web-based terminal

3. **Add SSH Key via Console**
   ```bash
   mkdir -p ~/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICSxx7HT31lAUYDz37YIbfMw1NIWpxev/G1vuB9RqUbU parth.ajit7052@gmail.com" >> ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

4. **Start SSH Service**
   ```bash
   systemctl start ssh
   systemctl enable ssh
   ```

5. **Test from your computer**
   ```bash
   ssh -i ~/.ssh/id_ed25519 root@165.227.76.219
   ```

---

## 📁 Files Created (Ready to Upload)

All files are in `CodeVaultV1/deploy-scripts/`:

| File | Purpose | Upload To |
|------|---------|-----------|
| `setup-server.sh` | Automated server setup | `/root/setup-server.sh` |
| `nginx-codevault.conf` | Nginx configuration | `/etc/nginx/sites-available/codevault` |
| `production.env` | Production environment | `/etc/codevault/.env` |
| `DEPLOYMENT_GUIDE.md` | Complete deployment guide | (reference) |

---

## ⚡ Once SSH Works - Run These Commands

### 1️⃣ Upload Setup Script
```bash
scp -i ~/.ssh/id_ed25519 deploy-scripts/setup-server.sh root@165.227.76.219:/root/
```

### 2️⃣ Run Setup (installs Docker, Nginx, etc.)
```bash
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219
chmod +x /root/setup-server.sh
./setup-server.sh
```
*Duration: ~10 minutes*

### 3️⃣ Upload Production Config
```bash
# From local:
scp -i ~/.ssh/id_ed25519 deploy-scripts/production.env root@165.227.76.219:/etc/codevault/.env
```

### 4️⃣ Deploy Application
```bash
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219
deploy-codevault
```

### 5️⃣ Configure Nginx
```bash
# From local:
scp -i ~/.ssh/id_ed25519 deploy-scripts/nginx-codevault.conf root@165.227.76.219:/etc/nginx/sites-available/codevault

# On server:
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219
ln -s /etc/nginx/sites-available/codevault /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

### 6️⃣ Get SSL Certificate
```bash
ssh -i ~/.ssh/id_ed25519 root@165.227.76.219
certbot --nginx -d api.codevault.parth7.me
```

---

## 🌐 DNS Configuration (Do This BEFORE SSL)

### Namecheap Setup:

1. Login: https://www.namecheap.com
2. Go to: **Domain List** → **parth7.me** → **Manage**
3. Click: **"Advanced DNS"** tab
4. **Add New Record:**
   - Type: `A Record`
   - Host: `api.codevault`
   - Value: `165.227.76.219`
   - TTL: `Automatic`
5. Save changes
6. Wait 5-30 minutes for propagation

**Verify DNS:**
```bash
nslookup api.codevault.parth7.me
# Should return: 165.227.76.219
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Backend health: `curl https://api.codevault.parth7.me/api/v1/health`
- [ ] Frontend loads: `https://codevault.parth7.me`
- [ ] Login works
- [ ] Can create projects
- [ ] Can generate licenses
- [ ] CORS errors resolved

---

## 🛠️ Useful Commands (After Deployment)

```bash
# Deploy updates
deploy-codevault

# View logs
codevault-logs

# Check status
codevault-status

# Restart container
docker restart codevault-backend

# Check SSL certificate
certbot certificates
```

---

## 🆘 Troubleshooting

### Problem: Can't SSH
**Solution:** Use Digital Ocean web console (see above)

### Problem: DNS not resolving
**Solution:** Wait up to 30 minutes, check Namecheap DNS settings

### Problem: SSL certificate fails
**Solution:** Ensure DNS is configured first, then re-run Certbot

### Problem: 502 Bad Gateway
**Solution:** Check container is running: `docker ps | grep codevault`

### Problem: CORS errors
**Solution:** Verify CORS_ORIGINS in `/etc/codevault/.env` includes both domains

---

## 📞 Need Help?

**Current Blocker:** SSH access to droplet

**Your Password (provided):** `Parth7052@`

**Your SSH Public Key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICSxx7HT31lAUYDz37YIbfMw1NIWpxev/G1vuB9RqUbU
```

**Next Step:** Fix SSH access using Digital Ocean web console, then run setup script.

---

*Ready to proceed once SSH access is restored!* 🚀

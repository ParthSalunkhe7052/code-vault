# CodeVault Deployment Guide

This guide covers deploying CodeVault to production using Vercel (frontend) and Digital Ocean (backend).

## Architecture Overview

- **Frontend**: React + Vite → Vercel
- **Backend**: FastAPI → Digital Ocean (App Platform or Droplet)
- **Database**: Neon PostgreSQL (cloud-hosted)
- **Storage**: Cloudflare R2
- **Email**: Resend
- **Cache**: Upstash Redis

---

## Prerequisites

Before deploying, ensure you have:

- [ ] Vercel account
- [ ] Digital Ocean account
- [ ] GitHub repository with your code
- [ ] Neon PostgreSQL database (get connection string)
- [ ] Cloudflare R2 bucket configured
- [ ] Upstash Redis instance
- [ ] Resend API key
- [ ] Stripe account (test or live keys)

---

## Part 1: Backend Deployment (Digital Ocean)

### Option A: App Platform (Recommended)

#### Step 1: Create App
1. Go to [Digital Ocean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"** → **"From GitHub"**
3. Authorize Digital Ocean to access your repository
4. Select your repository

#### Step 2: Configure Service
- **Source Directory**: `CodeVaultV1/server`
- **Dockerfile Path**: `CodeVaultV1/Dockerfile`
- **HTTP Port**: `8000`
- **Instance Size**: Start with **Basic ($12/mo)**
- **Health Check Path**: `/api/v1/health`

#### Step 3: Set Environment Variables

Add all of these in the Digital Ocean App Platform dashboard:

```bash
MODE=production
DATABASE_URL=postgresql://user:password@your-neon-host/database?sslmode=require
SECRET_KEY=<generate_with_openssl_rand_hex_32>
JWT_SECRET=<generate_with_openssl_rand_hex_32>
CORS_ORIGINS=https://your-frontend.vercel.app
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_bucket_name
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_REPO=yourusername/codevault
BUILD_CALLBACK_SECRET=<generate_with_openssl_rand_hex_32>
PUBLIC_API_URL=https://codevault-api-xxxxxx.ondigitalocean.app
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_upstash_token
RESEND_API_KEY=re_your_resend_api_key
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=CodeVault
EMAIL_ENABLED=true
EMAIL_PROVIDER=resend
ADMIN_EMAIL=your@email.com
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_PRICE_PRO=price_your_pro_price_id
STRIPE_PRICE_ENTERPRISE=price_your_enterprise_price_id
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

**Generate secrets:**
```bash
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For JWT_SECRET
openssl rand -hex 32  # For BUILD_CALLBACK_SECRET
```

#### Step 4: Deploy
1. Click **"Next"** → Review configuration
2. Click **"Create Resources"**
3. Wait for deployment (5-10 minutes)
4. Note your backend URL: `https://codevault-api-xxxxxx.ondigitalocean.app`

---

### Option B: Droplet (Manual Setup)

#### Step 1: Create Droplet
- OS: **Ubuntu 22.04 LTS**
- Plan: **Basic - 2GB RAM minimum**
- Add SSH keys for access

#### Step 2: Initial Server Setup
```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y
```

#### Step 3: Deploy Application
```bash
# Clone repository
git clone https://github.com/yourusername/codevault.git
cd codevault/CodeVaultV1

# Create .env file
nano .env
# Paste all environment variables from above

# Build and run
docker build -t codevault-backend .
docker run -d -p 8000:8000 --env-file .env --name codevault codevault-backend

# Check logs
docker logs -f codevault
```

#### Step 4: Setup Nginx + SSL
```bash
# Install Nginx and Certbot
apt install nginx certbot python3-certbot-nginx -y

# Configure Nginx reverse proxy
nano /etc/nginx/sites-available/codevault

# Add this configuration:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 500M;
    }
}

# Enable site
ln -s /etc/nginx/sites-available/codevault /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Get SSL certificate
certbot --nginx -d your-domain.com
```

---

## Part 2: Frontend Deployment (Vercel)

### Step 1: Prepare Frontend

Create production environment file:
```bash
cd CodeVaultV1/frontend
echo "VITE_API_URL=https://your-backend-url.ondigitalocean.app" > .env.production
```

### Step 2: Deploy to Vercel

#### Via Vercel Dashboard:
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. **Root Directory**: `CodeVaultV1/frontend`
4. **Framework Preset**: Vite
5. **Build Command**: `npm run build`
6. **Output Directory**: `dist`
7. **Environment Variables**:
   ```
   VITE_API_URL=https://your-backend-url.ondigitalocean.app
   ```
8. Click **Deploy**

#### Via Vercel CLI:
```bash
cd CodeVaultV1/frontend
npm install -g vercel
vercel login
vercel --prod
```

### Step 3: Configure Custom Domain (Optional)
1. In Vercel dashboard → **Settings** → **Domains**
2. Add your custom domain
3. Update DNS records as instructed

---

## Part 3: Configure External Services

### 3.1 Update CORS Origins

In your backend `.env` on Digital Ocean:
```bash
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-custom-domain.com
```

Redeploy backend after updating.

### 3.2 Stripe Webhooks

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click **"Add endpoint"**
3. **Endpoint URL**: `https://your-backend-url.ondigitalocean.app/api/v1/webhook/stripe`
4. **Events to send**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the **Signing Secret** (`whsec_...`)
6. Add to backend environment variables: `STRIPE_WEBHOOK_SECRET=whsec_...`

### 3.3 GitHub Actions Webhook

Your backend needs to be accessible by GitHub webhooks for cloud builds.

1. Ensure `PUBLIC_API_URL` in your backend env points to your backend URL
2. GitHub Actions will send build results to: `{PUBLIC_API_URL}/api/v1/cloud-build/callback`

---

## Part 4: Post-Deployment Verification

### Backend Health Check
```bash
curl https://your-backend-url.ondigitalocean.app/api/v1/health
```

Expected response:
```json
{"status": "healthy", "database": "connected"}
```

### Frontend Check
1. Visit your Vercel URL
2. Try logging in
3. Check browser console for API connection errors

### Test Full Flow
1. Create a test user account
2. Subscribe to a plan (use Stripe test mode)
3. Create a project
4. Generate a license
5. Trigger a build

---

## Troubleshooting

### CORS Errors
- Verify `CORS_ORIGINS` in backend includes your Vercel URL
- Ensure no trailing slashes in URLs

### Database Connection Failed
- Check `DATABASE_URL` is correct
- Ensure `?sslmode=require` is appended
- Verify Neon database allows connections

### Build Failures
- Check `GITHUB_TOKEN` has `repo` and `workflow` permissions
- Verify `GITHUB_REPO` format: `username/repo-name`
- Check GitHub Actions logs in your repository

### Stripe Webhook Not Working
- Verify webhook URL is correct
- Check `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
- Test webhook in Stripe dashboard using "Send test webhook"

---

## Monitoring & Maintenance

### Digital Ocean App Platform
- **Logs**: App Platform dashboard → **Runtime Logs**
- **Metrics**: CPU, Memory usage available in dashboard
- **Scaling**: Adjust instance size or enable autoscaling

### Vercel
- **Deployment Logs**: Vercel dashboard → **Deployments**
- **Analytics**: Available in Pro plan
- **Error Tracking**: Integrate with Sentry

### Database (Neon)
- Monitor connection count
- Set up connection pooling if needed
- Regularly check database size

---

## Cost Estimate (Monthly)

| Service | Plan | Cost |
|---------|------|------|
| Digital Ocean (Backend) | Basic 2GB | $12 |
| Vercel (Frontend) | Hobby | $0 |
| Neon PostgreSQL | Free tier | $0 (up to 0.5GB) |
| Cloudflare R2 | Pay as you go | ~$5 |
| Upstash Redis | Free tier | $0 |
| Resend | Free tier | $0 (up to 3k emails) |
| Stripe | Standard | 2.9% + $0.30/transaction |
| **Total (minimum)** | | **~$17/month** |

---

## Security Checklist

- [ ] All secrets generated with `openssl rand -hex 32`
- [ ] Production Stripe keys configured (not test keys)
- [ ] SSL/HTTPS enabled on all endpoints
- [ ] CORS origins restricted to your domains only
- [ ] Database connection uses SSL (`?sslmode=require`)
- [ ] Admin email set for admin role assignment
- [ ] `.env` files never committed to git
- [ ] Webhook secrets properly configured
- [ ] File upload limits set appropriately
- [ ] Rate limiting enabled (Redis configured)

---

## Rollback Procedure

### Vercel (Frontend)
1. Go to **Deployments**
2. Select previous working deployment
3. Click **"Promote to Production"**

### Digital Ocean (Backend)
1. Go to **Deployments** tab
2. Select previous working deployment
3. Click **"Rollback"**

### Manual Rollback (Droplet)
```bash
cd codevault/CodeVaultV1
git pull
git checkout <previous-commit-hash>
docker stop codevault
docker rm codevault
docker build -t codevault-backend .
docker run -d -p 8000:8000 --env-file .env --name codevault codevault-backend
```

---

## Support & Documentation

- **API Docs**: `https://your-backend-url/docs`
- **GitHub Issues**: [Repository Issues](https://github.com/yourusername/codevault/issues)
- **Stripe Docs**: [https://stripe.com/docs](https://stripe.com/docs)
- **Neon Docs**: [https://neon.tech/docs](https://neon.tech/docs)

---

**Last Updated**: January 2026

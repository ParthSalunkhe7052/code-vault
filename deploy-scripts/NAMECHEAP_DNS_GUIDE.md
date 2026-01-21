# 🌐 Namecheap DNS Configuration Guide for CodeVault

## Overview
This guide shows you **exactly** how to configure DNS in Namecheap to point `api.codevault.parth7.me` to your Digital Ocean droplet.

---

## 📋 Prerequisites
- ✅ Domain: `parth7.me` (purchased from Namecheap)
- ✅ Droplet IP: `165.227.76.219`
- ✅ Namecheap account access

---

## 🎯 Goal
Create subdomain: `api.codevault.parth7.me` → `165.227.76.219`

---

## 📝 Step-by-Step Instructions

### Step 1: Login to Namecheap

1. Go to: **https://www.namecheap.com/myaccount/login/**
2. Enter your credentials
3. Click **"Sign In"**

---

### Step 2: Access Domain Management

1. After login, you'll see the dashboard
2. Click on **"Domain List"** in the left sidebar
3. Find **"parth7.me"** in the list
4. Click the **"Manage"** button next to it

**What you'll see:**
- Domain details page with tabs: Domain, Products, Transfer, etc.

---

### Step 3: Open Advanced DNS Settings

1. Click on the **"Advanced DNS"** tab (top of the page)
2. You'll see current DNS records (if any)

**Current typical setup might show:**
- A Record: `@` → `some IP` (your main site)
- CNAME: `www` → `parth7.me`
- Maybe other records

---

### Step 4: Add A Record for API Subdomain

1. Click the **"Add New Record"** button
2. A new row will appear with dropdowns

**Fill in the fields:**

| Field | Value | Notes |
|-------|-------|-------|
| **Type** | Select: `A Record` | From dropdown |
| **Host** | `api.codevault` | **NOT** `api.codevault.parth7.me` |
| **Value** | `165.227.76.219` | Your droplet IP |
| **TTL** | `Automatic` | Or select `300` (5 minutes) |

**IMPORTANT:** 
- Host should be **`api.codevault`** (subdomain only)
- Do **NOT** include `.parth7.me` in the Host field
- Namecheap automatically appends your domain

**Visual Guide:**
```
┌─────────────┬─────────────────┬──────────────────┬──────────┐
│ Type ▼      │ Host            │ Value            │ TTL ▼    │
├─────────────┼─────────────────┼──────────────────┼──────────┤
│ A Record    │ api.codevault   │ 165.227.76.219   │ Automatic│
└─────────────┴─────────────────┴──────────────────┴──────────┘
```

---

### Step 5: Save Changes

1. Click the green **"Save All Changes"** button (top right or bottom right)
2. Wait for confirmation message: "All changes are successfully saved"
3. You should now see the new record in the list

---

### Step 6: Verify DNS Configuration

**In Namecheap Dashboard:**
- Your new A Record should appear in the list:
  ```
  A Record | api.codevault | 165.227.76.219 | 300 (or Automatic)
  ```

**From Your Computer (Terminal/CMD):**

Wait **5-30 minutes** for DNS propagation, then test:

```bash
# Windows (Command Prompt):
nslookup api.codevault.parth7.me

# Expected Output:
# Server:  [DNS Server Name]
# Address:  [DNS Server IP]
#
# Non-authoritative answer:
# Name:    api.codevault.parth7.me
# Address:  165.227.76.219
```

```bash
# Linux/Mac (Terminal):
dig api.codevault.parth7.me

# Expected Output (look for ANSWER SECTION):
# ;; ANSWER SECTION:
# api.codevault.parth7.me. 300 IN A 165.227.76.219
```

**Online Tools:**
- https://dnschecker.org/#A/api.codevault.parth7.me
- https://www.whatsmydns.net/#A/api.codevault.parth7.me

---

## 🕐 DNS Propagation Timeline

| Time | Status | Description |
|------|--------|-------------|
| 0-5 min | 🟡 Starting | Changes saved in Namecheap |
| 5-15 min | 🟡 Propagating | Some DNS servers updated |
| 15-30 min | 🟢 Complete | Most DNS servers updated |
| Up to 48h | 🟢 Worldwide | Full global propagation (rare) |

**Typical:** 10-20 minutes for most users

---

## ✅ Verification Checklist

Test these once DNS is propagated:

- [ ] `nslookup api.codevault.parth7.me` returns `165.227.76.219`
- [ ] `ping api.codevault.parth7.me` works (if firewall allows ICMP)
- [ ] `curl http://api.codevault.parth7.me` connects (after server setup)

---

## 🆘 Troubleshooting

### Problem: "Non-existent domain" error

**Cause:** DNS not propagated yet

**Solution:** 
- Wait 5-30 more minutes
- Check Namecheap → Advanced DNS → verify record is saved
- Try from different network (mobile hotspot)

---

### Problem: Wrong IP address returned

**Cause:** Old DNS cache

**Solution:**
```bash
# Windows - Flush DNS cache:
ipconfig /flushdns

# Linux - Flush DNS cache:
sudo systemd-resolve --flush-caches

# Mac - Flush DNS cache:
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

---

### Problem: Can't add record (grayed out)

**Cause:** Domain might use external nameservers

**Solution:**
1. In Namecheap → Domain → Nameservers section
2. Ensure it's set to **"Namecheap BasicDNS"** (not custom)
3. If using custom nameservers, you need to configure DNS there instead

---

### Problem: Record exists but still not working

**Checks:**
1. **Verify exact host name:** Should be `api.codevault` (no trailing dots)
2. **Verify IP format:** `165.227.76.219` (no spaces, no extra characters)
3. **Check TTL:** Set to `Automatic` or `300`
4. **Delete and re-add:** Sometimes helps refresh

---

## 📊 Common DNS Record Types (Reference)

| Type | Purpose | Example |
|------|---------|---------|
| **A** | Points domain to IPv4 address | `api.codevault` → `165.227.76.219` |
| **CNAME** | Alias to another domain | `www` → `parth7.me` |
| **MX** | Mail server | `@` → `mail.provider.com` |
| **TXT** | Text records (verification, SPF) | `@` → `v=spf1...` |

---

## 🎯 Additional Subdomains (Optional)

If you also want to point the main app subdomain:

**For Vercel Frontend:**
1. Add another A Record or CNAME:
   - **Type:** `CNAME Record`
   - **Host:** `codevault`
   - **Value:** `cname.vercel-dns.com` (check Vercel dashboard for exact value)
   - **TTL:** `Automatic`

2. Or use A Record if Vercel provides IP:
   - **Type:** `A Record`
   - **Host:** `codevault`
   - **Value:** `[Vercel IP from dashboard]`
   - **TTL:** `Automatic`

**Then in Vercel:**
- Go to Project Settings → Domains
- Add custom domain: `codevault.parth7.me`
- Follow Vercel's verification instructions

---

## 🔗 Quick Reference

**What you configured:**
```
Subdomain: api.codevault.parth7.me
Type:      A Record
Points to: 165.227.76.219
Purpose:   Backend API server (Digital Ocean droplet)
```

**Related domains:**
```
api.codevault.parth7.me   → Backend API (Digital Ocean)
codevault.parth7.me       → Frontend App (Vercel)
parth7.me                 → Your main site (existing)
```

---

## 📞 Need Help?

**If DNS isn't working after 30 minutes:**

1. **Double-check Namecheap settings:**
   - Login → Domain List → parth7.me → Manage
   - Advanced DNS tab
   - Verify the A Record is saved correctly

2. **Check nameservers:**
   - Domain tab → Nameservers section
   - Should say "Namecheap BasicDNS"

3. **Contact Namecheap support:**
   - Live chat: https://www.namecheap.com/support/live-chat/
   - Ticket: https://www.namecheap.com/support/

---

## ✨ Success!

Once `nslookup api.codevault.parth7.me` returns `165.227.76.219`, you're done!

**Next step:** Configure SSL certificate with Certbot (after backend is deployed)

---

*DNS Configuration Complete!* 🎉

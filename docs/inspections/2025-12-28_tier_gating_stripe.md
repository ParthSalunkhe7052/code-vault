# Inspection Report: Tier-Gating & Stripe Security
**Date:** 2025-12-28  
**Inspector:** Inspector Agent  
**Scope:** Obfuscation tier gating, Stripe integration, subscription bypass risks

---

## 🚨 Critical Issues (Must Fix Immediately)

- [ ] **[Security]** Obfuscation feature NOT gated by tier - Free users can use it
  - `TIER_LIMITS` in `config.py` has no `obfuscation` key
  - `get_compile_config()` returns obfuscate setting without tier check

---

## ⚠️ Warnings (Fix Before Release)

- [ ] **[Frontend]** Pricing.jsx Free limitations missing "No code obfuscation"
- [ ] **[Frontend]** Pricing.jsx Pro features missing "Code obfuscation"
- [ ] **[Config]** `PRICING_CONFIG.pro.features` needs "Code Obfuscation" added

---

## 💡 Suggestions (Nice to Have)

- [ ] Add rate limiting to `/stripe/create-checkout-session` (5/min)
- [ ] Add rate limiting to `/public/purchase` (10/min)

---

## ✅ Passed Checks (Stripe Security)

| Check | Status | Location |
|-------|--------|----------|
| Webhook signature verification | ✅ | `stripe_routes.py:L388-398` |
| No Stripe error leaks to client | ✅ | All catch blocks return 502 |
| Price ID allowlist validation | ✅ | `stripe_routes.py:L280-281` |
| Customer ID persistence (C4 fix) | ✅ | `stripe_routes.py:L180-204` |
| Subscription idempotency check | ✅ | `stripe_routes.py:L471-474` |
| JWT/API key auth on all routes | ✅ | All endpoints use `Depends()` |
| No hardcoded secrets | ✅ | All from env vars |
| `.env.example` exists | ✅ | Verified |
| Tier sync to users table | ✅ | `sync_user_tier()` called after all tier changes |

---

## Recommendation

**The Stripe integration is secure.** The only gap is the missing tier-gating for obfuscation.

See [Implementation Plan](file:///C:/Users/parth/.gemini/antigravity/brain/da5d8f3c-d68d-4e04-947d-81bf54dff23c/implementation_plan.md) for detailed fixes.

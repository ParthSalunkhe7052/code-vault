# CodeVault Security Checklist

## Pre-Deployment Security Verification

### Authentication & Authorization
- [x] JWT secrets are not using default values in production
- [x] Passwords are hashed with bcrypt (salt rounds >= 12)
- [x] Rate limiting is enabled for login/register endpoints
- [x] Session tokens expire after reasonable time (24 hours)
- [x] API keys are hashed before storage
- [x] Failed login attempts are logged and rate-limited

### Input Validation & Sanitization
- [x] All user inputs are validated using Pydantic models
- [x] SQL injection prevention via parameterized queries
- [x] XSS protection - no user input rendered as HTML
- [x] File upload restrictions (type, size)
- [x] Path traversal prevention in file operations
- [x] Command injection prevention in compiler calls

### Webhook Security
- [x] SSRF protection - private IPs blocked
- [x] Webhook signatures verified with HMAC
- [x] URL validation before delivery
- [x] Retry logic with exponential backoff
- [x] Maximum retry limits to prevent infinite loops
- [x] Webhook payload size limits

### Infrastructure Security
- [x] HTTPS enforced in production (HSTS headers)
- [x] CORS properly configured (no wildcard in production)
- [x] Security headers present (X-Content-Type-Options, X-Frame-Options)
- [x] Database connections use SSL/TLS
- [x] Redis connections use SSL (rediss://)
- [x] No sensitive data in logs
- [x] Error messages don't leak stack traces in production

### Data Protection
- [x] Database encrypted at rest (via provider)
- [x] Backups encrypted
- [x] API keys and secrets not in code repository
- [x] Environment variables for all secrets
- [x] Customer data isolated by user_id
- [x] GDPR compliance (data deletion capability)

### Rate Limiting & DDoS Protection
- [x] Global rate limiting configured
- [x] Endpoint-specific rate limits
- [x] Redis-based rate limiting (not in-memory)
- [x] Rate limit headers in responses
- [x] Different limits for different endpoints

### Monitoring & Alerting
- [x] Health check endpoint implemented
- [x] Failed request logging
- [x] Error tracking (Sentry or similar)
- [x] Database connection monitoring
- [x] Webhook failure alerts
- [x] Rate limit violation logging

## Testing Results

### Penetration Testing
```bash
# Run security tests
pytest tests/test_security_complete.py -v

# Check for SQL injection
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "'\'' OR '\''1'\''='\''1", "password": "test"}'
# Expected: 401 Unauthorized

# Check for XSS
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "<script>alert(1)</script>"}'
# Expected: Input sanitized or rejected
```

### Load Testing
```bash
# Install dependencies
pip install aiohttp

# Run load tests
python tests/load_test.py --url http://localhost:8000 --concurrency 100

# Expected results:
# - Health endpoint: < 100ms response time, 100% success
# - Login endpoint: Proper rate limiting (429 responses)
# - Database: No connection pool exhaustion
```

### Rate Limiting Verification
```bash
# Test login rate limiting
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"test@example.com\", \"password\": \"wrong\"}"
done
# Expected: First few succeed, then 429 Too Many Requests
```

## Deployment Security Checklist

### Environment Variables
Ensure all these are set in production:

```bash
# Required
DATABASE_URL=postgresql://... (must use SSL)
SECRET_KEY=<random-64-char-string>
JWT_SECRET=<different-random-64-char-string>
REDIS_URL=rediss://... (SSL required)
ENVIRONMENT=production

# Payment
POLAR_ACCESS_TOKEN=...
POLAR_WEBHOOK_SECRET=...

# Storage
CLOUDFLARE_R2_ENDPOINT=...
CLOUDFLARE_R2_ACCESS_KEY_ID=...
CLOUDFLARE_R2_SECRET_ACCESS_KEY=...

# Email
SMTP_HOST=...
SMTP_USER=...
SMTP_PASS=...

# Build System
GITHUB_TOKEN=...
BUILD_CALLBACK_SECRET=...
```

### Production Settings
- [ ] DEBUG mode disabled
- [ ] Logging level set to WARNING or ERROR
- [ ] Sentry/error tracking configured
- [ ] Database connection pooling optimized
- [ ] Redis connection pooling enabled
- [ ] Static files served via CDN
- [ ] SSL certificates valid and auto-renewing

### Post-Deployment Verification
- [ ] Health endpoint returns 200
- [ ] Rate limiting working
- [ ] Database connections stable
- [ ] Webhooks delivering successfully
- [ ] No errors in logs
- [ ] SSL certificate valid
- [ ] All security headers present

## Incident Response Plan

### Security Incident Detection
1. Monitor error logs for:
   - Unusual authentication failures
   - Rate limit violations
   - Database connection errors
   - Webhook delivery failures

2. Automated alerts for:
   - > 10 failed logins per minute
   - > 100 webhook failures per hour
   - Database connection pool exhausted
   - Error rate > 1%

### Response Procedures
1. **Suspected Breach**:
   - Immediately rotate JWT_SECRET
   - Force password resets for affected users
   - Review access logs
   - Notify affected customers within 24 hours

2. **DDoS Attack**:
   - Enable Cloudflare under attack mode
   - Scale up server instances
   - Enable stricter rate limiting
   - Contact hosting provider

3. **Data Leak**:
   - Identify scope of leak
   - Rotate all API keys
   - Audit database access logs
   - File GDPR breach report if required

## Security Contacts

- Security Issues: security@codevault.io
- Emergency: +1-XXX-XXX-XXXX
- On-call: Check PagerDuty

---

**Last Updated**: 2026-02-07
**Next Review**: 2026-03-07

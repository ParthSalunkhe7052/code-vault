# Security Rules

## Restricted Files

The following files contain sensitive data and MUST NOT be read, modified, or exposed:

### Environment & Secrets
- `.env`
- `.env.local`
- `.env.production`
- `.env.development`
- `.env.*.local`

### Credentials
- `credentials.json`
- `secrets.json`
- `secrets.yaml`
- `*_secrets.py`
- `*_credentials.py`

### Keys & Certificates
- `*.pem`
- `*.key`
- `*.p12`
- `*.pfx`
- `id_rsa*`
- `*.pub`

### Database
- `*.db`
- `*.sqlite`
- `*.sqlite3`

## Security Best Practices

### Never Commit
- API keys
- Database passwords
- JWT secrets
- OAuth tokens
- Private keys

### Code Patterns to Avoid
- Hardcoded secrets in source code
- SQL queries without parameterization
- Exposed endpoints without authentication
- Storing passwords in plain text

### Required Patterns
- Use environment variables for secrets
- Parameterized database queries
- Input validation on all endpoints
- Hardware ID (HWID) binding for license validation

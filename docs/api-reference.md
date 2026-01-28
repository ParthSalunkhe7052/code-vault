# API Reference

CodeVault provides a REST API for managing licenses, projects, and cloud builds.

**Base URL**: `https://api.codevault.com/api/v1`

## Authentication

All API requests (except license validation) require an API Key.

`X-API-Key: <your_api_key>`

## Licenses

### Validate a License (Public)
Used by the protected application to verify validity.

```http
POST /license/validate
```

**Payload:**
```json
{
  "license_key": "LIC-1234-5678",
  "hwid": "hardware-id-hash",
  "nonce": "random-string",
  "timestamp": 1705680000
}
```

### Create a License
```http
POST /licenses
```

## Cloud Build

### Start a Build
```http
POST /cloud-build/start
```

**Payload:**
```json
{
  "project_id": "proj_123",
  "platform": "windows",
  "fast_build": false
}
```

### Get Build Status
```http
GET /cloud-build/{build_id}/status
```

## Rate Limiting

- **Validation**: 100 req/min
- **Management**: 60 req/min

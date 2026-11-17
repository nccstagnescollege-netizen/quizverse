# QUIZVERSE API Conventions & Standards

## 1. Base URL & Versioning

All API endpoints reside under versioned paths:
```
http://localhost:8000/api/v1/*
```
Interactive OpenAPI documentation is automatically served at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 2. Standardized Response Format

Every endpoint returns structured JSON contracts validated via Pydantic v2:

### 2.1 Success Response (`200 OK`)
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "QUIZVERSE API",
    "version": "1.0.0",
    "environment": "development",
    "uptime_seconds": 124.5,
    "database_status": "connected",
    "features": {
      "auth": true,
      "storage": true,
      "realtime": true,
      "database_configured": true
    }
  },
  "meta": {
    "request_id": "c1a8e23b-6e9f-442b-923f-e5884bb0783a",
    "timestamp": "2026-11-17T12:00:00.000Z",
    "version": "v1"
  }
}
```

### 2.2 Validation Error Response (`422 Unprocessable Entity`)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      {
        "field": "body.email",
        "message": "value is not a valid email address",
        "type": "value_error"
      }
    ]
  },
  "meta": {
    "request_id": "c1a8e23b-6e9f-442b-923f-e5884bb0783a",
    "path": "/api/v1/auth/login"
  }
}
```

---

## 3. Mandatory Request Headers

- `x-request-id`: Client-supplied or server-generated UUID.
- `x-process-time-ms`: Server timing benchmark returned on all HTTP responses.

# JARVIS API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

All API endpoints require a valid JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

### Obtain Token

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Chat Endpoints

### Send Message

```http
POST /api/chat
Content-Type: application/json

{
  "message": "What's the weather today?",
  "context_id": "optional-context-id"
}
```

**Response:**
```json
{
  "response": "The weather today is sunny with a high of 75°F.",
  "context_id": "ctx_abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Stream Message (WebSocket)

```
ws://localhost:8000/ws/chat
```

Send JSON message, receive streamed responses.

## Notes Endpoints

### List Notes

```http
GET /api/notes?category=work&pinned=true&limit=20&offset=0
```

**Response:**
```json
{
  "notes": [
    {
      "id": "note_abc123",
      "title": "Meeting Notes",
      "content": "Discussed project timeline...",
      "tags": ["meeting", "project"],
      "category": "work",
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T09:30:00Z",
      "is_pinned": true
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

### Create Note

```http
POST /api/notes
Content-Type: application/json

{
  "title": "Meeting Notes",
  "content": "Discussed project timeline and milestones...",
  "tags": ["meeting", "project"],
  "category": "work"
}
```

**Response:** Returns created note object with ID.

### Get Note

```http
GET /api/notes/{note_id}
```

### Update Note

```http
PUT /api/notes/{note_id}
Content-Type: application/json

{
  "title": "Updated Meeting Notes",
  "content": "Updated content..."
}
```

### Delete Note

```http
DELETE /api/notes/{note_id}
```

### Search Notes

```http
POST /api/notes/search
Content-Type: application/json

{
  "query": "project timeline",
  "tags": ["meeting"],
  "category": "work",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### Export Note

```http
GET /api/notes/{note_id}/export?format=markdown
```

Supported formats: `json`, `markdown`, `txt`, `html`

### Import Note

```http
POST /api/notes/import
Content-Type: multipart/form-data

file: note.md
title: Optional Title
```

## Vision Endpoints

### Capture Webcam

```http
POST /api/vision/capture/webcam
```

**Response:** Returns base64-encoded image.

### Capture Screenshot

```http
POST /api/vision/capture/screenshot
```

### Analyze Image

```http
POST /api/vision/analyze
Content-Type: multipart/form-data

image: image.jpg
```

**Response:**
```json
{
  "description": "A person sitting at a desk with a computer...",
  "objects": ["person", "laptop", "desk"],
  "faces": 1,
  "confidence": 0.95
}
```

### OCR (Optical Character Recognition)

```http
POST /api/vision/ocr
Content-Type: multipart/form-data

image: document.jpg
```

**Response:**
```json
{
  "text": "Extracted text from the image..."
}
```

### Detect Objects

```http
POST /api/vision/detect
Content-Type: multipart/form-data

image: scene.jpg
```

### Compare Faces

```http
POST /api/vision/compare-faces
Content-Type: multipart/form-data

image1: face1.jpg
image2: face2.jpg
```

**Response:**
```json
{
  "similarity": 0.87,
  "match": true
}
```

## Plugin Endpoints

### List Plugins

```http
GET /api/plugins
```

**Response:**
```json
{
  "plugins": [
    {
      "name": "weather",
      "version": "1.0.0",
      "description": "Weather information plugin",
      "enabled": true,
      "capabilities": ["current_weather", "forecast", "alerts"]
    }
  ]
}
```

### Get Plugin Info

```http
GET /api/plugins/{plugin_name}
```

### Execute Plugin Action

```http
POST /api/plugins/{plugin_name}/execute
Content-Type: application/json

{
  "action": "current",
  "params": {
    "location": "New York"
  }
}
```

### Enable/Disable Plugin

```http
PUT /api/plugins/{plugin_name}/toggle
Content-Type: application/json

{
  "enabled": true
}
```

## System Endpoints

### Health Check

```http
GET /health
```

### System Status

```http
GET /api/status
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "memory_usage": "512MB",
  "active_connections": 5
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | Missing or invalid auth token |
| `FORBIDDEN` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Invalid request data |
| `RATE_LIMITED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

## Rate Limiting

- **Authenticated users**: 100 requests/minute
- **Chat endpoints**: 30 requests/minute
- **Vision endpoints**: 20 requests/minute

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

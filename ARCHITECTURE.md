# RingAI Integration - Architecture & Routes Flow

## 📁 Folder Structure

```
Cumma-voice-caller/
├── app/
│   ├── voice_main.py                    # FastAPI application entry point
│   │
│   ├── routers/                         # API endpoints (Controllers)
│   │   └── ringai/
│   │       ├── __init__.py              # Router exports
│   │       ├── calls.py                  # Call initiation endpoints
│   │       ├── webhooks.py               # Webhook endpoints for recordings
│   │       └── README.md                 # Documentation
│   │
│   ├── services/                         # Business logic layer
│   │   └── ringai/
│   │       ├── __init__.py
│   │       ├── call_service.py           # Call initiation logic
│   │       └── recording_service.py      # Recording storage & retrieval
│   │
│   ├── schemas/                         # Pydantic models (Request/Response validation)
│   │   └── ringai/
│   │       ├── __init__.py
│   │       ├── requests.py               # Request schemas (InitiateCallRequest, etc.)
│   │       ├── responses.py              # Response schemas (CallInitiatedResponse)
│   │       └── webhooks.py               # Webhook schemas (CallRecording, etc.)
│   │
│   ├── core/                            # Core infrastructure
│   │   ├── config/
│   │   │   └── settings.py               # Environment variables & config
│   │   ├── ringai/
│   │   │   ├── __init__.py
│   │   │   └── client.py                 # HTTP client for RingAI API
│   │   └── utils/
│   │       └── logger.py                 # Logging utilities
│   │
│   └── data/                            # Storage (created at runtime)
│       └── recordings/                  # Call recordings stored here
│           ├── {call_id}.json           # Individual recording files
│           └── user_index.json          # UserId -> [filenames] mapping
```

## 🔄 Request Flow Architecture

### Layer Separation (Clean Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                    HTTP Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  ROUTER LAYER (app/routers/ringai/)                     │
│  - HTTP concerns (status codes, error handling)         │
│  - Request validation via Pydantic                      │
│  - Response formatting                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  SERVICE LAYER (app/services/ringai/)                   │
│  - Business logic                                       │
│  - Data transformation                                  │
│  - Orchestration                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  CLIENT LAYER (app/core/ringai/client.py)               │
│  - HTTP communication with RingAI API                  │
│  - Error handling & retries                             │
│  - Authentication                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              RingAI External API                        │
└─────────────────────────────────────────────────────────┘
```

## 🛣️ Routes Flow

### 1. Call Initiation Flow

```
POST /api/v1/ringai/calls
│
├─► Router: app/routers/ringai/calls.py
│   └─► initiate_call()
│       ├─► Validates: InitiateCallRequest (from schemas/ringai/requests.py)
│       └─► Calls: RingAICallService.initiate_call()
│
├─► Service: app/services/ringai/call_service.py
│   └─► initiate_call()
│       ├─► Builds payload: request.to_ringai_payload()
│       └─► Calls: RingAIClient.initiate_call()
│
├─► Client: app/core/ringai/client.py
│   └─► initiate_call()
│       ├─► HTTP POST to RingAI API
│       └─► Returns: RingAI response
│
└─► Response: CallInitiatedResponse
    └─► { success: true, call_id: "...", status: "initiated" }
```

**Files Involved:**
- `app/routers/ringai/calls.py` - Endpoint handler
- `app/schemas/ringai/requests.py` - Request validation
- `app/schemas/ringai/responses.py` - Response model
- `app/services/ringai/call_service.py` - Business logic
- `app/core/ringai/client.py` - HTTP client

### 2. Webhook Flow (Call Completion)

```
POST /api/v1/ringai/webhooks/call-completed
│
├─► Router: app/routers/ringai/webhooks.py
│   └─► handle_call_completed()
│       ├─► Parses webhook payload
│       ├─► Validates: CallRecordingWebhook (from schemas/ringai/webhooks.py)
│       └─► Converts to: CallRecording
│
├─► Service: app/services/ringai/recording_service.py
│   └─► save_recording()
│       ├─► Saves to: ./data/recordings/{call_id}.json
│       └─► Updates: ./data/recordings/user_index.json (if userId provided)
│
└─► Response: { status: "success", call_id: "..." }
```

**Files Involved:**
- `app/routers/ringai/webhooks.py` - Webhook handler
- `app/schemas/ringai/webhooks.py` - Webhook schemas
- `app/services/ringai/recording_service.py` - Storage logic

### 3. Recording Retrieval Flow

```
GET /api/v1/ringai/webhooks/recordings/{call_id}
│
├─► Router: app/routers/ringai/webhooks.py
│   └─► get_recording()
│
├─► Service: app/services/ringai/recording_service.py
│   └─► get_recording()
│       ├─► Reads: ./data/recordings/{call_id}.json
│       └─► Generates CloudFront URL (if configured)
│
└─► Response: CallRecording
    └─► { call_id, transcription, recording_url (CloudFront), ... }
```

## 📊 Complete Request-Response Cycle

### Scenario: Making a Call and Retrieving Recording

```
1. INITIATE CALL
   Client → POST /api/v1/ringai/calls
   ↓
   Router (calls.py) → Service (call_service.py) → Client (client.py)
   ↓
   RingAI API → Call initiated
   ↓
   Response: { call_id: "abc123", status: "initiated" }

2. CALL HAPPENS (RingAI handles)
   RingAI → Makes phone call → Conversation happens

3. CALL COMPLETES
   RingAI → POST /api/v1/ringai/webhooks/call-completed
   ↓
   Router (webhooks.py) → Service (recording_service.py)
   ↓
   Saves: ./data/recordings/abc123.json
   Updates: ./data/recordings/user_index.json
   ↓
   Response: { status: "success" }

4. RETRIEVE RECORDING
   Client → GET /api/v1/ringai/webhooks/recordings/abc123
   ↓
   Router (webhooks.py) → Service (recording_service.py)
   ↓
   Reads: ./data/recordings/abc123.json
   Generates: CloudFront URL
   ↓
   Response: { call_id, transcription, recording_url: "https://cloudfront...", ... }
```

## 🔑 Key Components

### Routers (`app/routers/ringai/`)
- **Purpose**: HTTP endpoints, request/response handling
- **Responsibilities**:
  - Accept HTTP requests
  - Validate input via Pydantic schemas
  - Call service layer
  - Handle HTTP errors
  - Format responses

### Services (`app/services/ringai/`)
- **Purpose**: Business logic, orchestration
- **Responsibilities**:
  - Transform data
  - Coordinate between layers
  - Handle business rules
  - Manage storage

### Schemas (`app/schemas/ringai/`)
- **Purpose**: Data validation and type safety
- **Responsibilities**:
  - Validate request data
  - Structure response data
  - Type hints for IDE support
  - Auto-generate API docs

### Client (`app/core/ringai/client.py`)
- **Purpose**: External API communication
- **Responsibilities**:
  - HTTP requests to RingAI
  - Authentication
  - Error handling
  - Retry logic

## 📍 Available Endpoints

### Call Management
- `POST /api/v1/ringai/calls` - Initiate outbound call

### Webhooks
- `POST /api/v1/ringai/webhooks/call-completed` - Receive call completion events

### Recording Retrieval
- `GET /api/v1/ringai/webhooks/recordings/{call_id}` - Get recording by call ID
- `GET /api/v1/ringai/webhooks/recordings?phone_number=+91...` - Get by phone number
- `GET /api/v1/ringai/webhooks/recordings?limit=50` - List recent recordings

### Health Check
- `GET /health` - Service health check

## 🔐 Configuration

**Environment Variables** (in `app/core/config/settings.py`):
- `RING_API_KEY` - RingAI API key
- `RING_BASE_URL` - RingAI API base URL
- `CLOUDFRONT_BASE_URL` - CloudFront URL for recordings (optional)

## 💾 Storage

**Location**: `./data/recordings/`

**Files**:
- `{call_id}.json` - Individual call recording with transcription
- `user_index.json` - Maps userId → [recording filenames]

**Format**:
```json
{
  "call_id": "abc123",
  "user_id": "user456",
  "phone_number": "+918778898282",
  "transcription": "Full conversation text...",
  "recording_filename": "abc123.json",
  "recording_url": "https://cloudfront.net/recordings/abc123.json",
  "created_at": "2025-01-20T10:00:00",
  "completed_at": "2025-01-20T10:05:00"
}
```

## 🎯 Design Principles

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Type Safety**: Pydantic schemas ensure data validation
3. **Error Handling**: Graceful failures at each layer
4. **Scalability**: Easy to add database, caching, etc.
5. **Testability**: Each layer can be tested independently


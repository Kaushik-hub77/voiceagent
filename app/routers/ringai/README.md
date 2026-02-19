# RingAI Integration Endpoints

## Call Initiation

**POST** `/api/v1/ringai/calls`

Initiate an outbound call via RingAI.

## Webhooks (Call Recordings)

### Setup

1. **Configure Webhook URL in RingAI Dashboard:**
   - Go to RingAI dashboard → Webhooks/Settings
   - Set webhook URL to: `https://your-domain.com/api/v1/ringai/webhooks/call-completed`
   - For local testing, use ngrok: `ngrok http 8001`
   - Then set webhook to: `https://your-ngrok-url.ngrok.io/api/v1/ringai/webhooks/call-completed`

2. **Storage:**
   - Recordings are stored in `./data/recordings/` directory
   - Each call is saved as `{call_id}.json`
   - Contains transcription, recording URL, metadata

### Endpoints

**POST** `/api/v1/ringai/webhooks/call-completed`
- Receives webhook from RingAI when call completes
- Automatically saves transcription and recording data

**GET** `/api/v1/ringai/webhooks/recordings/{call_id}`
- Retrieve recording by call ID

**GET** `/api/v1/ringai/webhooks/recordings?phone_number=+918778898282`
- List all recordings for a phone number

**GET** `/api/v1/ringai/webhooks/recordings?limit=50`
- List recent recordings (default: 100)

## Example Webhook Payload

RingAI will POST to your webhook with:
```json
{
  "call_id": "ringai-call-12345",
  "status": "completed",
  "phone_number": "+918778898282",
  "transcription": "Full conversation text here...",
  "recording_url": "https://ringai.com/recordings/12345.mp3",
  "duration": 120
}
```

## Storage Location

Recordings are stored in: `./data/recordings/{call_id}.json`

Each file contains:
- Call ID
- Phone numbers
- Full transcription text
- Recording URL
- Call duration
- Timestamps
- Metadata


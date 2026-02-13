## 📥 Download / Clone

# From your development directory
git clone <your-repo-url> Cumma-voice-caller
cd Cumma-voice-caller> Always run commands from the project root: `Cumma-voice-caller`.

## 🧱 Environment Setup (Windows, PowerShell)
hell
# 1. Create and activate virtualenv (Python 3.11)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install the project and dependencies from pyproject.toml
python -m pip install --upgrade pip
pip install -e .This installs `fastapi`, `uvicorn`, `twilio`, and registers `app` as a package so imports like `app.routers.voice_bot` and `app.agent_builder.*` work.

## 🔑 Required Environment Variables

Set these before running the voice service:
hell
# Twilio credentials
$env:TWILIO_ACCOUNT_SID      = "<your-twilio-account-sid>"
$env:TWILIO_AUTH_TOKEN       = "<your-twilio-auth-token>"
$env:TWILIO_FROM_PHONE_NUMBER = "+15551234567"   # E.164 format

# Voice bot webhook + media stream host
$env:TWILIO_VOICE_WEBHOOK_URL = "https://your-domain.com/voice-bot/incoming-call"
$env:TWILIO_MEDIA_STREAM_HOST = "your-domain.com"  # host used in wss://<host>/voice-bot/media-streamFor local testing you can point these at an HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.).

## 🚀 Running the Voice Bot Service

From the project root, with `.venv` activated:
hell
# Development run (auto‑reload disabled or enabled as needed)
python -m uvicorn app.voice_main:app --host 0.0.0.0 --port 8001 --reload- Health check: `GET http://localhost:8001/health` → `{"status": "ok"}`
- Twilio Voice webhook: `POST https://<your-domain>/voice-bot/incoming-call`
- Twilio Media Stream WebSocket: `wss://<TWILIO_MEDIA_STREAM_HOST>/voice-bot/media-stream`

## 🧪 Quick Verification Checklist

1. Virtualenv is active: PowerShell prompt shows `(.venv)` prefix.
2. `pip show fastapi uvicorn twilio` all succeed.
3. `python -m uvicorn app.voice_main:app --host 0.0.0.0 --port 8001` starts without import errors.
4. `curl http://localhost:8001/health` returns `{"status":"ok"}`.
5. Twilio Console points the number’s Voice URL to `/voice-bot/incoming-call`.
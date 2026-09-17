# Cumma Voice Caller

A fast, scalable voice caller application built with FastAPI and RingAI.

## 🧱 Environment Setup

### 1. Prerequisites
- **Python 3.11** or **3.12** is highly recommended (Python 3.14+ may fail to build certain dependencies).
- Virtual environment (venv).

### 2. Local Setup (Windows, PowerShell)
```powershell
# Create and activate virtualenv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install the project and dependencies
python -m pip install --upgrade pip
pip install -e .
```

### 3. Required Environment Variables
Create a `.env` file in the root directory (or set these in your terminal) before running the voice service:
```bash
RING_API_KEY="your-ring-api-key"
RING_BASE_URL="https://api.ring.ai"
# Add other keys required by settings.py
```

## 🚀 Running the Service

### Run Locally (with Uvicorn)
From the project root, with `.venv` activated:
```powershell
python -m uvicorn app.voice_main:app --host 0.0.0.0 --port 8000 --reload
```

### Run with Docker (Recommended for Production)
```powershell
docker-compose up --build -d
```

## 🧪 Quick Verification Checklist
1. Application starts successfully without errors.
2. `curl http://localhost:8000/health` returns `{"status":"ok"}`.
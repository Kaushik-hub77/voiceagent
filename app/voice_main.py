"""
Minimal FastAPI application exposing only the voice-bot endpoints.

Run with:
    uvicorn app.voice_main:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI

from app.routers.ringai import calls_router, webhooks_router


app = FastAPI(
    title="Voice Bot Service",
    description="AI voice bot service using RingAI",
)

app.include_router(calls_router)
app.include_router(webhooks_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.voice_main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )



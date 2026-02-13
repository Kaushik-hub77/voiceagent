import json
import logging
import os
from typing import AsyncIterator

from fastapi import APIRouter, Request, WebSocket
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

from app.agent_builder.builders import VoiceAgentBuilder


logger = logging.getLogger(__name__)
router = APIRouter()


class StartVoiceBotCallRequest(BaseModel):
    toPhoneNumber: str  # E.164 format, e.g. "+14155550123"


def _get_twilio_client() -> Client:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    return Client(account_sid, auth_token)


def _create_outbound_call_sync(to_phone: str) -> str:
    client = _get_twilio_client()
    from_phone = os.environ["TWILIO_FROM_PHONE_NUMBER"]
    voice_webhook_url = os.environ["TWILIO_VOICE_WEBHOOK_URL"]

    call = client.calls.create(
        to=to_phone,
        from_=from_phone,
        url=voice_webhook_url,
    )
    return call.sid


@router.post("/api/v1/voice-bot/calls")
async def start_voice_bot_call(payload: StartVoiceBotCallRequest) -> dict:
    """
    Start an outbound Twilio call to the given phone number and
    connect it to the AI voice agent via media stream.
    """
    call_sid = await run_in_threadpool(_create_outbound_call_sync, payload.toPhoneNumber)
    return {"callSid": call_sid, "status": "initiated"}


@router.api_route("/voice-bot/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request) -> HTMLResponse:
    """
    Twilio webhook for inbound or outbound-initiated calls.
    Returns TwiML that connects the call to the media-stream WebSocket.
    """
    response = VoiceResponse()

    media_stream_host = os.environ.get("TWILIO_MEDIA_STREAM_HOST", request.url.hostname)
    connect = Connect()
    connect.stream(url=f"wss://{media_stream_host}/voice-bot/media-stream")
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")


@router.websocket("/voice-bot/media-stream")
async def handle_media_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint to process audio streams from Twilio and send responses.
    Based on the provided samplecode.md logic.
    """
    await websocket.accept()
    stream_sid = None

    async def input_audio_stream() -> AsyncIterator[str]:
        nonlocal stream_sid

        # Initial configuration event for the voice agent
        yield json.dumps(
            {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "voice": "alloy",
                    "output_audio_format": "g711_ulaw",
                },
            }
        )

        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message from Twilio", message=message)
                    continue

                event = data.get("event")

                if event == "start":
                    stream_sid = data.get("start", {}).get("streamSid")
                    logger.info("Stream started", streamSid=stream_sid)
                elif event == "media":
                    media = data.get("media") or {}
                    payload = media.get("payload")
                    if payload:
                        yield json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": payload,
                            }
                        )
                elif event == "stop":
                    logger.info("Stream stopped", streamSid=stream_sid)
                    break
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", streamSid=stream_sid)

    async def handle_output_event(event_str: str) -> None:
        """
        Process responses from the voice agent and send audio back to Twilio.
        """
        try:
            event = json.loads(event_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse output event JSON", raw=event_str)
            return

        if event.get("type") == "response.audio.delta" and "delta" in event:
            if stream_sid:
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": event["delta"]},
                        }
                    )
                )

    voice_agent = (
        VoiceAgentBuilder()
        .set_voice("alloy")
        .set_input_audio_format("g711_ulaw")
        .build()
    )

    await voice_agent.ainvoke(input_audio_stream(), handle_output_event)



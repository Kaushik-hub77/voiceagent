from __future__ import annotations

from typing import AsyncIterator

import asyncio
import logging

from app.core.voice.base import VoiceProvider
from app.core.voice.sarvam_client import SarvamVoiceClient
from app.core.config.settings import settings


logger = logging.getLogger(__name__)


class SarvamVoiceProvider(VoiceProvider):
    """
    VoiceProvider implementation backed by Sarvam TTS.

    This provider is responsible only for turning text into audio chunks.
    It does not know about Twilio or WebSocket details.
    """

    def __init__(self, client: SarvamVoiceClient | None = None) -> None:
        if client is None:
            client = SarvamVoiceClient(
                api_key=settings.SARVAM_API_KEY,
                default_target_language_code=settings.SARVAM_TARGET_LANGUAGE_CODE,
                default_model=settings.SARVAM_TTS_MODEL,
                default_speaker=settings.SARVAM_SPEAKER
            )
        self._client = client

    async def speak(self, text: str, *, session_id: str) -> AsyncIterator[str]:
        """
        Yield base64-encoded audio suitable for Twilio media payloads.

        For now we call Sarvam once per utterance and yield the full audio
        as a single chunk. This keeps behavior deterministic and simple; we
        can later introduce slicing if we need finer-grained streaming.
        """
        logger.info("SarvamVoiceProvider.speak", extra={"session_id": session_id})

        # Sarvam client is sync under the hood; offload to threadpool to avoid
        # blocking the event loop.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._client.synthesize(text),
        )

        # NOTE: Twilio expects base64 G.711 u-law. If Sarvam does not return
        # that format directly, we will need an explicit transcoding step.
        # For now we just forward the base64 audio as-is.
        yield result.audio_base64



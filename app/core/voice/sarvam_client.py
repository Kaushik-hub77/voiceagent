from __future__ import annotations

from typing import Any, Dict, Optional

import base64
import logging
import os

from sarvamai import SarvamAI

logger = logging.getLogger(__name__)


class SarvamVoiceResult:
    """
    Simple container for Sarvam TTS results.
    """

    def __init__(self, audio_base64: str, audio_format: str, text_used: str) -> None:
        self.audio_base64 = audio_base64
        self.audio_format = audio_format
        self.text_used = text_used


class SarvamVoiceClient:
    """
    Thin wrapper around the SarvamAI SDK for TTS.

    This client is environment-agnostic: it only knows about API keys and
    Sarvam parameters, not HTTP/WebSocket or Twilio details.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_target_language_code: str = "en-IN",
        default_model: str = "bulbul:v3",
        default_speaker: str = "shubh",
    ) -> None:
        api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY is not configured")

        self._client = SarvamAI(api_subscription_key=api_key)
        self._default_target_language_code = default_target_language_code
        self._default_model = default_model
        self._default_speaker = default_speaker

    def synthesize(
        self,
        text: str,
        *,
        target_language_code: Optional[str] = None,
        model: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> SarvamVoiceResult:
        """
        Convert text to speech using Sarvam TTS (synchronous).

        Callers MUST offload this to a threadpool or background worker
        if they are running in an async context.
        """
        target_lang = target_language_code or self._default_target_language_code
        model_name = model or self._default_model
        speaker_name = speaker or self._default_speaker

        logger.info(
            "Calling Sarvam TTS",
            extra={
                "target_language_code": target_lang,
                "model": model_name,
                "speaker": speaker_name,
            },
        )

        try:
            response: Dict[str, Any] = self._client.text_to_speech.convert(
                target_language_code=target_lang,
                text=text,
                model=model_name,
                speaker=speaker_name,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Sarvam TTS call failed", exc_info=exc)
            raise

        # The exact shape depends on Sarvam's SDK; we expect an audio payload and format.
        audio_base64: str = response.get("audio") or response.get("audio_base64")  # type: ignore[assignment]
        audio_format: str = response.get("format") or "wav"

        if not audio_base64:
            logger.error("Sarvam TTS response missing audio payload", extra={"response": response})
            raise ValueError("Sarvam TTS response missing audio payload")

        return SarvamVoiceResult(
            audio_base64=audio_base64,
            audio_format=audio_format,
            text_used=text,
        )



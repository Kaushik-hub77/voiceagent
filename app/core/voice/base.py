from __future__ import annotations

from typing import AsyncIterator, Protocol


class VoiceProvider(Protocol):
    """
    Abstraction for any TTS/voice backend.

    This is intentionally LLM-agnostic and transport-agnostic. It just
    converts text into an async stream of audio chunks (base64 strings or bytes).
    """

    async def speak(self, text: str, *, session_id: str) -> AsyncIterator[str]:  # pragma: no cover - protocol
        """
        Convert text to an async stream of audio chunks suitable for sending
        back to Twilio as media payloads.
        """
        ...



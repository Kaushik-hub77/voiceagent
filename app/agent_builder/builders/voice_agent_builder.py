from __future__ import annotations

from typing import Awaitable, Callable, AsyncIterator, Optional, Protocol


class OutputHandler(Protocol):
    async def __call__(self, event_str: str) -> None:  # pragma: no cover - protocol
        ...


class VoiceAgent:
    """
    Minimal async voice agent interface that streams between Twilio and the model.

    For now, this is a very thin wrapper that just forwards events; you can plug
    in real model / streaming logic here without changing the routers.
    """

    def __init__(self, voice: str, input_audio_format: str) -> None:
        self._voice = voice
        self._input_audio_format = input_audio_format

    async def ainvoke(
        self,
        input_events: AsyncIterator[str],
        handle_output_event: OutputHandler,
    ) -> None:
        """
        Consume events from Twilio and hand them off to the model / output handler.

        This placeholder implementation simply iterates the input stream without
        doing any LLM work yet.
        """
        async for _ in input_events:
            # In a real implementation, you would:
            # 1. Send audio chunks to your LLM / voice model.
            # 2. Stream partial responses via handle_output_event.
            # For now, we no-op so the router can run end‑to‑end.
            continue


class VoiceAgentBuilder:
    """
    Deterministic, side‑effect‑free builder for VoiceAgent instances.
    """

    def __init__(self) -> None:
        self._voice: Optional[str] = None
        self._input_audio_format: Optional[str] = None

    def set_voice(self, voice: str) -> "VoiceAgentBuilder":
        self._voice = voice
        return self

    def set_input_audio_format(self, audio_format: str) -> "VoiceAgentBuilder":
        self._input_audio_format = audio_format
        return self

    def build(self) -> VoiceAgent:
        if self._voice is None:
            raise ValueError("Voice must be set before building VoiceAgent")
        if self._input_audio_format is None:
            raise ValueError("Input audio format must be set before building VoiceAgent")

        return VoiceAgent(
            voice=self._voice,
            input_audio_format=self._input_audio_format,
        )



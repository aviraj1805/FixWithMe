"""Fixy's voice: Gemini text-to-speech with a warm female voice. Returns WAV audio.

Only the words to say are sent: a style instruction in the text gets read out loud.

The browser falls back to its own speech synthesis whenever this fails (quota, outage)."""

import asyncio
import logging
from collections import OrderedDict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .knowledge import Lang

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


class SpeakRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=600)]
    lang: Lang = "en"


class Speaker:
    def __init__(
        self, api_key: str, models: list[str], voice: str, timeout_s: float = 20.0
    ) -> None:
        from google import genai
        from google.genai import types

        self.models, self.voice, self.timeout_s = models, voice, timeout_s
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000))
        )
        self._cache: OrderedDict[tuple[str, str], tuple[bytes, str]] = OrderedDict()

    async def speak(self, text: str, lang: Lang) -> tuple[bytes, str] | None:
        key = (text, lang)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        from google.genai import types

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
                )
            ),
        )
        for model in self.models:
            try:
                resp = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=model, contents=text, config=config
                    ),
                    timeout=self.timeout_s + 5,
                )
                part = resp.candidates[0].content.parts[0].inline_data
                audio = (part.data, part.mime_type or "audio/wav")
            except Exception as exc:
                log.warning("tts failed on %s: %s", model, exc)
                continue
            if not audio[1].startswith("audio/wav"):
                audio = (_pcm_to_wav(audio[0], _rate(audio[1])), "audio/wav")
            self._cache[key] = audio
            if len(self._cache) > 200:
                self._cache.popitem(last=False)
            return audio
        return None


def _rate(mime: str) -> int:
    for part in mime.replace(",", ";").split(";"):
        if part.strip().startswith("rate="):
            return int(part.split("=")[1])
    return 24000


def _pcm_to_wav(pcm: bytes, rate: int) -> bytes:
    """16-bit mono little-endian PCM → WAV container."""
    import struct

    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return header + b"data" + struct.pack("<I", len(pcm)) + pcm


@router.post("/speak")
async def speak(req: SpeakRequest, request: Request) -> Response:
    speaker: Speaker | None = request.app.state.speaker
    audio = await speaker.speak(req.text, req.lang) if speaker else None
    if audio is None:
        raise HTTPException(status_code=503, detail="Voice unavailable; use the browser voice")
    return Response(content=audio[0], media_type=audio[1], headers={"Cache-Control": "no-store"})

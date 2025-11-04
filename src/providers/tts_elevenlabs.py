from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class ElevenTTS:
    def __init__(self, api_key: str | None = None, voice_id: str | None = None, model_id: str | None = None, mock: bool = False):
        self.mock = mock or os.getenv("MOCK_ELEVENLABS", "false").lower() in {"1", "true", "yes"}
        if self.mock:
            logger.info("ElevenLabs MOCK mode enabled - skipping API calls")
            self.api_key = None
            self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "mock-voice")
            self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
            self.client = None
        else:
            self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
            self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
            self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
            if not self.api_key:
                raise RuntimeError("Missing ELEVENLABS_API_KEY")
            if not self.voice_id:
                raise RuntimeError("Missing ELEVENLABS_VOICE_ID")
            from elevenlabs import ElevenLabs
            self.client = ElevenLabs(api_key=self.api_key)

    def synth(self, text: str, out_path: Path) -> Path:
        # Preprocess text to speed up speech: replace slashes and other pauses with commas
        text_fast = text.replace("/", " and ")
        text_fast = text_fast.replace(" — ", ", ")
        text_fast = text_fast.replace(" → ", ", ")
        
        if self.mock:
            # Mock mode: just create an empty file and log
            logger.info("MOCK: Would synthesize %d chars to %s (text preview: %s...)", len(text_fast), out_path, text_fast[:100])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a small dummy file so the pipeline doesn't break
            with open(out_path, "w") as f:
                f.write("# MOCK AUDIO FILE - ElevenLabs API not called\n")
                f.write(f"Text length: {len(text_fast)} chars\n")
                f.write(f"Preview: {text_fast[:200]}...\n")
            return out_path
        
        audio_stream = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            optimize_streaming_latency="0",
            output_format="mp3_44100_128",
            text=text_fast,
            voice_settings={
                "stability": 0.4,  # Lower stability = faster, more dynamic pace
                "similarity_boost": 0.75,
            },
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
        return out_path



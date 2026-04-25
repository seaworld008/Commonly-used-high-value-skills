# API Integration Reference

Provider integration patterns for game audio generation APIs. Covers sound effects (SFX), background music (BGM), voice/TTS, ambient soundscapes, and procedural audio workflows.

## Provider Comparison

| Provider | Strength | Category | Input | Pricing Model | Output Format | Generation Time |
|----------|----------|----------|-------|---------------|---------------|-----------------|
| **ElevenLabs SFX** | High-quality sound effects from text | SFX | Text prompt | Per-generation (~$0.08) | MP3 | 2-10s |
| **ElevenLabs TTS** | Natural multilingual voices | Voice | Text + voice ID | Per-character (~$0.30/1K chars) | MP3 | 1-5s |
| **Stable Audio 2.5** | Music and SFX, long-form | BGM/SFX | Text prompt | Per-generation (~$0.03-0.10) | WAV | 10-60s |
| **MusicGen** | Music generation, continuation | BGM/Ambient | Text prompt | Per-generation (~$0.02-0.08) | WAV | 10-90s |
| **OpenAI TTS** | Reliable, consistent voices | Voice | Text | Per-character (~$15/1M chars) | MP3/WAV/FLAC/Opus | 1-3s |
| **Google Cloud TTS** | Wide language/voice selection | Voice | Text/SSML | Per-character (~$4-16/1M chars) | MP3/WAV/OGG | 1-3s |
| **Bark** | Expressive speech + non-speech sounds | Voice/Ambient | Text + tags | Per-generation (~$0.02-0.05) | WAV | 5-30s |
| **JSFXR** | Retro/chiptune procedural SFX | SFX/UI/Retro | Parameters | Free (local) | WAV | <1ms |
| **Suno AI** | Full song / instrumental BGM with structure control | BGM | Style prompt + metatags | Credit-based (~$0.10-0.30) | MP3/WAV | 30-120s |
| **Freesound** | Massive CC-licensed sound library | All (search) | Search query | Free (rate limited) | WAV/MP3/OGG/FLAC | N/A (download) |

### Provider Capability Matrix

| Capability | ElevenLabs SFX | ElevenLabs TTS | Stable Audio | MusicGen | Suno AI | OpenAI TTS | Google TTS | Bark | JSFXR | Freesound |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Sound Effects | Yes | No | Yes | No | No | No | No | Limited | Yes | Yes |
| Background Music | No | No | Yes | Yes | Yes | No | No | No | No | Yes |
| Voice/Speech | No | Yes | No | No | No | Yes | Yes | Yes | No | Yes |
| Ambient/Atmosphere | No | No | Yes | Yes | Limited | No | No | Yes | No | Yes |
| UI Sounds | Yes | No | No | No | No | No | No | No | Yes | Yes |
| Non-speech vocals | No | No | No | No | Yes | No | No | Yes | No | Yes |
| Multilingual | N/A | Yes | N/A | N/A | N/A | Yes | Yes | Yes | N/A | N/A |
| SSML Support | N/A | No | N/A | N/A | No | No | Yes | No | N/A | N/A |
| Duration Control | Yes | N/A | Yes | Yes | Limited | N/A | N/A | No | No | N/A |
| Streaming | No | Yes | No | No | No | Yes | Yes | No | N/A | N/A |
| Seed Control | No | No | Yes | Yes | No | No | No | No | Yes | N/A |
| Continuation | No | No | No | Yes | Yes | No | No | No | No | N/A |
| Local/Offline | No | No | No | No | No | No | No | No | Yes | No |
| Structure Control | No | No | No | No | Yes | No | No | No | No | N/A |
| Stem Separation | No | No | No | No | Yes | No | No | No | No | N/A |

## Authentication Pattern

All cloud providers use API key authentication via environment variables.

```python
import os
import httpx

# Standard auth pattern - NEVER hardcode keys
API_KEY = os.environ["ELEVENLABS_API_KEY"]  # or REPLICATE_API_TOKEN, etc.

headers = {
    "xi-api-key": API_KEY,  # ElevenLabs style
    # or "Authorization": f"Bearer {API_KEY}",  # OpenAI/Replicate/Google style
    "Content-Type": "application/json",
}
```

Environment variable naming convention:

| Provider | Environment Variable |
|----------|---------------------|
| ElevenLabs (SFX + TTS) | `ELEVENLABS_API_KEY` |
| Suno AI (via suno-api) | `SUNO_COOKIE` + `SUNO_BASE_URL` |
| Stable Audio (via Replicate) | `REPLICATE_API_TOKEN` |
| MusicGen (via Replicate) | `REPLICATE_API_TOKEN` |
| Bark (via Replicate) | `REPLICATE_API_TOKEN` |
| OpenAI TTS | `OPENAI_API_KEY` |
| Google Cloud TTS | `GOOGLE_APPLICATION_CREDENTIALS` (service account JSON path) |
| Freesound | `FREESOUND_API_KEY` |
| JSFXR | N/A (local library) |

## Provider Abstraction Layer

Abstract the provider interface for swappability and testability:

```python
import os
import time
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AudioGenerationConfig:
    """Unified configuration for audio generation across providers."""
    prompt: str = ""
    category: str = "sfx"  # "sfx" | "bgm" | "voice" | "ambient" | "ui"
    duration_seconds: float = 5.0
    output_format: str = "wav"  # "wav" | "mp3" | "ogg" | "flac"
    sample_rate: int = 44100
    quality: str = "standard"  # "preview" | "standard" | "high"
    seed: Optional[int] = None
    # Voice-specific
    voice_id: str = ""
    language: str = "en"
    # Music-specific
    tempo_bpm: Optional[int] = None
    key: str = ""  # e.g. "C major", "A minor"
    genre: str = ""


@dataclass
class AudioGenerationResult:
    """Unified result from any audio provider."""
    task_id: str
    provider: str
    status: str  # "pending" | "processing" | "succeeded" | "failed"
    audio_url: str = ""
    audio_bytes: bytes = b""
    duration_seconds: float = 0.0
    format: str = ""
    sample_rate: int = 0
    metadata: dict = field(default_factory=dict)


class AudioProvider(ABC):
    """Abstract base for audio generation providers."""

    @abstractmethod
    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate audio from config. Returns result (may require polling)."""

    @abstractmethod
    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        """Estimate cost in USD for the given config."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier string."""

    @property
    @abstractmethod
    def supported_categories(self) -> list[str]:
        """List of supported audio categories."""

    def save_audio(self, result: AudioGenerationResult, output_path: str) -> Path:
        """Save audio result to file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if result.audio_bytes:
            path.write_bytes(result.audio_bytes)
        elif result.audio_url:
            resp = httpx.get(result.audio_url, timeout=120.0, follow_redirects=True)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        else:
            raise ValueError("No audio data or URL in result")
        return path
```

## Provider Implementations

---

### ElevenLabs Sound Effects

```python
class ElevenLabsSFXProvider(AudioProvider):
    """ElevenLabs Sound Effects API integration.

    Generates sound effects from text descriptions.
    Auth: xi-api-key header via ELEVENLABS_API_KEY env var.
    Docs: https://elevenlabs.io/docs/api-reference/sound-generation
    Cost: ~$0.08 per generation (check current pricing).
    License: Safe (licensed training data).
    """

    provider_name = "elevenlabs_sfx"
    supported_categories = ["sfx", "ui", "ambient"]

    def __init__(self):
        self.api_key = os.environ["ELEVENLABS_API_KEY"]
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate a sound effect from a text prompt.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Description of the sound (e.g. "sword clash on metal shield")
                - duration_seconds: 0.5 to 22 seconds
        """
        payload = {
            "text": config.prompt,
            "duration_seconds": max(0.5, min(config.duration_seconds, 22.0)),
            "prompt_influence": 0.3,  # 0.0-1.0, higher = closer to prompt
        }

        resp = httpx.post(
            f"{self.base_url}/sound-generation",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()

        return AudioGenerationResult(
            task_id=f"el_sfx_{int(time.time())}",
            provider=self.provider_name,
            status="succeeded",
            audio_bytes=resp.content,
            duration_seconds=config.duration_seconds,
            format="mp3",
            sample_rate=44100,
        )

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        return 0.08  # Flat rate per generation


# --- Usage Example ---

def generate_sfx_elevenlabs(prompt: str, duration: float = 5.0,
                            output_path: str = "output.mp3") -> Path:
    """Generate a sound effect using ElevenLabs.

    Example:
        generate_sfx_elevenlabs(
            prompt="heavy wooden door creaking open slowly in a stone castle",
            duration=3.0,
            output_path="door_creak.mp3",
        )
    """
    provider = ElevenLabsSFXProvider()
    config = AudioGenerationConfig(
        prompt=prompt,
        category="sfx",
        duration_seconds=duration,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**Rate Limits:**
- Free tier: 10,000 characters/month (shared with TTS)
- Starter: 30,000 characters/month
- Rate: ~3 requests/second

**Prompt Tips:**
- Be specific about material, environment, intensity: "metal sword hitting stone floor in a large cave with echo"
- Specify duration context: "short burst" vs "sustained rumble"
- Avoid abstract concepts; describe physical sounds

---

### ElevenLabs Text-to-Speech

```python
class ElevenLabsTTSProvider(AudioProvider):
    """ElevenLabs Text-to-Speech API integration.

    High-quality multilingual voice synthesis.
    Auth: xi-api-key header via ELEVENLABS_API_KEY env var.
    Docs: https://elevenlabs.io/docs/api-reference/text-to-speech
    Cost: ~$0.30 per 1000 characters (check current pricing).
    License: Safe.
    """

    provider_name = "elevenlabs_tts"
    supported_categories = ["voice"]

    # Common built-in voice IDs
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "adam": "pNInz6obpgDQGcFmaJgB",
        "antoni": "ErXwobaYiN019PkySvjV",
        "bella": "EXAVITQu4vr4xnSDxMaL",
        "elli": "MF3mGyEYCl7XYWbV9V6O",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "sam": "yoZ06aMxZJJ28mfd3POQ",
    }

    MODELS = {
        "multilingual_v2": "eleven_multilingual_v2",
        "turbo_v2_5": "eleven_turbo_v2_5",
    }

    def __init__(self):
        self.api_key = os.environ["ELEVENLABS_API_KEY"]
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate speech from text.

        Args:
            config: AudioGenerationConfig with:
                - prompt: The text to speak
                - voice_id: ElevenLabs voice ID or name from VOICES dict
                - language: Language code (used with multilingual model)
        """
        voice_id = config.voice_id or self.VOICES.get("rachel", "21m00Tcm4TlvDq8ikWAM")
        if voice_id in self.VOICES:
            voice_id = self.VOICES[voice_id]

        model_id = self.MODELS["multilingual_v2"]
        if config.language == "en":
            model_id = self.MODELS["turbo_v2_5"]

        payload = {
            "text": config.prompt,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        resp = httpx.post(
            f"{self.base_url}/text-to-speech/{voice_id}",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()

        return AudioGenerationResult(
            task_id=f"el_tts_{int(time.time())}",
            provider=self.provider_name,
            status="succeeded",
            audio_bytes=resp.content,
            format="mp3",
            sample_rate=44100,
            metadata={"voice_id": voice_id, "model_id": model_id},
        )

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        char_count = len(config.prompt)
        return (char_count / 1000) * 0.30

    def list_voices(self) -> list[dict]:
        """List all available voices."""
        resp = httpx.get(
            f"{self.base_url}/voices",
            headers={"xi-api-key": self.api_key},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])


# --- Usage Example ---

def generate_voice_elevenlabs(text: str, voice: str = "rachel",
                              output_path: str = "voice.mp3") -> Path:
    """Generate speech using ElevenLabs.

    Example:
        generate_voice_elevenlabs(
            text="Welcome to the dungeon, brave adventurer.",
            voice="adam",
            output_path="npc_greeting.mp3",
        )
    """
    provider = ElevenLabsTTSProvider()
    config = AudioGenerationConfig(
        prompt=text,
        category="voice",
        voice_id=voice,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**Voice Settings Guide:**
- `stability` (0-1): Lower = more expressive/variable, Higher = more consistent
- `similarity_boost` (0-1): Higher = closer to original voice, may amplify artifacts
- `style` (0-1): Style exaggeration, higher = more dramatic (multilingual_v2 only)
- `use_speaker_boost`: Increases similarity to original speaker at slight quality cost

**Rate Limits:**
- Shared character quota with SFX
- Concurrent request limit depends on plan tier
- Rate: ~2-3 requests/second

---

### Stable Audio 2.5 (via Replicate)

```python
class StableAudioProvider(AudioProvider):
    """Stable Audio 2.5 via Replicate API.

    High-quality music and sound effect generation.
    Auth: Bearer token via REPLICATE_API_TOKEN env var.
    Model: stability-ai/stable-audio
    Cost: ~$0.03-0.10 per generation (check current pricing).
    License: Safe (licensed training data).
    """

    provider_name = "stable_audio"
    supported_categories = ["bgm", "sfx", "ambient"]

    def __init__(self):
        self.api_key = os.environ["REPLICATE_API_TOKEN"]
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate audio using Stable Audio 2.5.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Description of desired audio
                - duration_seconds: Up to 47 seconds
                - seed: Optional seed for reproducibility
        """
        # Submit prediction
        payload = {
            "version": "stable-audio-2.5",  # Use latest stable version
            "input": {
                "prompt": config.prompt,
                "seconds_total": min(config.duration_seconds, 47.0),
                "steps": 100,
                "cfg_scale": 7.0,
            },
        }
        if config.seed is not None:
            payload["input"]["seed"] = config.seed

        resp = httpx.post(
            f"{self.base_url}/predictions",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        prediction = resp.json()
        prediction_id = prediction["id"]

        # Poll for completion
        result = self._poll_prediction(prediction_id)
        return result

    def _poll_prediction(self, prediction_id: str,
                         interval: int = 3, max_wait: int = 300) -> AudioGenerationResult:
        """Poll Replicate prediction until complete."""
        elapsed = 0
        current_interval = interval
        while elapsed < max_wait:
            resp = httpx.get(
                f"{self.base_url}/predictions/{prediction_id}",
                headers=self.headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]

            if status == "succeeded":
                output_url = data["output"]
                if isinstance(output_url, list):
                    output_url = output_url[0]
                return AudioGenerationResult(
                    task_id=prediction_id,
                    provider=self.provider_name,
                    status="succeeded",
                    audio_url=output_url,
                    format="wav",
                    sample_rate=44100,
                    metadata={"metrics": data.get("metrics", {})},
                )
            if status == "failed":
                raise RuntimeError(
                    f"Stable Audio generation failed: {data.get('error', 'unknown')}"
                )

            print(f"[stable_audio] {prediction_id}: {status} elapsed={elapsed}s")
            time.sleep(current_interval)
            elapsed += current_interval
            current_interval = min(current_interval * 1.5, 15)

        raise TimeoutError(f"Prediction {prediction_id} timed out after {max_wait}s")

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        # Rough estimate based on duration and compute time
        if config.duration_seconds <= 10:
            return 0.03
        elif config.duration_seconds <= 30:
            return 0.06
        else:
            return 0.10


# --- Usage Example ---

def generate_bgm_stable_audio(prompt: str, duration: float = 30.0,
                               seed: Optional[int] = None,
                               output_path: str = "bgm.wav") -> Path:
    """Generate background music using Stable Audio 2.5.

    Example:
        generate_bgm_stable_audio(
            prompt="epic orchestral battle music with brass and drums, 120 BPM, cinematic",
            duration=30.0,
            seed=42,
            output_path="battle_bgm.wav",
        )
    """
    provider = StableAudioProvider()
    config = AudioGenerationConfig(
        prompt=prompt,
        category="bgm",
        duration_seconds=duration,
        seed=seed,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**Prompt Tips for Stable Audio:**
- Include genre, instruments, tempo, mood: "lo-fi hip hop beat with jazzy piano, vinyl crackle, 85 BPM, relaxed"
- For SFX, describe the sound source and environment: "thunder crack followed by distant rolling rumble, outdoor"
- Use negative prompts in the prompt itself: "orchestral score, no vocals, no drums"
- Specify duration context: "short jingle" vs "looping ambient track"

**Rate Limits (Replicate):**
- Default: 600 predictions/minute
- Cold start may add 10-30s on first request

---

### MusicGen / AudioCraft (via Replicate)

```python
class MusicGenProvider(AudioProvider):
    """Meta MusicGen via Replicate API.

    Text-to-music generation with optional melody continuation.
    Auth: Bearer token via REPLICATE_API_TOKEN env var.
    Model: meta/musicgen
    Cost: ~$0.02-0.08 per generation (check current pricing).
    License: Safe (MIT code, CC-BY-NC for training data - check commercial use).
    """

    provider_name = "musicgen"
    supported_categories = ["bgm", "ambient"]

    MODEL_VERSIONS = {
        "small": "small",    # 300M params, fastest
        "medium": "medium",  # 1.5B params, balanced
        "large": "large",    # 3.3B params, highest quality
    }

    def __init__(self):
        self.api_key = os.environ["REPLICATE_API_TOKEN"]
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate music from text prompt.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Music description
                - duration_seconds: Up to 30 seconds
                - quality: "preview" (small), "standard" (medium), "high" (large)
                - seed: Optional for reproducibility
        """
        model_version = {
            "preview": "small",
            "standard": "medium",
            "high": "large",
        }.get(config.quality, "medium")

        payload = {
            "version": "musicgen",  # Use latest
            "input": {
                "prompt": config.prompt,
                "duration": min(config.duration_seconds, 30),
                "model_version": model_version,
                "top_k": 250,
                "top_p": 0.0,
                "temperature": 1.0,
                "output_format": "wav",
                "normalization_strategy": "loudness",
            },
        }
        if config.seed is not None:
            payload["input"]["seed"] = config.seed

        resp = httpx.post(
            f"{self.base_url}/predictions",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        prediction = resp.json()
        prediction_id = prediction["id"]

        return self._poll_prediction(prediction_id)

    def generate_continuation(self, config: AudioGenerationConfig,
                               audio_url: str) -> AudioGenerationResult:
        """Continue from an existing audio clip.

        Useful for extending a generated BGM track or creating seamless loops.
        """
        payload = {
            "version": "musicgen",
            "input": {
                "prompt": config.prompt,
                "duration": min(config.duration_seconds, 30),
                "model_version": "medium",
                "continuation": True,
                "continuation_start": 0,
                "input_audio": audio_url,
                "output_format": "wav",
            },
        }

        resp = httpx.post(
            f"{self.base_url}/predictions",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        prediction = resp.json()
        return self._poll_prediction(prediction["id"])

    def _poll_prediction(self, prediction_id: str,
                         interval: int = 3, max_wait: int = 300) -> AudioGenerationResult:
        """Poll Replicate prediction until complete."""
        elapsed = 0
        current_interval = interval
        while elapsed < max_wait:
            resp = httpx.get(
                f"{self.base_url}/predictions/{prediction_id}",
                headers=self.headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]

            if status == "succeeded":
                output_url = data["output"]
                if isinstance(output_url, list):
                    output_url = output_url[0]
                return AudioGenerationResult(
                    task_id=prediction_id,
                    provider=self.provider_name,
                    status="succeeded",
                    audio_url=output_url,
                    format="wav",
                    sample_rate=32000,
                    metadata={"metrics": data.get("metrics", {})},
                )
            if status == "failed":
                raise RuntimeError(
                    f"MusicGen generation failed: {data.get('error', 'unknown')}"
                )

            print(f"[musicgen] {prediction_id}: {status} elapsed={elapsed}s")
            time.sleep(current_interval)
            elapsed += current_interval
            current_interval = min(current_interval * 1.5, 15)

        raise TimeoutError(f"Prediction {prediction_id} timed out after {max_wait}s")

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        model_multiplier = {"preview": 0.5, "standard": 1.0, "high": 2.0}
        base = 0.04
        return base * model_multiplier.get(config.quality, 1.0)


# --- Usage Example ---

def generate_bgm_musicgen(prompt: str, duration: float = 15.0,
                           quality: str = "standard",
                           output_path: str = "bgm.wav") -> Path:
    """Generate background music using MusicGen.

    Example:
        generate_bgm_musicgen(
            prompt="calm fantasy RPG village theme with acoustic guitar and flute",
            duration=15.0,
            quality="high",
            output_path="village_bgm.wav",
        )
    """
    provider = MusicGenProvider()
    config = AudioGenerationConfig(
        prompt=prompt,
        category="bgm",
        duration_seconds=duration,
        quality=quality,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**MusicGen Model Selection:**
- `small` (300M): Fast iteration, good for previews, ~5s generation for 10s audio
- `medium` (1.5B): Best balance of quality and speed for most game audio
- `large` (3.3B): Highest quality, use for final assets, 2-3x slower than medium

**Rate Limits (Replicate):**
- Default: 600 predictions/minute
- Large model may queue during peak times

---

### OpenAI Text-to-Speech

```python
class OpenAITTSProvider(AudioProvider):
    """OpenAI Text-to-Speech API integration.

    Reliable, consistent voice generation with multiple voices.
    Auth: Bearer token via OPENAI_API_KEY env var.
    Docs: https://platform.openai.com/docs/guides/text-to-speech
    Cost: ~$15.00/1M chars (tts-1), ~$30.00/1M chars (tts-1-hd) (check current pricing).
    License: Safe.
    """

    provider_name = "openai_tts"
    supported_categories = ["voice"]

    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    # Voice characteristics for game audio selection
    VOICE_GUIDE = {
        "alloy": "neutral, versatile, suitable for UI narration",
        "echo": "warm, conversational, suitable for friendly NPCs",
        "fable": "expressive, dramatic, suitable for storytelling/cutscenes",
        "onyx": "deep, authoritative, suitable for villains/commanders",
        "nova": "bright, energetic, suitable for young characters",
        "shimmer": "soft, gentle, suitable for tutorial/guide characters",
    }

    def __init__(self):
        self.api_key = os.environ["OPENAI_API_KEY"]
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate speech from text.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Text to speak
                - voice_id: One of VOICES (default: "alloy")
                - quality: "standard" uses tts-1, "high" uses tts-1-hd
                - output_format: "mp3", "opus", "aac", "flac", "wav", "pcm"
        """
        voice = config.voice_id if config.voice_id in self.VOICES else "alloy"
        model = "tts-1-hd" if config.quality == "high" else "tts-1"

        format_map = {
            "wav": "wav",
            "mp3": "mp3",
            "ogg": "opus",
            "flac": "flac",
        }
        response_format = format_map.get(config.output_format, "mp3")

        payload = {
            "model": model,
            "voice": voice,
            "input": config.prompt,
            "response_format": response_format,
            "speed": 1.0,  # 0.25 to 4.0
        }

        resp = httpx.post(
            f"{self.base_url}/audio/speech",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()

        return AudioGenerationResult(
            task_id=f"oai_tts_{int(time.time())}",
            provider=self.provider_name,
            status="succeeded",
            audio_bytes=resp.content,
            format=response_format,
            sample_rate=24000 if response_format == "opus" else 44100,
            metadata={"voice": voice, "model": model},
        )

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        char_count = len(config.prompt)
        rate = 30.0 if config.quality == "high" else 15.0  # per 1M chars
        return (char_count / 1_000_000) * rate


# --- Usage Example ---

def generate_voice_openai(text: str, voice: str = "alloy",
                          quality: str = "standard",
                          output_path: str = "voice.mp3") -> Path:
    """Generate speech using OpenAI TTS.

    Example:
        generate_voice_openai(
            text="You have discovered a legendary sword!",
            voice="fable",
            quality="high",
            output_path="item_discovery.mp3",
        )
    """
    provider = OpenAITTSProvider()
    config = AudioGenerationConfig(
        prompt=text,
        category="voice",
        voice_id=voice,
        quality=quality,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**tts-1 vs tts-1-hd:**
- `tts-1`: Lower latency, good for real-time/preview. May have audible artifacts in some cases.
- `tts-1-hd`: Higher quality, better for final assets. 2x cost but cleaner output.

**Rate Limits:**
- Tier 1: 500 RPM, 10M TPM
- Tier 2+: Higher limits
- No concurrent request limit beyond RPM

---

### Google Cloud Text-to-Speech

```python
class GoogleTTSProvider(AudioProvider):
    """Google Cloud Text-to-Speech API integration.

    Wide selection of voices across many languages with SSML support.
    Auth: OAuth2 Bearer token or API key.
    Docs: https://cloud.google.com/text-to-speech/docs
    Cost: ~$4.00/1M chars (Standard), ~$16.00/1M chars (Neural2/Studio)
          (check current pricing).
    License: Safe.
    """

    provider_name = "google_tts"
    supported_categories = ["voice"]

    VOICE_TYPES = {
        "standard": "Standard",
        "wavenet": "WaveNet",
        "neural2": "Neural2",
        "studio": "Studio",
    }

    def __init__(self):
        # Uses Application Default Credentials or explicit service account
        self._token = self._get_access_token()
        self.base_url = "https://texttospeech.googleapis.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _get_access_token() -> str:
        """Get OAuth2 access token from service account credentials."""
        import json
        import jwt  # PyJWT
        creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        with open(creds_path) as f:
            creds = json.load(f)

        now = int(time.time())
        payload = {
            "iss": creds["client_email"],
            "scope": "https://www.googleapis.com/auth/cloud-platform",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        signed_jwt = jwt.encode(payload, creds["private_key"], algorithm="RS256")

        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate speech from text or SSML.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Plain text or SSML-wrapped text
                - voice_id: Voice name (e.g. "en-US-Neural2-D")
                - language: Language code (e.g. "en-US", "ja-JP")
                - output_format: "mp3", "wav", "ogg"
        """
        # Detect SSML
        is_ssml = config.prompt.strip().startswith("<speak>")
        input_field = {"ssml": config.prompt} if is_ssml else {"text": config.prompt}

        encoding_map = {
            "mp3": "MP3",
            "wav": "LINEAR16",
            "ogg": "OGG_OPUS",
        }
        audio_encoding = encoding_map.get(config.output_format, "MP3")

        voice_name = config.voice_id or f"{config.language}-Neural2-D"

        payload = {
            "input": input_field,
            "voice": {
                "languageCode": config.language,
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": 1.0,   # 0.25 to 4.0
                "pitch": 0.0,          # -20.0 to 20.0 semitones
                "volumeGainDb": 0.0,   # -96.0 to 16.0
                "sampleRateHertz": config.sample_rate,
            },
        }

        resp = httpx.post(
            f"{self.base_url}/text:synthesize",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        import base64
        audio_bytes = base64.b64decode(data["audioContent"])

        return AudioGenerationResult(
            task_id=f"g_tts_{int(time.time())}",
            provider=self.provider_name,
            status="succeeded",
            audio_bytes=audio_bytes,
            format=config.output_format,
            sample_rate=config.sample_rate,
            metadata={"voice_name": voice_name},
        )

    def list_voices(self, language_code: str = "") -> list[dict]:
        """List available voices, optionally filtered by language."""
        params = {}
        if language_code:
            params["languageCode"] = language_code

        resp = httpx.get(
            f"{self.base_url}/voices",
            headers=self.headers,
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        char_count = len(config.prompt)
        # Neural2/Studio voices cost more
        voice_name = config.voice_id or ""
        if "Neural2" in voice_name or "Studio" in voice_name:
            rate = 16.0
        elif "WaveNet" in voice_name:
            rate = 16.0
        else:
            rate = 4.0
        return (char_count / 1_000_000) * rate


# --- Usage Example ---

def generate_voice_google(text: str, voice: str = "en-US-Neural2-D",
                          language: str = "en-US",
                          output_path: str = "voice.mp3") -> Path:
    """Generate speech using Google Cloud TTS.

    Example:
        generate_voice_google(
            text="The ancient door opens with a thunderous groan.",
            voice="en-US-Studio-M",
            output_path="narrator.mp3",
        )

    SSML Example:
        generate_voice_google(
            text='<speak>Beware! <break time="500ms"/> The dragon approaches.</speak>',
            voice="en-US-Neural2-D",
            output_path="dragon_warning.mp3",
        )
    """
    provider = GoogleTTSProvider()
    config = AudioGenerationConfig(
        prompt=text,
        category="voice",
        voice_id=voice,
        language=language,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**Google TTS Voice Tiers:**
- **Standard**: Lowest cost, basic quality, concatenative synthesis
- **WaveNet**: High quality, natural-sounding, uses DeepMind WaveNet
- **Neural2**: Latest neural model, improved naturalness over WaveNet
- **Studio**: Highest quality, limited languages, best for final assets

**SSML Features for Games:**
- `<break>`: Pause between phrases (dramatic effect)
- `<prosody>`: Control rate, pitch, volume per phrase
- `<emphasis>`: Stress specific words
- `<say-as>`: Numbers, dates, spell-out

---

### Bark (via Replicate)

```python
class BarkProvider(AudioProvider):
    """Suno Bark via Replicate API.

    Expressive TTS with non-speech sounds (laughter, music, etc.).
    Auth: Bearer token via REPLICATE_API_TOKEN env var.
    Model: suno-ai/bark
    Cost: ~$0.02-0.05 per generation (check current pricing).
    License: Safe (MIT).
    """

    provider_name = "bark"
    supported_categories = ["voice", "ambient"]

    # Speaker presets for consistent character voices
    SPEAKER_PRESETS = {
        "male_1": "v2/en_speaker_0",
        "male_2": "v2/en_speaker_1",
        "male_3": "v2/en_speaker_6",
        "female_1": "v2/en_speaker_2",
        "female_2": "v2/en_speaker_3",
        "female_3": "v2/en_speaker_9",
        "narrator": "v2/en_speaker_5",
        # Non-English
        "ja_male": "v2/ja_speaker_0",
        "ja_female": "v2/ja_speaker_2",
        "zh_male": "v2/zh_speaker_0",
        "zh_female": "v2/zh_speaker_4",
        "de_male": "v2/de_speaker_0",
        "fr_female": "v2/fr_speaker_1",
    }

    # Non-speech sound tags for game audio
    SOUND_TAGS = {
        "laugh": "[laughing]",
        "sigh": "[sighing]",
        "gasp": "[gasps]",
        "cry": "[crying]",
        "music": "[music]",
        "clear_throat": "[clears throat]",
    }

    def __init__(self):
        self.api_key = os.environ["REPLICATE_API_TOKEN"]
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Generate expressive speech with optional non-speech sounds.

        Args:
            config: AudioGenerationConfig with:
                - prompt: Text with optional sound tags like [laughing], [music]
                - voice_id: Speaker preset name or Bark history_prompt path
        """
        history_prompt = config.voice_id
        if history_prompt in self.SPEAKER_PRESETS:
            history_prompt = self.SPEAKER_PRESETS[history_prompt]

        payload = {
            "version": "bark",  # Use latest
            "input": {
                "prompt": config.prompt,
                "text_temp": 0.7,      # 0.0-1.0, controls speech variation
                "waveform_temp": 0.7,  # 0.0-1.0, controls audio variation
            },
        }
        if history_prompt:
            payload["input"]["history_prompt"] = history_prompt

        resp = httpx.post(
            f"{self.base_url}/predictions",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        prediction = resp.json()
        return self._poll_prediction(prediction["id"])

    def _poll_prediction(self, prediction_id: str,
                         interval: int = 3, max_wait: int = 180) -> AudioGenerationResult:
        """Poll Replicate prediction until complete."""
        elapsed = 0
        current_interval = interval
        while elapsed < max_wait:
            resp = httpx.get(
                f"{self.base_url}/predictions/{prediction_id}",
                headers=self.headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]

            if status == "succeeded":
                output_url = data["output"]
                if isinstance(output_url, dict):
                    output_url = output_url.get("audio_out", "")
                elif isinstance(output_url, list):
                    output_url = output_url[0]
                return AudioGenerationResult(
                    task_id=prediction_id,
                    provider=self.provider_name,
                    status="succeeded",
                    audio_url=output_url,
                    format="wav",
                    sample_rate=24000,
                    metadata={"metrics": data.get("metrics", {})},
                )
            if status == "failed":
                raise RuntimeError(
                    f"Bark generation failed: {data.get('error', 'unknown')}"
                )

            print(f"[bark] {prediction_id}: {status} elapsed={elapsed}s")
            time.sleep(current_interval)
            elapsed += current_interval
            current_interval = min(current_interval * 1.5, 10)

        raise TimeoutError(f"Prediction {prediction_id} timed out after {max_wait}s")

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        return 0.03  # Approximate per generation


# --- Usage Example ---

def generate_voice_bark(text: str, speaker: str = "narrator",
                        output_path: str = "voice.wav") -> Path:
    """Generate expressive speech using Bark.

    Example (normal speech):
        generate_voice_bark(
            text="Greetings, traveler. What brings you to these lands?",
            speaker="male_1",
            output_path="npc_greeting.wav",
        )

    Example (with non-speech sounds):
        generate_voice_bark(
            text="[laughing] Oh, you think you can defeat me? [clears throat] Very well then.",
            speaker="female_1",
            output_path="villain_taunt.wav",
        )

    Example (singing/music):
        generate_voice_bark(
            text="[music] La la la, the hero comes to save the day [music]",
            speaker="female_2",
            output_path="bard_song.wav",
        )
    """
    provider = BarkProvider()
    config = AudioGenerationConfig(
        prompt=text,
        category="voice",
        voice_id=speaker,
    )
    result = provider.generate(config)
    return provider.save_audio(result, output_path)
```

**Bark Special Features for Games:**
- Non-speech sounds: `[laughing]`, `[sighs]`, `[music]`, `[gasps]`, `[clears throat]`, `[crying]`
- Capitalization and punctuation affect emphasis and pacing
- Ellipses (`...`) create hesitation
- ALL CAPS creates shouting effect
- Short prompts work best (<15 seconds of speech per generation)

**Temperature Guide:**
- `text_temp` 0.1-0.3: Very consistent, robotic. Good for UI/system voices.
- `text_temp` 0.5-0.7: Natural variation. Best for most game dialogue.
- `text_temp` 0.8-1.0: Highly varied, may produce unexpected results. Good for crazy/chaotic characters.

---

### JSFXR (Local Procedural SFX)

```javascript
/**
 * JSFXR - Procedural retro sound effect generator.
 *
 * Local library, no API key needed. Generates chiptune/retro game SFX.
 * Based on sfxr by DrPetter.
 * Install: npm install jsfxr
 * License: MIT
 * Cost: Free
 */

// --- Installation ---
// npm install jsfxr

const jsfxr = require('jsfxr');

// --- Preset Categories ---
// Each preset returns a parameter object that can be customized

const GAME_SFX_PRESETS = {
  // UI & Menu
  menuSelect: () => jsfxr.blipSelect(),
  menuHover: () => {
    const params = jsfxr.blipSelect();
    params.p_freq_limit = 0.4;
    params.p_env_sustain = 0.05;
    return params;
  },
  confirm: () => jsfxr.powerUp(),
  cancel: () => {
    const params = jsfxr.hitHurt();
    params.p_base_freq = 0.3;
    return params;
  },

  // Player Actions
  jump: () => jsfxr.jump(),
  doubleJump: () => {
    const params = jsfxr.jump();
    params.p_base_freq = 0.45;
    params.p_freq_ramp = 0.35;
    return params;
  },
  land: () => {
    const params = jsfxr.hitHurt();
    params.p_base_freq = 0.15;
    params.p_env_sustain = 0.1;
    return params;
  },

  // Combat
  swordSwing: () => {
    const params = jsfxr.laserShoot();
    params.wave_type = 3; // noise
    params.p_env_sustain = 0.05;
    params.p_env_decay = 0.15;
    return params;
  },
  laserShoot: () => jsfxr.laserShoot(),
  explosion: () => jsfxr.explosion(),
  smallExplosion: () => {
    const params = jsfxr.explosion();
    params.p_env_sustain = 0.1;
    params.p_env_decay = 0.2;
    return params;
  },
  hit: () => jsfxr.hitHurt(),
  shield: () => {
    const params = jsfxr.powerUp();
    params.p_base_freq = 0.5;
    params.wave_type = 1; // sawtooth
    return params;
  },

  // Items & Rewards
  coinPickup: () => jsfxr.pickupCoin(),
  gemPickup: () => {
    const params = jsfxr.pickupCoin();
    params.p_base_freq = 0.5;
    params.p_freq_ramp = 0.25;
    return params;
  },
  healthPickup: () => jsfxr.powerUp(),
  powerUp: () => jsfxr.powerUp(),
  levelUp: () => {
    const params = jsfxr.powerUp();
    params.p_env_sustain = 0.3;
    params.p_env_decay = 0.4;
    params.p_arp_speed = 0.5;
    return params;
  },
};


/**
 * Generate a retro sound effect and save as WAV.
 *
 * @param {string} presetName - Key from GAME_SFX_PRESETS
 * @param {string} outputPath - Output WAV file path
 * @param {object} [overrides] - Optional parameter overrides
 * @returns {Buffer} WAV audio buffer
 *
 * @example
 * // Generate a coin pickup sound
 * generateRetroSFX('coinPickup', 'coin.wav');
 *
 * // Generate with custom parameters
 * generateRetroSFX('explosion', 'big_boom.wav', {
 *   p_env_sustain: 0.4,
 *   p_env_decay: 0.6,
 * });
 */
function generateRetroSFX(presetName, outputPath, overrides = {}) {
  const fs = require('fs');
  const path = require('path');

  const presetFn = GAME_SFX_PRESETS[presetName];
  if (!presetFn) {
    throw new Error(
      `Unknown preset: ${presetName}. Available: ${Object.keys(GAME_SFX_PRESETS).join(', ')}`
    );
  }

  const params = presetFn();
  Object.assign(params, overrides);

  const wavBuffer = jsfxr.toWav(params);

  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(outputPath, Buffer.from(wavBuffer));

  return wavBuffer;
}


/**
 * Generate a batch of SFX variations from a single preset.
 * Useful for creating multiple hit sounds, coin pickups, etc.
 *
 * @param {string} presetName - Key from GAME_SFX_PRESETS
 * @param {number} count - Number of variations
 * @param {string} outputDir - Directory for output files
 * @returns {string[]} Array of output file paths
 *
 * @example
 * // Generate 5 hit sound variations
 * generateSFXVariations('hit', 5, './sfx/hits/');
 */
function generateSFXVariations(presetName, count, outputDir) {
  const fs = require('fs');
  const path = require('path');

  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const paths = [];
  for (let i = 0; i < count; i++) {
    const presetFn = GAME_SFX_PRESETS[presetName];
    const params = presetFn(); // Each call randomizes slightly
    const wavBuffer = jsfxr.toWav(params);
    const filePath = path.join(outputDir, `${presetName}_${i}.wav`);
    fs.writeFileSync(filePath, Buffer.from(wavBuffer));
    paths.push(filePath);
  }

  return paths;
}
```

**JSFXR Parameter Reference:**

| Parameter | Range | Description |
|-----------|-------|-------------|
| `wave_type` | 0-3 | 0=square, 1=sawtooth, 2=sine, 3=noise |
| `p_base_freq` | 0-1 | Base frequency |
| `p_freq_limit` | 0-1 | Minimum frequency cutoff |
| `p_freq_ramp` | -1 to 1 | Frequency slide over time |
| `p_env_attack` | 0-1 | Attack time |
| `p_env_sustain` | 0-1 | Sustain time |
| `p_env_decay` | 0-1 | Decay time |
| `p_env_punch` | 0-1 | Sustain punch |
| `p_arp_speed` | 0-1 | Arpeggio speed |
| `p_arp_mod` | -1 to 1 | Arpeggio frequency change |

**When to Use JSFXR:**
- Retro/pixel art games needing chiptune-style SFX
- Rapid prototyping (instant generation, no API calls)
- UI sounds (clicks, hovers, confirmations)
- Procedural variation (multiple hit sounds from one preset)
- Offline/local development without API keys

---

### Freesound API

```python
class FreesoundProvider(AudioProvider):
    """Freesound API integration.

    Massive library of CC-licensed audio. Search + download.
    Auth: API key or OAuth2 Bearer token via FREESOUND_API_KEY env var.
    Docs: https://freesound.org/docs/api/
    Cost: Free (rate limited).
    License: VARIES PER SOUND - MUST check license before use.
    """

    provider_name = "freesound"
    supported_categories = ["sfx", "bgm", "ambient", "voice", "ui"]

    # License compatibility for game use
    LICENSE_SAFE = {"Creative Commons 0"}  # No attribution needed
    LICENSE_ATTRIBUTION = {
        "Attribution",
        "Attribution Noncommercial",
    }  # Must credit author

    def __init__(self):
        self.api_key = os.environ["FREESOUND_API_KEY"]
        self.base_url = "https://freesound.org/apiv2"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
        }

    def search(self, query: str, limit: int = 15,
               min_duration: float = 0.0,
               max_duration: float = 60.0,
               license_filter: str = "",
               sort: str = "score") -> list[dict]:
        """Search for sounds on Freesound.

        Args:
            query: Search terms (e.g. "sword clash metal")
            limit: Max results (up to 150 per page)
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            license_filter: "Creative Commons 0", "Attribution", etc.
            sort: "score", "duration_asc", "duration_desc",
                  "created_asc", "created_desc",
                  "downloads_asc", "downloads_desc",
                  "rating_asc", "rating_desc"
        """
        params = {
            "query": query,
            "page_size": min(limit, 150),
            "fields": "id,name,tags,description,duration,license,avg_rating,"
                      "num_downloads,previews,username,filesize,samplerate,"
                      "bitdepth,channels,type",
            "sort": sort,
        }

        filters = []
        if min_duration > 0:
            filters.append(f"duration:[{min_duration} TO *]")
        if max_duration < 9999:
            filters.append(f"duration:[* TO {max_duration}]")
        if license_filter:
            filters.append(f'license:"{license_filter}"')
        if filters:
            params["filter"] = " ".join(filters)

        resp = httpx.get(
            f"{self.base_url}/search/text/",
            headers=self.headers,
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        return data.get("results", [])

    def download(self, sound_id: int, output_dir: str) -> dict:
        """Download a sound by ID.

        IMPORTANT: Always check the license field before using in a game.
        CC0 sounds can be used freely. Attribution sounds require credit.

        Returns dict with filepath, license, and attribution info.
        """
        # Get sound details first
        resp = httpx.get(
            f"{self.base_url}/sounds/{sound_id}/",
            headers=self.headers,
            params={"fields": "id,name,license,username,previews,download"},
            timeout=30.0,
        )
        resp.raise_for_status()
        sound_info = resp.json()

        # Download the sound
        download_url = sound_info.get("download")
        if not download_url:
            # Fall back to high-quality preview (no OAuth needed)
            download_url = sound_info["previews"]["preview-hq-mp3"]

        dl_resp = httpx.get(
            download_url,
            headers=self.headers,
            timeout=120.0,
            follow_redirects=True,
        )
        dl_resp.raise_for_status()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine extension from content type or URL
        ext = download_url.rsplit(".", 1)[-1].split("?")[0]
        if ext not in ("wav", "mp3", "ogg", "flac", "aiff"):
            ext = "mp3"
        filepath = output_path / f"freesound_{sound_id}.{ext}"
        filepath.write_bytes(dl_resp.content)

        license_str = sound_info.get("license", "unknown")
        username = sound_info.get("username", "unknown")

        return {
            "filepath": str(filepath),
            "sound_id": sound_id,
            "name": sound_info.get("name", ""),
            "license": license_str,
            "username": username,
            "attribution": f'"{sound_info.get("name", "")}" by {username} '
                          f"(freesound.org/{sound_id}) - {license_str}",
        }

    def generate(self, config: AudioGenerationConfig) -> AudioGenerationResult:
        """Search and download the best matching sound."""
        results = self.search(
            query=config.prompt,
            max_duration=config.duration_seconds * 2 if config.duration_seconds > 0 else 60,
            limit=1,
        )
        if not results:
            raise ValueError(f"No sounds found for: {config.prompt}")

        sound = results[0]
        preview_url = sound.get("previews", {}).get("preview-hq-mp3", "")

        return AudioGenerationResult(
            task_id=str(sound["id"]),
            provider=self.provider_name,
            status="succeeded",
            audio_url=preview_url,
            duration_seconds=sound.get("duration", 0),
            format="mp3",
            sample_rate=sound.get("samplerate", 44100),
            metadata={
                "name": sound.get("name"),
                "license": sound.get("license"),
                "username": sound.get("username"),
                "tags": sound.get("tags", []),
            },
        )

    def estimate_cost(self, config: AudioGenerationConfig) -> float:
        return 0.0  # Free


# --- Usage Example ---

def search_and_download_freesound(query: str, output_dir: str = "./sounds",
                                   limit: int = 5,
                                   cc0_only: bool = True) -> list[dict]:
    """Search Freesound and download matching sounds.

    Example:
        results = search_and_download_freesound(
            query="forest ambience birds wind",
            output_dir="./sounds/ambient",
            limit=3,
            cc0_only=True,
        )
        for r in results:
            print(f"  {r['name']}: {r['license']}")
            print(f"  Attribution: {r['attribution']}")
    """
    provider = FreesoundProvider()
    license_filter = "Creative Commons 0" if cc0_only else ""
    results = provider.search(query, limit=limit, license_filter=license_filter)

    downloads = []
    for sound in results:
        info = provider.download(sound["id"], output_dir)
        downloads.append(info)

    return downloads
```

**License Guidelines for Game Audio:**
- **CC0**: Safe for any use, no attribution required. Prefer this for shipped games.
- **CC-BY**: Must credit the author. Include in game credits or a LICENSES file.
- **CC-BY-NC**: Non-commercial only. NOT safe for commercial game releases.
- Always store the license and attribution info alongside downloaded sounds.
- Use `cc0_only=True` for the safest option in commercial projects.

**Rate Limits:**
- 60 requests/minute (authenticated)
- 2000 requests/day
- Download limits depend on account type

**Search Tips:**
- Use specific descriptors: "footstep concrete indoor" not just "footstep"
- Filter by duration for game-appropriate clips
- Sort by "rating_desc" for highest-quality results
- Combine multiple short clips via layering rather than searching for complex sounds

---

## Fallback Chain Pattern

Automatic fallback between providers when the primary provider fails or is unavailable:

```python
import os
import time
from typing import Optional


class AudioFallbackChain:
    """Try multiple providers in sequence until one succeeds.

    Useful for production pipelines where reliability matters.
    Falls back to the next provider on failure or timeout.
    """

    # Provider chains by audio category
    CHAINS = {
        "sfx": ["elevenlabs_sfx", "stable_audio", "freesound"],
        "bgm": ["stable_audio", "musicgen", "freesound"],
        "voice": ["elevenlabs_tts", "openai_tts", "google_tts", "bark"],
        "ambient": ["stable_audio", "musicgen", "bark", "freesound"],
        "ui": ["jsfxr", "elevenlabs_sfx", "freesound"],
    }

    # Provider factory
    PROVIDERS = {
        "elevenlabs_sfx": lambda: ElevenLabsSFXProvider(),
        "elevenlabs_tts": lambda: ElevenLabsTTSProvider(),
        "stable_audio": lambda: StableAudioProvider(),
        "musicgen": lambda: MusicGenProvider(),
        "openai_tts": lambda: OpenAITTSProvider(),
        "google_tts": lambda: GoogleTTSProvider(),
        "bark": lambda: BarkProvider(),
        "freesound": lambda: FreesoundProvider(),
    }

    # Required env vars per provider (for availability check)
    REQUIRED_ENV = {
        "elevenlabs_sfx": "ELEVENLABS_API_KEY",
        "elevenlabs_tts": "ELEVENLABS_API_KEY",
        "stable_audio": "REPLICATE_API_TOKEN",
        "musicgen": "REPLICATE_API_TOKEN",
        "openai_tts": "OPENAI_API_KEY",
        "google_tts": "GOOGLE_APPLICATION_CREDENTIALS",
        "bark": "REPLICATE_API_TOKEN",
        "freesound": "FREESOUND_API_KEY",
        "jsfxr": None,  # Always available (local)
    }

    def __init__(self, custom_chains: Optional[dict] = None):
        if custom_chains:
            self.CHAINS.update(custom_chains)

    def _is_available(self, provider_name: str) -> bool:
        """Check if a provider's API key is configured."""
        env_var = self.REQUIRED_ENV.get(provider_name)
        if env_var is None:
            return True  # No API key needed (local provider)
        return bool(os.environ.get(env_var))

    def generate(self, config: AudioGenerationConfig,
                 max_attempts: int = 3) -> AudioGenerationResult:
        """Generate audio using fallback chain for the given category.

        Tries each available provider in the chain until one succeeds.
        """
        chain = self.CHAINS.get(config.category, self.CHAINS["sfx"])
        available = [p for p in chain if self._is_available(p)]

        if not available:
            raise RuntimeError(
                f"No providers available for category '{config.category}'. "
                f"Configure at least one of: "
                f"{', '.join(self.REQUIRED_ENV[p] for p in chain if self.REQUIRED_ENV.get(p))}"
            )

        errors = []
        for provider_name in available[:max_attempts]:
            try:
                provider = self.PROVIDERS[provider_name]()
                print(f"[fallback] Trying {provider_name}...")
                result = provider.generate(config)
                if result.status == "succeeded":
                    print(f"[fallback] Success with {provider_name}")
                    return result
            except Exception as e:
                print(f"[fallback] {provider_name} failed: {e}")
                errors.append((provider_name, str(e)))
                continue

        error_summary = "; ".join(f"{p}: {e}" for p, e in errors)
        raise RuntimeError(f"All providers failed for '{config.category}': {error_summary}")


# --- Usage Example ---

def generate_with_fallback(prompt: str, category: str = "sfx",
                            duration: float = 5.0,
                            output_path: str = "output.wav") -> Path:
    """Generate audio with automatic provider fallback.

    Example:
        # Will try ElevenLabs SFX -> Stable Audio -> Freesound
        generate_with_fallback(
            prompt="magical spell casting with sparkle sounds",
            category="sfx",
            output_path="spell_cast.wav",
        )

        # Will try Stable Audio -> MusicGen -> Freesound
        generate_with_fallback(
            prompt="tense horror ambient with low drone",
            category="ambient",
            duration=30.0,
            output_path="horror_ambient.wav",
        )
    """
    chain = AudioFallbackChain()
    config = AudioGenerationConfig(
        prompt=prompt,
        category=category,
        duration_seconds=duration,
    )
    result = chain.generate(config)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if result.audio_bytes:
        path.write_bytes(result.audio_bytes)
    elif result.audio_url:
        resp = httpx.get(result.audio_url, timeout=120.0, follow_redirects=True)
        resp.raise_for_status()
        path.write_bytes(resp.content)

    return path
```

---

## Batch Generation Pattern

Generate multiple audio variations or an entire soundbank in one pass:

```python
import os
import time
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BatchItem:
    """Single item in a batch generation request."""
    name: str          # Output filename (without extension)
    prompt: str
    category: str = "sfx"
    duration: float = 5.0
    provider: str = ""  # Empty = use fallback chain


@dataclass
class BatchResult:
    """Result of a batch generation."""
    name: str
    filepath: str
    provider: str
    status: str  # "succeeded" | "failed"
    error: str = ""
    cost: float = 0.0


def generate_batch(items: list[BatchItem], output_dir: str,
                   max_workers: int = 3,
                   fallback: bool = True) -> list[BatchResult]:
    """Generate multiple audio files in parallel.

    Args:
        items: List of BatchItem describing each sound to generate
        output_dir: Directory for output files
        max_workers: Max concurrent API calls (respect rate limits)
        fallback: Use fallback chain on failure

    Example:
        items = [
            BatchItem("sword_hit_1", "metal sword hitting armor", "sfx", 1.0),
            BatchItem("sword_hit_2", "metal sword hitting stone", "sfx", 1.0),
            BatchItem("sword_hit_3", "metal sword hitting wood", "sfx", 1.0),
            BatchItem("footstep_grass", "footstep on grass outdoor", "sfx", 0.5),
            BatchItem("footstep_stone", "footstep on stone indoor", "sfx", 0.5),
            BatchItem("door_open", "heavy wooden door opening", "sfx", 2.0),
            BatchItem("ambient_cave", "dark cave with water dripping", "ambient", 30.0),
            BatchItem("battle_bgm", "intense battle music orchestral", "bgm", 30.0),
        ]
        results = generate_batch(items, "./game_audio/")
        for r in results:
            print(f"  {r.name}: {r.status} -> {r.filepath} (${r.cost:.2f})")
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    chain = AudioFallbackChain() if fallback else None
    results = []

    def process_item(item: BatchItem) -> BatchResult:
        try:
            config = AudioGenerationConfig(
                prompt=item.prompt,
                category=item.category,
                duration_seconds=item.duration,
            )

            if chain:
                result = chain.generate(config)
            else:
                provider = AudioFallbackChain.PROVIDERS[item.provider]()
                result = provider.generate(config)

            ext = result.format or "wav"
            filepath = output_path / f"{item.name}.{ext}"
            if result.audio_bytes:
                filepath.write_bytes(result.audio_bytes)
            elif result.audio_url:
                resp = httpx.get(result.audio_url, timeout=120.0, follow_redirects=True)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)

            return BatchResult(
                name=item.name,
                filepath=str(filepath),
                provider=result.provider,
                status="succeeded",
                cost=AudioFallbackChain.PROVIDERS.get(
                    result.provider, lambda: None
                )
                if False else 0.0,  # Cost tracked separately
            )

        except Exception as e:
            return BatchResult(
                name=item.name,
                filepath="",
                provider=item.provider,
                status="failed",
                error=str(e),
            )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_item, item): item for item in items}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status_icon = "OK" if result.status == "succeeded" else "FAIL"
            print(f"  [{status_icon}] {result.name}: {result.provider}")

    return sorted(results, key=lambda r: r.name)
```

---

## Cost Estimation Utility

Estimate total costs before running a batch generation:

```python
import os
from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Estimated cost for a generation request."""
    provider: str
    category: str
    estimated_usd: float
    unit: str  # "per generation", "per 1K chars", etc.
    notes: str = ""


# Cost rates per provider (check current pricing - these are approximate)
COST_TABLE = {
    "elevenlabs_sfx": {
        "rate": 0.08,
        "unit": "per generation",
        "notes": "Flat rate regardless of duration",
    },
    "elevenlabs_tts": {
        "rate": 0.30,
        "unit": "per 1K characters",
        "notes": "Shared quota with SFX",
    },
    "stable_audio": {
        "rate_short": 0.03,   # <= 10s
        "rate_medium": 0.06,  # 10-30s
        "rate_long": 0.10,    # > 30s
        "unit": "per generation (duration-based)",
        "notes": "Replicate compute pricing, may vary",
    },
    "musicgen": {
        "rate_small": 0.02,
        "rate_medium": 0.04,
        "rate_large": 0.08,
        "unit": "per generation (model-size-based)",
        "notes": "CC-BY-NC training data - check commercial license",
    },
    "openai_tts": {
        "rate_standard": 15.00,  # per 1M chars
        "rate_hd": 30.00,        # per 1M chars
        "unit": "per 1M characters",
        "notes": "tts-1 vs tts-1-hd",
    },
    "google_tts": {
        "rate_standard": 4.00,   # per 1M chars
        "rate_wavenet": 16.00,   # per 1M chars
        "rate_neural2": 16.00,   # per 1M chars
        "rate_studio": 16.00,    # per 1M chars (varies)
        "unit": "per 1M characters",
        "notes": "Voice tier affects pricing",
    },
    "bark": {
        "rate": 0.03,
        "unit": "per generation",
        "notes": "Replicate compute pricing",
    },
    "jsfxr": {
        "rate": 0.0,
        "unit": "free",
        "notes": "Local generation, no API calls",
    },
    "freesound": {
        "rate": 0.0,
        "unit": "free",
        "notes": "Check per-sound license for commercial use",
    },
}


def estimate_cost(items: list[BatchItem],
                  default_provider: str = "") -> dict:
    """Estimate total cost for a batch of audio generation items.

    Args:
        items: List of BatchItem with category, prompt, duration
        default_provider: Provider to use for cost calculation
                         (empty = use first in fallback chain)

    Returns:
        Dict with per-item estimates, total, and breakdown by provider.

    Example:
        items = [
            BatchItem("sfx_1", "explosion", "sfx", 2.0),
            BatchItem("sfx_2", "gunshot", "sfx", 1.0),
            BatchItem("bgm_1", "battle music", "bgm", 30.0),
            BatchItem("voice_1", "Hello adventurer, welcome!", "voice", 0),
            BatchItem("voice_2", "The dragon is approaching the castle gates.", "voice", 0),
        ]
        cost = estimate_cost(items)
        print(f"Total estimated cost: ${cost['total_usd']:.2f}")
        for item_name, est in cost['items'].items():
            print(f"  {item_name}: ${est['usd']:.4f} ({est['provider']})")
    """
    # Map category to default provider
    category_providers = {
        "sfx": "elevenlabs_sfx",
        "bgm": "stable_audio",
        "voice": "elevenlabs_tts",
        "ambient": "stable_audio",
        "ui": "jsfxr",
    }

    item_estimates = {}
    provider_totals = {}
    total = 0.0

    for item in items:
        provider = default_provider or category_providers.get(item.category, "elevenlabs_sfx")
        cost_info = COST_TABLE.get(provider, {})

        if provider == "elevenlabs_sfx":
            cost = cost_info.get("rate", 0.08)
        elif provider == "elevenlabs_tts":
            chars = len(item.prompt)
            cost = (chars / 1000) * cost_info.get("rate", 0.30)
        elif provider == "stable_audio":
            if item.duration <= 10:
                cost = cost_info.get("rate_short", 0.03)
            elif item.duration <= 30:
                cost = cost_info.get("rate_medium", 0.06)
            else:
                cost = cost_info.get("rate_long", 0.10)
        elif provider == "musicgen":
            cost = cost_info.get("rate_medium", 0.04)
        elif provider == "openai_tts":
            chars = len(item.prompt)
            cost = (chars / 1_000_000) * cost_info.get("rate_standard", 15.0)
        elif provider == "google_tts":
            chars = len(item.prompt)
            cost = (chars / 1_000_000) * cost_info.get("rate_neural2", 16.0)
        elif provider == "bark":
            cost = cost_info.get("rate", 0.03)
        else:
            cost = 0.0

        item_estimates[item.name] = {
            "provider": provider,
            "usd": cost,
            "notes": cost_info.get("notes", ""),
        }

        provider_totals[provider] = provider_totals.get(provider, 0.0) + cost
        total += cost

    return {
        "total_usd": total,
        "items": item_estimates,
        "by_provider": provider_totals,
        "item_count": len(items),
        "disclaimer": "Estimates are approximate. Check provider pricing pages for current rates.",
    }


def print_cost_report(items: list[BatchItem]) -> None:
    """Print a formatted cost report for a batch.

    Example:
        items = [
            BatchItem("hit_1", "sword hitting metal", "sfx", 1.0),
            BatchItem("hit_2", "sword hitting wood", "sfx", 1.0),
            BatchItem("bgm", "epic battle orchestral", "bgm", 30.0),
            BatchItem("npc_hello", "Greetings traveler!", "voice"),
        ]
        print_cost_report(items)

    Output:
        === Audio Generation Cost Estimate ===
        Items: 4
        ------------------------------------------
        hit_1          elevenlabs_sfx    $0.0800
        hit_2          elevenlabs_sfx    $0.0800
        bgm            stable_audio      $0.0600
        npc_hello      elevenlabs_tts    $0.0057
        ------------------------------------------
        By Provider:
          elevenlabs_sfx:  $0.1600 (2 items)
          stable_audio:    $0.0600 (1 items)
          elevenlabs_tts:  $0.0057 (1 items)
        ------------------------------------------
        TOTAL: $0.2257
        * Estimates are approximate. Check provider pricing for current rates.
    """
    report = estimate_cost(items)
    print("=== Audio Generation Cost Estimate ===")
    print(f"Items: {report['item_count']}")
    print("-" * 42)

    for name, est in report["items"].items():
        print(f"  {name:<20s} {est['provider']:<20s} ${est['usd']:.4f}")

    print("-" * 42)
    print("By Provider:")
    for provider, total in report["by_provider"].items():
        count = sum(1 for e in report["items"].values() if e["provider"] == provider)
        print(f"  {provider:<20s} ${total:.4f} ({count} items)")

    print("-" * 42)
    print(f"TOTAL: ${report['total_usd']:.4f}")
    print(f"* {report['disclaimer']}")
```

---

## Replicate Async Polling Pattern

Shared polling pattern for all Replicate-based providers (Stable Audio, MusicGen, Bark):

```python
import time
import httpx
from typing import Optional


def replicate_submit_and_poll(
    api_token: str,
    model: str,
    input_params: dict,
    interval: int = 3,
    max_wait: int = 300,
    version: Optional[str] = None,
) -> dict:
    """Submit a prediction to Replicate and poll until complete.

    Shared utility for Stable Audio, MusicGen, Bark, and any
    future Replicate-hosted audio model.

    Args:
        api_token: Replicate API token
        model: Model identifier (e.g. "stability-ai/stable-audio")
        input_params: Model-specific input parameters
        interval: Initial polling interval in seconds
        max_wait: Maximum wait time in seconds
        version: Specific model version (optional)

    Returns:
        Raw prediction response dict with output URL(s).

    Raises:
        RuntimeError: If prediction fails
        TimeoutError: If prediction exceeds max_wait
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    base_url = "https://api.replicate.com/v1"

    # Submit prediction
    payload = {"input": input_params}
    if version:
        payload["version"] = version

    resp = httpx.post(
        f"{base_url}/models/{model}/predictions",
        headers=headers,
        json=payload,
        timeout=30.0,
    )
    # Fallback to /predictions endpoint if model endpoint not available
    if resp.status_code == 404:
        payload["model"] = model
        resp = httpx.post(
            f"{base_url}/predictions",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
    resp.raise_for_status()
    prediction = resp.json()
    prediction_id = prediction["id"]

    # Poll for completion
    elapsed = 0
    current_interval = interval
    while elapsed < max_wait:
        poll_resp = httpx.get(
            f"{base_url}/predictions/{prediction_id}",
            headers=headers,
            timeout=30.0,
        )
        poll_resp.raise_for_status()
        data = poll_resp.json()

        if data["status"] == "succeeded":
            return data
        if data["status"] in ("failed", "canceled"):
            raise RuntimeError(
                f"Prediction {prediction_id} {data['status']}: "
                f"{data.get('error', 'unknown error')}"
            )

        print(f"[replicate/{model}] {prediction_id}: {data['status']} "
              f"elapsed={elapsed}s")
        time.sleep(current_interval)
        elapsed += current_interval
        current_interval = min(current_interval * 1.5, 15)

    raise TimeoutError(
        f"Prediction {prediction_id} timed out after {max_wait}s"
    )


# --- Usage Examples ---

def replicate_stable_audio(prompt: str, duration: float = 10.0) -> str:
    """Quick helper for Stable Audio via Replicate."""
    token = os.environ["REPLICATE_API_TOKEN"]
    result = replicate_submit_and_poll(
        api_token=token,
        model="stability-ai/stable-audio",
        input_params={
            "prompt": prompt,
            "seconds_total": duration,
            "steps": 100,
            "cfg_scale": 7.0,
        },
    )
    output = result["output"]
    return output[0] if isinstance(output, list) else output


def replicate_musicgen(prompt: str, duration: float = 15.0,
                       model_version: str = "medium") -> str:
    """Quick helper for MusicGen via Replicate."""
    token = os.environ["REPLICATE_API_TOKEN"]
    result = replicate_submit_and_poll(
        api_token=token,
        model="meta/musicgen",
        input_params={
            "prompt": prompt,
            "duration": duration,
            "model_version": model_version,
            "output_format": "wav",
        },
    )
    output = result["output"]
    return output[0] if isinstance(output, list) else output


def replicate_bark(prompt: str, speaker: str = "v2/en_speaker_5") -> str:
    """Quick helper for Bark via Replicate."""
    token = os.environ["REPLICATE_API_TOKEN"]
    result = replicate_submit_and_poll(
        api_token=token,
        model="suno-ai/bark",
        input_params={
            "prompt": prompt,
            "text_temp": 0.7,
            "waveform_temp": 0.7,
            "history_prompt": speaker,
        },
    )
    output = result["output"]
    if isinstance(output, dict):
        return output.get("audio_out", "")
    return output[0] if isinstance(output, list) else output
```

---

## Game Audio Category Guide

Quick reference for choosing the right provider per audio category:

| Game Audio Need | Recommended Provider | Fallback | Notes |
|----------------|---------------------|----------|-------|
| UI click/hover | JSFXR | ElevenLabs SFX | JSFXR for retro, ElevenLabs for realistic |
| Weapon SFX | ElevenLabs SFX | Freesound | Layer multiple for richness |
| Footsteps | Freesound | ElevenLabs SFX | Freesound has large footstep libraries |
| Explosions | ElevenLabs SFX | Stable Audio | Combine with screen shake |
| NPC dialogue | ElevenLabs TTS | OpenAI TTS | ElevenLabs for expressiveness |
| Narrator/cutscene | OpenAI TTS (HD) | ElevenLabs TTS | OpenAI HD for consistency |
| Tutorial voice | OpenAI TTS | Google TTS | Clear, neutral voices |
| Character emotes | Bark | ElevenLabs TTS | Bark for non-speech sounds |
| Battle BGM | Stable Audio | Suno AI, MusicGen | Stable Audio for quality, Suno for structured arrangement |
| Menu music | MusicGen | Suno AI, Stable Audio | MusicGen for melody, Suno for full arrangement |
| Game theme song | Suno AI | Stable Audio | Suno for structured BGM with intro/verse/chorus |
| Ambient loops | Stable Audio | Freesound | Stable Audio for custom, Freesound for natural |
| Horror atmosphere | Bark + Stable Audio | Freesound | Layer Bark whispers with Stable Audio drones |
| Retro/chiptune SFX | JSFXR | N/A | Only option for authentic 8-bit sounds |
| Notification sounds | JSFXR | ElevenLabs SFX | JSFXR for simple tones |

# Anti-Patterns Reference

Common pitfalls in AI game audio generation workflows and how to avoid them.

## Ship Unprocessed Audio

**Problem**: Raw AI-generated audio almost always contains artifacts, inconsistent volume levels, silence padding, and other issues that make it unsuitable for direct use in games. Shipping unprocessed output leads to ear fatigue, immersion breaks, and unprofessional audio quality.

**Symptoms**:
- Volume spikes or sudden loudness changes.
- Clicks, pops, and digital artifacts.
- Long silence at the start or end of audio files.
- Ear fatigue during extended play sessions.
- Inconsistent perceived loudness across assets.

**Fix**: Always apply a post-processing pipeline: normalize LUFS, trim silence, and apply fade in/out to every generated asset.

```python
# WRONG: Generate and use directly
audio = generate_sfx(prompt="sword slash")
export_audio(audio, "sword_slash.wav")

# RIGHT: Generate, process, then use
audio = generate_sfx(prompt="sword slash")
audio = trim_silence(audio, threshold_db=-40)
audio = normalize_lufs(audio, target=-23)
audio = apply_fade(audio, fade_in_ms=5, fade_out_ms=10)
export_audio(audio, "sword_slash.wav")
```

## Single Variation Trap

**Problem**: Using a single sound for events that fire repeatedly. The human ear is extremely sensitive to repetition, and hearing the same exact sound more than twice in quick succession breaks immersion and becomes annoying.

**Symptoms**:
- "Machine gun effect" on footsteps (same clip repeating rapidly).
- Repetitive UI click sounds that players describe as "annoying."
- Player complaints about sound monotony.
- Audio feels robotic or artificial.

**Fix**: Generate a minimum of 3 variations for any sound that plays more than once. Use round-robin or random-no-repeat playback to avoid consecutive duplicates.

```python
# WRONG: Single sound for repeated event
footstep = generate_sfx("footstep on gravel")
export_audio(footstep, "footstep_gravel.wav")

# RIGHT: Multiple variations with naming convention
for i in range(5):
    footstep = generate_sfx(
        f"footstep on gravel, variation {i+1}",
        seed=base_seed + i,
    )
    footstep = post_process(footstep)
    export_audio(footstep, f"footstep_gravel_{i:02d}.wav")
```

In the game engine, use a randomized playback strategy:

```gdscript
# Godot example - random no-repeat
var last_index := -1

func play_footstep():
    var index = randi() % footstep_variants.size()
    while index == last_index and footstep_variants.size() > 1:
        index = randi() % footstep_variants.size()
    last_index = index
    audio_player.stream = footstep_variants[index]
    audio_player.pitch_scale = randf_range(0.95, 1.05)  # Subtle pitch variation
    audio_player.play()
```

## Seamless Loop Failure

**Problem**: Audio loops that click or pop at the loop boundary due to waveform discontinuity. When the end sample value does not match the start sample value, the sudden jump creates an audible artifact.

**Symptoms**:
- Audible click at the loop point.
- "Thumping" sound on ambient loops every N seconds.
- BGM has a glitch at a regular interval matching the loop length.
- Players notice a rhythmic pop in otherwise smooth background audio.

**Fix**: Ensure zero-crossing alignment at loop boundaries. Apply crossfade overlap between the end and start of the loop.

```python
import numpy as np

# WRONG: Trim to length and export
loop = audio[:sample_rate * 4]  # 4-second loop
export_audio(loop, "ambient_loop.wav")

# RIGHT: Crossfade loop boundaries for seamless playback
def make_seamless_loop(audio, loop_duration_s, crossfade_ms=50):
    sr = audio.sample_rate
    crossfade_samples = int(sr * crossfade_ms / 1000)
    loop_samples = int(sr * loop_duration_s) + crossfade_samples

    segment = audio[:loop_samples]
    fade_out = np.linspace(1.0, 0.0, crossfade_samples)
    fade_in = np.linspace(0.0, 1.0, crossfade_samples)

    # Overlap-add: blend end into start
    result = segment[:int(sr * loop_duration_s)]
    result[:crossfade_samples] = (
        result[:crossfade_samples] * fade_in
        + segment[-crossfade_samples:] * fade_out
    )
    return result

loop = make_seamless_loop(audio, loop_duration_s=4.0, crossfade_ms=50)
export_audio(loop, "ambient_loop.wav")
```

## Wrong Format for Platform

**Problem**: Choosing the wrong audio format for the target platform causes bloated app size, playback failures, or compatibility issues. WAV on mobile wastes storage. MP3 on web without OGG fallback fails on some browsers.

**Symptoms**:
- App size 10x larger than expected (WAV files on mobile).
- Playback failures on specific browsers or platforms.
- Loading time spikes due to large uncompressed files.
- Silent audio on Safari (MP3-only without AAC/OGG fallback).

**Fix**: Choose format based on platform. Keep WAV as master/archive format, and convert to compressed formats for runtime.

```python
# WRONG: Ship WAV everywhere
export_audio(audio, "bgm.wav")  # 50MB for a 3-minute track

# RIGHT: Platform-appropriate formats
def export_for_platform(audio, name, platform):
    # Always keep master WAV
    export_audio(audio, f"master/{name}.wav", format="wav", sample_rate=48000)

    if platform == "desktop":
        export_audio(audio, f"build/{name}.ogg", format="ogg", quality=6)
    elif platform == "mobile":
        export_audio(audio, f"build/{name}.ogg", format="ogg", quality=4)
        # AAC for iOS fallback
        export_audio(audio, f"build/{name}.m4a", format="aac", bitrate="128k")
    elif platform == "web":
        # Dual format for browser compatibility
        export_audio(audio, f"build/{name}.ogg", format="ogg", quality=6)
        export_audio(audio, f"build/{name}.mp3", format="mp3", bitrate="192k")
```

| Format | Use Case | File Size (1 min) | Browser Support | Notes |
|--------|----------|-------------------|-----------------|-------|
| WAV | Master/archive | ~10 MB | All | Uncompressed, lossless |
| OGG Vorbis | Runtime (desktop/mobile/web) | ~1 MB | Chrome, Firefox, Edge | Best general-purpose |
| MP3 | Web fallback | ~1.5 MB | All | Patent-free since 2017 |
| AAC/M4A | iOS runtime | ~1 MB | Safari, iOS | Required for iOS WebAudio |
| OPUS | Voice/streaming | ~0.5 MB | Modern browsers | Best compression ratio |

## Skip Legal Review

**Problem**: Using audio generated from unknown or unlicensed training data creates legal risk. AI audio generation is a rapidly evolving legal landscape, and unclear provenance can lead to takedowns, store rejections, or lawsuits.

**Symptoms**:
- DMCA takedown notices.
- App store rejection citing unclear audio licensing.
- Lawsuit from rights holders.
- Unclear attribution chain making legal defense difficult.

**Fix**: Default to models trained on licensed data. Maintain an audio asset license registry for every asset in the project.

```python
# WRONG: Use any model without checking license
audio = unknown_model.generate("epic orchestral battle theme")
# No record of provenance, no license check

# RIGHT: Track provenance and license for every asset
asset_metadata = {
    "file": "battle_theme_01.ogg",
    "generator": "stable-audio-open",
    "model_license": "Stability Community License",
    "commercial_use": True,
    "training_data": "licensed/public-domain",
    "generation_date": "2026-03-08",
    "prompt": "epic orchestral battle theme, 120 BPM",
    "reviewed": True,
}
save_asset_registry(asset_metadata)
```

Recommended providers by license clarity:
- **ElevenLabs Sound Effects**: Commercial license included with subscription.
- **Stable Audio Open**: Open-weight, check specific license terms for commercial use.
- **Freesound.org**: Per-clip Creative Commons license (CC0, CC-BY, CC-BY-NC). Always check individual clip terms.
- **JSFXR/SFXR**: Generated from synthesis, no copyright concern.

## Ignore LUFS

**Problem**: Each audio asset generated at a different loudness level results in an inconsistent mix. Players experience ear fatigue and constantly adjust volume controls. BGM drowns out dialogue, or SFX are barely audible.

**Symptoms**:
- BGM drowns out dialogue or SFX.
- SFX barely audible against background music.
- UI sounds jarringly loud compared to gameplay audio.
- Players constantly adjusting volume sliders.
- Audio mix sounds amateur or unpolished.

**Fix**: Normalize all assets to a standard loudness target (EBU R128: -23 LUFS for broadcast, or -16 LUFS for streaming). Apply category-based mix offsets on top.

```python
import pyloudnorm as meter

# WRONG: Export at whatever level the AI produced
export_audio(bgm, "bgm.wav")
export_audio(sfx, "sfx.wav")
export_audio(ui, "ui.wav")

# RIGHT: Normalize to standard, then apply category offsets
CATEGORY_OFFSETS = {
    "bgm": -23,       # Background music baseline
    "sfx": -20,       # SFX slightly above BGM
    "dialogue": -18,  # Dialogue most prominent
    "ui": -26,        # UI sounds subtle
    "ambient": -28,   # Ambient very quiet
}

def normalize_for_category(audio, category, sr=48000):
    m = meter.Meter(sr)
    current_lufs = m.integrated_loudness(audio)
    target = CATEGORY_OFFSETS[category]
    gain_db = target - current_lufs
    return audio * (10 ** (gain_db / 20))

bgm = normalize_for_category(bgm_raw, "bgm")
sfx = normalize_for_category(sfx_raw, "sfx")
```

## Hardcode Paths and Keys

**Problem**: Embedding API keys directly in source code or using absolute file paths creates security risks and breaks portability. Leaked keys on GitHub lead to unauthorized API usage and billing surprises.

**Symptoms**:
- API keys exposed in Git history or public repositories.
- Scripts fail on other machines due to hardcoded absolute paths.
- CI/CD pipeline failures from environment-specific paths.
- Unexpected API bills from leaked credentials.

**Fix**: Use environment variables for API keys and relative or configurable paths for file references.

```python
# WRONG: Hardcoded keys and paths
API_KEY = "sk-abc123secretkey"
OUTPUT_DIR = "/Users/john/projects/game/audio/"

# RIGHT: Environment variables and configurable paths
import os
from pathlib import Path

API_KEY = os.environ["AUDIO_API_KEY"]  # Fails loudly if missing
OUTPUT_DIR = Path(os.environ.get(
    "AUDIO_OUTPUT_DIR",
    Path.cwd() / "assets" / "audio"  # Sensible default
))
```

For team projects, use a `.env` file (excluded from version control):

```bash
# .env (in .gitignore)
AUDIO_API_KEY=sk-abc123secretkey
AUDIO_OUTPUT_DIR=./assets/audio
```

## Missing Fallback

**Problem**: Depending on a single audio generation provider means that any API outage, rate limit, or service change completely blocks the audio workflow. No fallback strategy results in silent failures and blocked production.

**Symptoms**:
- Generation script fails silently when primary API is down.
- Entire audio workflow blocked by a single provider outage.
- No placeholder audio for testing or development.
- Team idle waiting for API recovery.

**Fix**: Implement a fallback chain with multiple providers and include a placeholder audio strategy for development.

```python
# WRONG: Single provider, no fallback
def generate_sound(prompt):
    return elevenlabs_api.generate(prompt)  # Fails if ElevenLabs is down

# RIGHT: Fallback chain with placeholder strategy
PROVIDERS = [
    ElevenLabsProvider(),
    StableAudioProvider(),
    JsfxrProvider(),  # Procedural synthesis fallback (always available)
]

def generate_sound(prompt, category="sfx"):
    for provider in PROVIDERS:
        try:
            audio = provider.generate(prompt)
            if audio is not None:
                return audio
        except (APIError, TimeoutError) as e:
            log.warning(f"{provider.name} failed: {e}")
            continue

    # Final fallback: placeholder audio
    log.warning("All providers failed, using placeholder")
    return load_placeholder(category)

def load_placeholder(category):
    """Load a pre-made silent or beep placeholder by category."""
    placeholder_path = PLACEHOLDER_DIR / f"{category}_placeholder.wav"
    if placeholder_path.exists():
        return load_audio(placeholder_path)
    return generate_silence(duration_s=1.0)
```

## Overly Long Generation

**Problem**: Generating a 3-minute BGM track when a 30-second loop would serve the same purpose. Longer generation means higher API costs, longer wait times, potential quality degradation, and wasted storage.

**Symptoms**:
- High API costs for audio generation.
- Long generation wait times (minutes instead of seconds).
- Quality degradation in longer AI-generated outputs (repetition, drift).
- Excessive storage usage for audio assets.
- Most of the generated audio is never heard by players.

**Fix**: Match generation duration to actual gameplay need. Use short loops with crossfade for background music. Estimate cost before generation.

```python
# WRONG: Generate full-length track for a looping BGM
bgm = generate_music(
    prompt="calm forest ambience",
    duration_s=180,  # 3 minutes - expensive and unnecessary
)

# RIGHT: Generate short loop, estimate cost first
COST_PER_SECOND = 0.02  # Example rate
target_duration = 30  # 30-second loop is sufficient
estimated_cost = target_duration * COST_PER_SECOND
log.info(f"Estimated cost: ${estimated_cost:.2f}")

bgm = generate_music(
    prompt="calm forest ambience, seamless loop",
    duration_s=target_duration,
)
bgm = make_seamless_loop(bgm, loop_duration_s=30)
```

Duration guidelines by category:

| Category | Recommended Duration | Rationale |
|----------|---------------------|-----------|
| BGM loop | 15-60 seconds | Loops seamlessly, saves cost |
| Ambient loop | 10-30 seconds | Short, layered for variety |
| SFX | 0.1-3 seconds | One-shot, trimmed tight |
| UI sounds | 0.05-0.5 seconds | Instant feedback |
| Dialogue placeholder | Match script length | Full duration needed |
| Cinematic | Full duration | Non-looping, one-time play |

## Mono/Stereo Mismatch

**Problem**: Using stereo audio for 3D-spatialized sounds, or mono audio for music. Stereo files do not spatialize correctly in game engines because the engine cannot position two channels independently in 3D space. Mono BGM sounds thin and lacks stereo width.

**Symptoms**:
- 3D positional audio sounds wrong (comes from center instead of a direction).
- Stereo SFX do not respond to listener position in the game world.
- Mono background music sounds flat and lifeless.
- Audio engine warnings about stereo sources on 3D audio emitters.

**Fix**: Use mono for all 3D-spatialized sounds (SFX, ambient point sources). Use stereo for non-spatialized audio (BGM, UI, cinematics).

```python
# WRONG: Stereo SFX for 3D game
sfx = generate_sfx("gunshot", channels="stereo")
# This will not spatialize correctly in Unity/Unreal/Godot

# RIGHT: Match channel count to use case
CHANNEL_RULES = {
    "sfx_3d": "mono",       # 3D-positioned sounds
    "ambient_3d": "mono",   # Point-source ambient (e.g., campfire)
    "ambient_bed": "stereo", # Non-positioned ambient layer
    "bgm": "stereo",        # Background music
    "ui": "stereo",         # UI feedback (non-spatialized)
    "dialogue": "mono",     # Usually spatialized to character
    "cinematic": "stereo",  # Cutscene audio
}

def export_with_channels(audio, name, category):
    target_channels = CHANNEL_RULES.get(category, "mono")
    if target_channels == "mono" and audio.channels == 2:
        audio = mixdown_to_mono(audio)
    elif target_channels == "stereo" and audio.channels == 1:
        audio = mono_to_stereo(audio)  # Duplicate channel
    export_audio(audio, f"{name}.wav")
```

## Sample Rate Chaos

**Problem**: Mixing sample rates (44.1kHz, 48kHz, 96kHz) across audio assets forces the game engine to resample at runtime, wasting CPU and potentially introducing artifacts like pitch shifts or aliasing.

**Symptoms**:
- Subtle pitch shifts on some sounds (44.1kHz played as 48kHz or vice versa).
- Aliasing artifacts on resampled audio.
- Increased CPU usage from runtime sample rate conversion.
- Inconsistent audio quality across assets.

**Fix**: Standardize on a single sample rate for all project audio. 48kHz is the modern standard for games and video. Convert to 44.1kHz only for specific mobile targets if needed.

```python
# WRONG: Mixed sample rates across assets
sfx_44 = generate_sfx("explosion", sample_rate=44100)
bgm_48 = generate_music("battle theme", sample_rate=48000)
amb_96 = generate_ambient("rain", sample_rate=96000)
# Engine must resample everything at runtime

# RIGHT: Standardize to 48kHz for all assets
PROJECT_SAMPLE_RATE = 48000

def ensure_sample_rate(audio, target_sr=PROJECT_SAMPLE_RATE):
    if audio.sample_rate != target_sr:
        audio = resample(audio, target_sr)
    return audio

sfx = ensure_sample_rate(generate_sfx("explosion"))
bgm = ensure_sample_rate(generate_music("battle theme"))
amb = ensure_sample_rate(generate_ambient("rain"))
```

| Sample Rate | Use Case | Notes |
|-------------|----------|-------|
| 48000 Hz | Game/video standard | Default for all new projects |
| 44100 Hz | Legacy/CD standard | Only for mobile optimization |
| 96000 Hz | Production/mastering | Never ship to runtime |
| 22050 Hz | Low-quality mobile | Only for extreme size constraints |

## No Silence Trimming

**Problem**: AI-generated audio frequently contains 0.5 to 2 seconds of silence at the beginning and/or end of the file. This silence causes delayed playback, making sound effects feel laggy and causing desynchronization with animations.

**Symptoms**:
- Sound effects feel delayed or "laggy" when triggered.
- Animation and audio are out of sync.
- SFX play noticeably after the visual event.
- File sizes larger than necessary due to silence padding.
- Players perceive input lag due to audio delay.

**Fix**: Auto-trim silence below a threshold (typically -40dB) from both ends of every generated audio file. Preserve intentional attack characteristics.

```python
import numpy as np

# WRONG: Use AI output directly with leading silence
sfx = generate_sfx("button click")
export_audio(sfx, "button_click.wav")  # Has 0.8s silence at start

# RIGHT: Trim silence while preserving attack
def trim_silence(audio, threshold_db=-40, pad_ms=5):
    """Remove silence from start/end, keep small pad for natural attack."""
    threshold = 10 ** (threshold_db / 20)
    samples = np.abs(audio.data)

    # Find first and last samples above threshold
    above = np.where(samples > threshold)[0]
    if len(above) == 0:
        return audio  # All silence - return as-is

    start = max(0, above[0] - int(audio.sample_rate * pad_ms / 1000))
    end = min(len(samples), above[-1] + int(audio.sample_rate * pad_ms / 1000))

    return audio[start:end]

sfx = generate_sfx("button click")
sfx = trim_silence(sfx, threshold_db=-40, pad_ms=5)
export_audio(sfx, "button_click.wav")  # Plays instantly on trigger
```

The `pad_ms` parameter preserves a small buffer before the first audible sample to avoid cutting into the natural attack transient of the sound.

## Summary Table

| Anti-Pattern | Risk Level | Detection | Prevention |
|-------------|------------|-----------|------------|
| Ship Unprocessed Audio | High | Listen test, waveform inspection | Post-processing pipeline on all assets |
| Single Variation Trap | Medium | Playtest repetitive events | Generate 3+ variations minimum |
| Seamless Loop Failure | High | Loop playback test | Crossfade boundaries, zero-crossing check |
| Wrong Format for Platform | High | Build size audit, cross-browser test | Platform-specific export pipeline |
| Skip Legal Review | Critical | License audit | Licensed-data models, asset registry |
| Ignore LUFS | Medium | Loudness meter, A/B listen | Normalize to EBU R128, category offsets |
| Hardcode Paths and Keys | High | Code review, secret scanning | Environment variables, relative paths |
| Missing Fallback | Medium | Simulate provider outage | Fallback chain, placeholder strategy |
| Overly Long Generation | Low | Cost tracking, duration audit | Match duration to need, cost estimation |
| Mono/Stereo Mismatch | Medium | Engine spatialization test | Channel rules per audio category |
| Sample Rate Chaos | Medium | Asset audit script | Standardize on 48kHz project-wide |
| No Silence Trimming | High | Waveform inspection, latency test | Auto-trim pipeline on all generated assets |

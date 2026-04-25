# Audio Format Optimization Reference

Comprehensive guide for audio format selection, conversion, normalization,
and platform-specific optimization for game audio pipelines.

---

## 1. Master Format Strategy

### Golden Rule: Master First, Convert Later

All AI-generated audio should be saved as **master files** before any processing:

- **Master Format**: WAV 48kHz / 24-bit (PCM, uncompressed)
- **Runtime Formats**: Platform-specific conversions derived from masters
- **Never delete masters** after conversion -- they are your archive and source of truth

### Why 48kHz / 24-bit?

| Property     | Reason                                                    |
|--------------|-----------------------------------------------------------|
| 48kHz        | Industry standard for video/game audio (matches DAW default) |
| 24-bit       | 144 dB dynamic range -- headroom for processing without quantization noise |
| WAV (PCM)    | No generational loss -- can re-encode to any format indefinitely |
| Uncompressed | No decoding artifacts, no encoder quirks to worry about   |

### Directory Structure Convention

```
audio/
  masters/           # WAV 48kHz/24-bit -- NEVER delete these
    sfx/
    bgm/
    voice/
    ambient/
  runtime/
    desktop/          # OGG Vorbis high quality
    mobile/           # AAC or OGG medium quality
    web/              # MP3 + OGG dual format
  sprites/            # Web audio sprites
  manifests/          # JSON metadata for each build
```

### Naming Convention

```
<category>_<name>_<variant>_v<version>.wav

Examples:
  sfx_footstep_grass_v1.wav
  bgm_battle_intro_v2.wav
  amb_forest_rain_v1.wav
  ui_click_confirm_v1.wav
```

---

## 2. Format Comparison Table

| Format | Codec      | Lossy | Size vs WAV  | Browser         | Unity | UE5 | Godot | Best For                  |
|--------|------------|-------|--------------|-----------------|-------|-----|-------|---------------------------|
| WAV    | PCM        | No    | 1x (baseline)| Yes             | Yes   | Yes | Yes   | Master, desktop SFX       |
| OGG    | Vorbis     | Yes   | ~10-15x smaller | Chrome/FF    | Yes   | Yes | Yes   | Runtime SFX/BGM           |
| MP3    | MPEG-1 L3  | Yes   | ~10-12x smaller | All           | Yes   | Yes | Yes   | Web fallback              |
| AAC    | AAC-LC     | Yes   | ~12-15x smaller | Safari/Chrome | Yes   | Yes | No    | iOS/mobile                |
| OPUS   | Opus       | Yes   | ~15-20x smaller | Modern        | Plugin| No  | Yes   | VoIP, streaming           |
| FLAC   | FLAC       | No    | ~2-3x smaller  | Limited       | No    | No  | Yes   | Archival                  |

### Decision Flowchart

```
Need lossless archive?
  YES --> WAV (master) or FLAC (space-constrained archive)
  NO  --> What platform?
    Web         --> MP3 (universal) + OGG (preferred)
    iOS         --> AAC (native hardware decode)
    Android     --> OGG Vorbis (native support)
    Desktop     --> OGG Vorbis (best quality/size ratio)
    Console     --> Platform-native (check TRC/XR docs)
    VoIP/Stream --> OPUS (lowest latency, smallest size)
```

### Codec Quality Notes

- **OGG Vorbis**: Excellent at mid-bitrates (128-192kbps). No patent issues. Slight encoder
  latency (~20ms) acceptable for games. Best general-purpose lossy codec for games.
- **MP3**: Universal browser support but inferior quality at same bitrate vs OGG/AAC.
  Has mandatory encoder delay (~576-1152 samples). Use `--nogap` for gapless playback.
- **AAC**: Superior to MP3 at equivalent bitrates. Hardware decode on iOS saves battery.
  Requires `.m4a` container for best compatibility.
- **OPUS**: Best quality-per-bit of any lossy codec. Ideal for real-time voice and streaming.
  Limited game engine support currently.
- **FLAC**: Lossless but 2-3x smaller than WAV. Good for distribution when WAV is too large
  but lossy is unacceptable. Limited browser support.

---

## 3. ffmpeg Processing Scripts

All commands assume ffmpeg 5.0+ with standard codec libraries.

### 3.1 Format Conversion

#### WAV to OGG Vorbis

```bash
# Quality 6 = ~192kbps (recommended for game SFX)
ffmpeg -i input.wav -c:a libvorbis -q:a 6 output.ogg

# Quality 4 = ~128kbps (mobile / smaller footprint)
ffmpeg -i input.wav -c:a libvorbis -q:a 4 output.ogg

# Quality 8 = ~256kbps (high-quality BGM)
ffmpeg -i input.wav -c:a libvorbis -q:a 8 output.ogg
```

Vorbis quality scale reference:

| -q:a | Approximate Bitrate | Use Case            |
|------|---------------------|---------------------|
| 2    | ~96 kbps            | Low-quality / voice |
| 4    | ~128 kbps           | Mobile SFX          |
| 6    | ~192 kbps           | Desktop SFX         |
| 8    | ~256 kbps           | High-quality BGM    |
| 10   | ~500 kbps           | Near-transparent    |

#### WAV to MP3

```bash
# 192kbps CBR (constant bitrate -- predictable file size)
ffmpeg -i input.wav -c:a libmp3lame -b:a 192k output.mp3

# VBR quality 2 (~190kbps average -- better quality-per-bit)
ffmpeg -i input.wav -c:a libmp3lame -q:a 2 output.mp3

# 128kbps CBR (web / bandwidth-constrained)
ffmpeg -i input.wav -c:a libmp3lame -b:a 128k output.mp3
```

#### WAV to AAC

```bash
# 192kbps AAC-LC in M4A container (iOS recommended)
ffmpeg -i input.wav -c:a aac -b:a 192k output.m4a

# 128kbps for mobile (good quality on iOS hardware decoder)
ffmpeg -i input.wav -c:a aac -b:a 128k output.m4a

# High quality 256kbps
ffmpeg -i input.wav -c:a aac -b:a 256k -movflags +faststart output.m4a
```

#### WAV to OPUS

```bash
# 128kbps Opus (excellent quality at this bitrate)
ffmpeg -i input.wav -c:a libopus -b:a 128k output.opus

# 64kbps for voice / VoIP
ffmpeg -i input.wav -c:a libopus -b:a 64k -application voip output.opus

# 192kbps for music
ffmpeg -i input.wav -c:a libopus -b:a 192k -application audio output.opus
```

#### WAV to FLAC

```bash
# Default compression (level 5)
ffmpeg -i input.wav -c:a flac output.flac

# Maximum compression (slower encode, same decode speed)
ffmpeg -i input.wav -c:a flac -compression_level 12 output.flac
```

### 3.2 LUFS Normalization (Two-Pass loudnorm)

LUFS (Loudness Units Full Scale) normalization ensures consistent perceived loudness
across all audio assets. Two-pass is essential for accurate, linear normalization.

#### Common LUFS Targets

| Context         | Target LUFS | True Peak | LRA   |
|-----------------|-------------|-----------|-------|
| Game SFX        | -23 LUFS   | -1 dBTP   | 11 LU |
| Game BGM        | -23 LUFS   | -1 dBTP   | 11 LU |
| Dialogue        | -23 LUFS   | -1 dBTP   | 7 LU  |
| Mobile Game     | -16 LUFS   | -1 dBTP   | 8 LU  |
| Broadcast (EBU) | -23 LUFS   | -1 dBTP   | 11 LU |

#### Pass 1: Measure

```bash
ffmpeg -i input.wav \
  -af loudnorm=I=-23:TP=-1:LRA=11:print_format=json \
  -f null -
```

This outputs JSON with measured values:

```json
{
  "input_i" : "-27.32",
  "input_tp" : "-4.15",
  "input_lra" : "6.80",
  "input_thresh" : "-38.42",
  "output_i" : "-23.01",
  "output_tp" : "-1.00",
  "output_lra" : "5.90",
  "output_thresh" : "-33.81",
  "normalization_type" : "dynamic",
  "target_offset" : "-0.01"
}
```

#### Pass 2: Apply (Linear Mode)

Use the measured values from pass 1 to apply linear normalization:

```bash
ffmpeg -i input.wav -af loudnorm=I=-23:TP=-1:LRA=11:\
measured_I=-27.32:\
measured_LRA=6.80:\
measured_TP=-4.15:\
measured_thresh=-38.42:\
offset=-0.01:\
linear=true \
  output.wav
```

Key: `linear=true` preserves the original dynamics. Without it, ffmpeg applies
dynamic compression which can alter the character of the sound.

### 3.3 Trim Silence

```bash
# Remove silence from start and end (threshold: -40dB, min silence: 0.1s)
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-40dB,\
areverse,\
silenceremove=start_periods=1:start_silence=0.1:start_threshold=-40dB,\
areverse" \
  output.wav
```

The double-reverse trick: `silenceremove` only trims from the start, so we reverse
the audio, trim the (now leading) end silence, then reverse back.

```bash
# More aggressive trim (threshold: -30dB, useful for AI-generated audio with noise tails)
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-30dB,\
areverse,\
silenceremove=start_periods=1:start_silence=0.05:start_threshold=-30dB,\
areverse" \
  output.wav
```

### 3.4 Fade In / Fade Out

```bash
# 10ms fade in, 50ms fade out (for a 2-second clip)
ffmpeg -i input.wav \
  -af "afade=t=in:st=0:d=0.01,afade=t=out:st=1.95:d=0.05" \
  output.wav
```

```bash
# Automatic fade out using file duration (no hardcoded times)
# Get duration first, then apply
DURATION=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.wav)
FADE_OUT_START=$(echo "$DURATION - 0.05" | bc)
ffmpeg -i input.wav \
  -af "afade=t=in:st=0:d=0.01,afade=t=out:st=${FADE_OUT_START}:d=0.05" \
  output.wav
```

```bash
# Longer fades for BGM (500ms in, 2s out)
ffmpeg -i input.wav \
  -af "afade=t=in:st=0:d=0.5,afade=t=out:st=${FADE_OUT_START}:d=2.0" \
  output.wav
```

### 3.5 Stereo to Mono

```bash
# Downmix stereo to mono (averages both channels)
ffmpeg -i input.wav -ac 1 output_mono.wav

# Downmix with -3dB compensation to prevent clipping
ffmpeg -i input.wav -af "pan=mono|c0=0.5*c0+0.5*c1" output_mono.wav
```

Use mono for:
- 3D positional SFX (the engine handles spatialization)
- UI sounds (no spatial component)
- Mobile builds (saves 50% file size)

### 3.6 Sample Rate Conversion

```bash
# Resample to 44.1kHz (for mobile / web)
ffmpeg -i input.wav -ar 44100 output_44k.wav

# Resample to 22050Hz (for very small SFX, voice)
ffmpeg -i input.wav -ar 22050 output_22k.wav

# High-quality resampling with SoX resampler
ffmpeg -i input.wav -af aresample=44100:resampler=soxr:precision=28 output_44k.wav
```

### 3.7 Crossfade Loop Creation

Create a seamless loop from a non-looping audio file using crossfade:

```bash
# Create seamless loop with 2-second crossfade
# Input: a BGM track (e.g., 30 seconds)
# Output: a seamlessly looping version

CROSSFADE=2
DURATION=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.wav)
LOOP_LEN=$(echo "$DURATION - $CROSSFADE" | bc)

ffmpeg -i input.wav -filter_complex \
  "[0]atrim=0:${CROSSFADE},afade=t=in:d=${CROSSFADE}[head];
   [0]atrim=${LOOP_LEN}:${DURATION},afade=t=out:d=${CROSSFADE}[tail];
   [0]atrim=${CROSSFADE}:${LOOP_LEN}[body];
   [tail][head]amix=inputs=2:duration=longest[xfade];
   [body][xfade]concat=n=2:v=0:a=1[out]" \
  -map "[out]" output_loop.wav
```

Verify the loop by playing it twice back-to-back:

```bash
ffmpeg -stream_loop 1 -i output_loop.wav -c copy loop_test.wav
```

### 3.8 Batch Processing Script

```bash
#!/bin/bash
# batch_convert.sh -- Convert + normalize all WAV masters to platform formats
#
# Usage: ./batch_convert.sh <input_dir> <output_dir> [lufs_target]
#
# Example: ./batch_convert.sh masters/ runtime/ -23

set -euo pipefail

INPUT_DIR="${1:?Usage: $0 <input_dir> <output_dir> [lufs_target]}"
OUTPUT_DIR="${2:?Usage: $0 <input_dir> <output_dir> [lufs_target]}"
LUFS_TARGET="${3:--23}"

mkdir -p "$OUTPUT_DIR"/{normalized,ogg,mp3,aac}

for f in "$INPUT_DIR"/*.wav; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .wav)
  echo "Processing: $name"

  # --- Pass 1: Measure loudness ---
  LOUDNORM_JSON=$(ffmpeg -i "$f" \
    -af "loudnorm=I=${LUFS_TARGET}:TP=-1:LRA=11:print_format=json" \
    -f null - 2>&1 | tail -12)

  measured_I=$(echo "$LOUDNORM_JSON" | grep '"input_i"' | grep -o '[-0-9.]*')
  measured_LRA=$(echo "$LOUDNORM_JSON" | grep '"input_lra"' | grep -o '[-0-9.]*')
  measured_TP=$(echo "$LOUDNORM_JSON" | grep '"input_tp"' | grep -o '[-0-9.]*')
  measured_thresh=$(echo "$LOUDNORM_JSON" | grep '"input_thresh"' | grep -o '[-0-9.]*')
  offset=$(echo "$LOUDNORM_JSON" | grep '"target_offset"' | grep -o '[-0-9.]*')

  # --- Pass 2: Normalize ---
  ffmpeg -y -i "$f" \
    -af "loudnorm=I=${LUFS_TARGET}:TP=-1:LRA=11:\
measured_I=${measured_I}:measured_LRA=${measured_LRA}:\
measured_TP=${measured_TP}:measured_thresh=${measured_thresh}:\
offset=${offset}:linear=true" \
    "$OUTPUT_DIR/normalized/${name}.wav"

  NORM="$OUTPUT_DIR/normalized/${name}.wav"

  # --- Convert to platform formats ---
  # OGG Vorbis (desktop)
  ffmpeg -y -i "$NORM" -c:a libvorbis -q:a 6 "$OUTPUT_DIR/ogg/${name}.ogg"

  # MP3 (web fallback)
  ffmpeg -y -i "$NORM" -c:a libmp3lame -q:a 2 "$OUTPUT_DIR/mp3/${name}.mp3"

  # AAC (mobile)
  ffmpeg -y -i "$NORM" -c:a aac -b:a 128k "$OUTPUT_DIR/aac/${name}.m4a"

  echo "  Done: $name"
done

echo "Batch conversion complete. Output in: $OUTPUT_DIR"
```

---

## 4. Platform Optimization Profiles

### 4.1 Desktop (Windows / Mac / Linux)

| Parameter           | Recommendation                          |
|---------------------|-----------------------------------------|
| Format (SFX)        | OGG Vorbis q6 (~192kbps)               |
| Format (BGM)        | OGG Vorbis q6-q8 (streaming)           |
| Sample Rate         | 48kHz                                   |
| Channels            | Stereo for BGM, Mono for 3D SFX        |
| Bit Depth (master)  | 24-bit WAV                              |
| Total Audio Budget  | 500MB - 2GB                             |
| Simultaneous Voices | 32-128 depending on hardware            |
| Streaming           | BGM and ambient should stream from disk |

Tips:
- Preload short SFX into memory (< 1 second)
- Stream long BGM tracks (> 10 seconds)
- Use distance-based attenuation to cull inaudible sources
- Group similar sounds and use random selection to avoid repetition

### 4.2 Mobile (iOS / Android)

| Parameter           | Recommendation                      |
|---------------------|-------------------------------------|
| Format (iOS)        | AAC 128kbps in .m4a container       |
| Format (Android)    | OGG Vorbis q4 (~128kbps)           |
| Format (Cross-plat) | OGG Vorbis (works on both)          |
| Sample Rate         | 44.1kHz                             |
| Channels            | Mono preferred (saves 50% size)     |
| Total Audio Budget  | 50 - 200MB                          |
| Simultaneous Voices | 8-16 (reduce aggressively)          |
| Streaming           | Stream BGM only; preload all SFX    |

Tips:
- AAC uses hardware decoder on iOS, saving CPU and battery
- Reduce polyphony limits; mobile speakers do not reproduce complex mixes well
- Consider lower sample rates (22050Hz) for UI sounds and simple SFX
- Test on low-end devices (audio decode can spike CPU)
- Use audio focus / interruption handling for phone calls

### 4.3 Web (Browser)

| Parameter           | Recommendation                           |
|---------------------|------------------------------------------|
| Primary Format      | OGG Vorbis (Chrome, Firefox, Edge)       |
| Fallback Format     | MP3 (Safari, universal)                  |
| Sample Rate         | 44.1kHz                                  |
| Channels            | Stereo BGM, Mono SFX                     |
| Quality             | 128-192kbps                              |
| Total Audio Budget  | 20 - 50MB (initial load < 5MB)           |
| Simultaneous Voices | 8-16                                     |

Tips:
- Always provide dual format (OGG + MP3) for maximum browser coverage
- Use the Web Audio API for low-latency SFX playback
- Audio sprites reduce HTTP requests significantly (see Section 6)
- `<audio>` element for BGM streaming; Web Audio for interactive SFX
- Autoplay restrictions: always start audio from a user gesture
- Use `preload="none"` for BGM to avoid unnecessary bandwidth usage
- Consider progressive loading: load UI sounds first, BGM later

### 4.4 Console (PS5 / Xbox / Switch)

| Parameter           | Recommendation                              |
|---------------------|---------------------------------------------|
| Format (PS5)        | Opus or platform-native (Atrac9 legacy)     |
| Format (Xbox)       | XMA2 or Opus                                |
| Format (Switch)     | Opus or ADPCM                               |
| Sample Rate         | 48kHz                                       |
| Quality             | High (hardware decode available)            |
| Total Audio Budget  | 256MB - 1GB                                 |
| Simultaneous Voices | 64-256 (hardware-accelerated mixing)        |

Important notes:
- Check platform-specific TRC (Technical Requirements Checklist) / XR (Xbox Requirements)
- Consoles often have dedicated audio hardware with specific codec requirements
- Audio memory management is stricter; budget carefully
- Certification may require specific loudness standards (EBU R128 or ATSC A/85)
- Use platform SDKs for optimal decode performance

---

## 5. File Size Budget Calculator

### PCM (Uncompressed WAV) Size Formula

```
Size (bytes) = sample_rate x (bit_depth / 8) x channels x duration_seconds
Size (MB) = Size (bytes) / 1,048,576
```

### Quick Reference Table

Duration and format vs file size (approximate):

| Duration | WAV 48k/24/Stereo | WAV 48k/16/Mono | OGG 192kbps | MP3 192kbps | AAC 128kbps |
|----------|-------------------|------------------|-------------|-------------|-------------|
| 0.1s     | 28 KB             | 9.4 KB           | 2.4 KB      | 2.4 KB      | 1.6 KB      |
| 0.5s     | 140 KB            | 47 KB            | 12 KB       | 12 KB       | 8 KB        |
| 1s       | 281 KB            | 94 KB            | 24 KB       | 24 KB       | 16 KB       |
| 5s       | 1.4 MB            | 469 KB           | 120 KB      | 120 KB      | 80 KB       |
| 10s      | 2.8 MB            | 938 KB           | 240 KB      | 240 KB      | 160 KB      |
| 30s      | 8.4 MB            | 2.7 MB           | 720 KB      | 720 KB      | 480 KB      |
| 1 min    | 16.9 MB           | 5.5 MB           | 1.4 MB      | 1.4 MB      | 960 KB      |
| 3 min    | 50.6 MB           | 16.5 MB          | 4.2 MB      | 4.2 MB      | 2.8 MB      |
| 5 min    | 84.4 MB           | 27.5 MB          | 7.0 MB      | 7.0 MB      | 4.7 MB      |

### Budget Planning Example

A typical indie game audio budget:

| Category    | Count | Avg Duration | Format      | Size Each | Total     |
|-------------|-------|--------------|-------------|-----------|-----------|
| BGM tracks  | 15    | 3 min        | OGG q6      | 4.2 MB    | 63 MB     |
| SFX         | 200   | 0.5s         | OGG q6      | 12 KB     | 2.4 MB    |
| Ambient     | 10    | 2 min        | OGG q4      | 1.9 MB    | 19 MB     |
| UI sounds   | 50    | 0.2s         | OGG q4      | 5 KB      | 250 KB    |
| Voice lines | 100   | 3s           | OGG q4      | 48 KB     | 4.8 MB    |
| **Total**   |       |              |             |           | **~90 MB**|

---

## 6. Audio Sprite Creation for Web

### Concept

Audio sprites pack multiple short sounds into a single audio file. The player seeks
to the correct offset when playing a specific sound. This reduces HTTP requests from
potentially hundreds to just one or two files.

### When to Use Sprites

- Web games with many short UI/SFX sounds (< 2 seconds each)
- Reduces latency from network round-trips
- Not suitable for BGM or long ambient tracks

### Step 1: Prepare Individual Files

Ensure all source files have the same sample rate and channel count:

```bash
# Normalize all inputs to 44.1kHz mono
for f in sfx_sources/*.wav; do
  name=$(basename "$f")
  ffmpeg -y -i "$f" -ar 44100 -ac 1 "sfx_normalized/$name"
done
```

### Step 2: Concatenate with Silence Gaps

```bash
#!/bin/bash
# create_sprite.sh -- Build an audio sprite from individual WAV files
#
# Usage: ./create_sprite.sh <input_dir> <output_name>

set -euo pipefail

INPUT_DIR="${1:?Usage: $0 <input_dir> <output_name>}"
OUTPUT_NAME="${2:?Usage: $0 <input_dir> <output_name>}"
GAP_MS=100  # 100ms silence between sprites

# Generate silence gap
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t $(echo "$GAP_MS/1000" | bc -l) \
  -c:a pcm_s16le gap.wav

# Build concat list and track offsets
OFFSET=0
CONCAT_LIST=""
JSON="{\n  \"src\": [\"${OUTPUT_NAME}.ogg\", \"${OUTPUT_NAME}.mp3\"],\n  \"sprite\": {"
FIRST=true

for f in "$INPUT_DIR"/*.wav; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .wav)

  # Get duration in milliseconds
  DUR_S=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$f")
  DUR_MS=$(echo "$DUR_S * 1000" | bc | cut -d. -f1)

  # Add to JSON sprite map
  if [ "$FIRST" = true ]; then
    FIRST=false
  else
    JSON+=","
  fi
  JSON+="\n    \"${name}\": [${OFFSET}, ${DUR_MS}]"

  # Update offset (duration + gap)
  OFFSET=$((OFFSET + DUR_MS + GAP_MS))

  # Build concat list
  CONCAT_LIST+="file '$f'\nfile 'gap.wav'\n"
done

JSON+="\n  }\n}"

# Write concat file
echo -e "$CONCAT_LIST" > concat_list.txt

# Concatenate all files
ffmpeg -y -f concat -safe 0 -i concat_list.txt -c:a pcm_s16le "${OUTPUT_NAME}.wav"

# Export as OGG + MP3
ffmpeg -y -i "${OUTPUT_NAME}.wav" -c:a libvorbis -q:a 6 "${OUTPUT_NAME}.ogg"
ffmpeg -y -i "${OUTPUT_NAME}.wav" -c:a libmp3lame -q:a 2 "${OUTPUT_NAME}.mp3"

# Write sprite map JSON
echo -e "$JSON" > "${OUTPUT_NAME}.json"

# Cleanup
rm -f gap.wav concat_list.txt

echo "Sprite created: ${OUTPUT_NAME}.ogg, ${OUTPUT_NAME}.mp3"
echo "Sprite map: ${OUTPUT_NAME}.json"
```

### Step 3: Use with Howler.js

```javascript
// Load the sprite using Howler.js
const gameAudio = new Howl({
  src: ['sprites/ui_sounds.ogg', 'sprites/ui_sounds.mp3'],
  sprite: {
    click:    [0, 150],
    hover:    [250, 100],
    confirm:  [450, 300],
    cancel:   [850, 200],
    error:    [1150, 400],
    pickup:   [1650, 250],
    drop:     [2000, 200]
  }
});

// Play a specific sprite
gameAudio.play('click');
gameAudio.play('confirm');
```

### Sprite Best Practices

- Keep total sprite duration under 60 seconds
- Use 100ms silence gaps between sounds (prevents bleed during seek)
- Group sprites by usage context (UI, combat, ambient)
- Generate both OGG and MP3 for browser compatibility
- Regenerate sprites whenever source assets change

---

## 7. Complete Processing Pipeline Script

A comprehensive shell script that takes raw AI-generated WAV files through the full
optimization pipeline.

```bash
#!/bin/bash
# audio_pipeline.sh -- Complete audio processing pipeline for game assets
#
# Processes raw AI-generated WAV files through:
#   1. Silence trimming
#   2. LUFS normalization (two-pass)
#   3. Fade in/out
#   4. Multi-platform format conversion
#   5. Manifest JSON generation
#
# Usage: ./audio_pipeline.sh <input_dir> <output_dir> [options]
#
# Options:
#   --lufs TARGET      Target LUFS (default: -23)
#   --fade-in MS       Fade in duration in ms (default: 10)
#   --fade-out MS      Fade out duration in ms (default: 50)
#   --trim-threshold   Silence threshold in dB (default: -40)
#   --platforms LIST   Comma-separated: desktop,mobile,web (default: all)
#   --mono             Force mono output for SFX
#
# Example:
#   ./audio_pipeline.sh raw_audio/ processed/ --lufs -23 --platforms desktop,web

set -euo pipefail

# ============================================================
# Default Configuration
# ============================================================
LUFS_TARGET=-23
TRUE_PEAK=-1
LRA=11
FADE_IN_MS=10
FADE_OUT_MS=50
TRIM_THRESHOLD=-40
PLATFORMS="desktop,mobile,web"
FORCE_MONO=false

# ============================================================
# Parse Arguments
# ============================================================
INPUT_DIR=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --lufs)        LUFS_TARGET="$2"; shift 2 ;;
    --fade-in)     FADE_IN_MS="$2"; shift 2 ;;
    --fade-out)    FADE_OUT_MS="$2"; shift 2 ;;
    --trim-threshold) TRIM_THRESHOLD="$2"; shift 2 ;;
    --platforms)   PLATFORMS="$2"; shift 2 ;;
    --mono)        FORCE_MONO=true; shift ;;
    *)
      if [ -z "$INPUT_DIR" ]; then
        INPUT_DIR="$1"
      elif [ -z "$OUTPUT_DIR" ]; then
        OUTPUT_DIR="$1"
      fi
      shift ;;
  esac
done

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: $0 <input_dir> <output_dir> [options]"
  exit 1
fi

# ============================================================
# Setup Directories
# ============================================================
STAGE_DIR="$OUTPUT_DIR/.staging"
mkdir -p "$STAGE_DIR"/{trimmed,normalized,faded}
mkdir -p "$OUTPUT_DIR"/{master,desktop,mobile,web}

FADE_IN=$(echo "scale=4; $FADE_IN_MS / 1000" | bc)
FADE_OUT=$(echo "scale=4; $FADE_OUT_MS / 1000" | bc)

# Manifest data
MANIFEST_ENTRIES=""
PROCESSED=0
FAILED=0

echo "========================================"
echo "Audio Processing Pipeline"
echo "========================================"
echo "Input:       $INPUT_DIR"
echo "Output:      $OUTPUT_DIR"
echo "LUFS Target: $LUFS_TARGET"
echo "Platforms:   $PLATFORMS"
echo "Fade:        ${FADE_IN_MS}ms in / ${FADE_OUT_MS}ms out"
echo "Trim:        ${TRIM_THRESHOLD}dB threshold"
echo "========================================"

# ============================================================
# Process Each File
# ============================================================
for f in "$INPUT_DIR"/*.wav; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .wav)
  echo ""
  echo "--- Processing: $name ---"

  # --------------------------------------------------------
  # Step 1: Trim Silence
  # --------------------------------------------------------
  echo "  [1/4] Trimming silence..."
  ffmpeg -y -i "$f" \
    -af "silenceremove=start_periods=1:start_silence=0.05:start_threshold=${TRIM_THRESHOLD}dB,\
areverse,\
silenceremove=start_periods=1:start_silence=0.05:start_threshold=${TRIM_THRESHOLD}dB,\
areverse" \
    "$STAGE_DIR/trimmed/${name}.wav" 2>/dev/null

  # --------------------------------------------------------
  # Step 2: LUFS Normalization (two-pass)
  # --------------------------------------------------------
  echo "  [2/4] Normalizing to ${LUFS_TARGET} LUFS..."

  # Pass 1: Measure
  LOUDNORM_OUTPUT=$(ffmpeg -i "$STAGE_DIR/trimmed/${name}.wav" \
    -af "loudnorm=I=${LUFS_TARGET}:TP=${TRUE_PEAK}:LRA=${LRA}:print_format=json" \
    -f null - 2>&1)

  measured_I=$(echo "$LOUDNORM_OUTPUT" | grep '"input_i"' | grep -o '[-0-9.]*')
  measured_LRA=$(echo "$LOUDNORM_OUTPUT" | grep '"input_lra"' | grep -o '[-0-9.]*')
  measured_TP=$(echo "$LOUDNORM_OUTPUT" | grep '"input_tp"' | grep -o '[-0-9.]*')
  measured_thresh=$(echo "$LOUDNORM_OUTPUT" | grep '"input_thresh"' | grep -o '[-0-9.]*')
  offset=$(echo "$LOUDNORM_OUTPUT" | grep '"target_offset"' | grep -o '[-0-9.]*')

  if [ -z "$measured_I" ]; then
    echo "  WARNING: Could not measure loudness for $name, skipping."
    FAILED=$((FAILED + 1))
    continue
  fi

  # Pass 2: Apply
  ffmpeg -y -i "$STAGE_DIR/trimmed/${name}.wav" \
    -af "loudnorm=I=${LUFS_TARGET}:TP=${TRUE_PEAK}:LRA=${LRA}:\
measured_I=${measured_I}:measured_LRA=${measured_LRA}:\
measured_TP=${measured_TP}:measured_thresh=${measured_thresh}:\
offset=${offset}:linear=true" \
    "$STAGE_DIR/normalized/${name}.wav" 2>/dev/null

  # --------------------------------------------------------
  # Step 3: Apply Fade In/Out
  # --------------------------------------------------------
  echo "  [3/4] Applying fades..."
  DURATION=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$STAGE_DIR/normalized/${name}.wav")
  FADE_OUT_START=$(echo "$DURATION - $FADE_OUT" | bc)

  MONO_FILTER=""
  if [ "$FORCE_MONO" = true ]; then
    MONO_FILTER=",pan=mono|c0=0.5*c0+0.5*c1"
  fi

  ffmpeg -y -i "$STAGE_DIR/normalized/${name}.wav" \
    -af "afade=t=in:st=0:d=${FADE_IN},afade=t=out:st=${FADE_OUT_START}:d=${FADE_OUT}${MONO_FILTER}" \
    "$STAGE_DIR/faded/${name}.wav" 2>/dev/null

  PROCESSED_WAV="$STAGE_DIR/faded/${name}.wav"

  # Copy master
  cp "$PROCESSED_WAV" "$OUTPUT_DIR/master/${name}.wav"

  # --------------------------------------------------------
  # Step 4: Platform Conversions
  # --------------------------------------------------------
  echo "  [4/4] Converting to platform formats..."

  # Get final file info for manifest
  FINAL_DURATION=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$PROCESSED_WAV")
  FINAL_RATE=$(ffprobe -v error -select_streams a:0 \
    -show_entries stream=sample_rate \
    -of default=noprint_wrappers=1:nokey=1 "$PROCESSED_WAV")
  FINAL_CHANNELS=$(ffprobe -v error -select_streams a:0 \
    -show_entries stream=channels \
    -of default=noprint_wrappers=1:nokey=1 "$PROCESSED_WAV")

  FORMATS_GENERATED=""

  if echo "$PLATFORMS" | grep -q "desktop"; then
    ffmpeg -y -i "$PROCESSED_WAV" -c:a libvorbis -q:a 6 \
      "$OUTPUT_DIR/desktop/${name}.ogg" 2>/dev/null
    FORMATS_GENERATED+="\"desktop\": \"desktop/${name}.ogg\", "
  fi

  if echo "$PLATFORMS" | grep -q "mobile"; then
    ffmpeg -y -i "$PROCESSED_WAV" -ar 44100 -c:a aac -b:a 128k \
      "$OUTPUT_DIR/mobile/${name}.m4a" 2>/dev/null
    FORMATS_GENERATED+="\"mobile\": \"mobile/${name}.m4a\", "
  fi

  if echo "$PLATFORMS" | grep -q "web"; then
    ffmpeg -y -i "$PROCESSED_WAV" -ar 44100 -c:a libvorbis -q:a 4 \
      "$OUTPUT_DIR/web/${name}.ogg" 2>/dev/null
    ffmpeg -y -i "$PROCESSED_WAV" -ar 44100 -c:a libmp3lame -q:a 2 \
      "$OUTPUT_DIR/web/${name}.mp3" 2>/dev/null
    FORMATS_GENERATED+="\"web_ogg\": \"web/${name}.ogg\", \"web_mp3\": \"web/${name}.mp3\", "
  fi

  # Remove trailing comma-space
  FORMATS_GENERATED=$(echo "$FORMATS_GENERATED" | sed 's/, $//')

  # Build manifest entry
  MANIFEST_ENTRIES+="    \"${name}\": {
      \"master\": \"master/${name}.wav\",
      \"duration\": ${FINAL_DURATION},
      \"sampleRate\": ${FINAL_RATE},
      \"channels\": ${FINAL_CHANNELS},
      \"lufs\": ${LUFS_TARGET},
      \"formats\": { ${FORMATS_GENERATED} }
    },
"

  PROCESSED=$((PROCESSED + 1))
  echo "  Done: $name (${FINAL_DURATION}s)"
done

# ============================================================
# Generate Manifest JSON
# ============================================================
# Remove trailing comma from last entry
MANIFEST_ENTRIES=$(echo "$MANIFEST_ENTRIES" | sed '$ s/,$//')

cat > "$OUTPUT_DIR/manifest.json" << EOF
{
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pipeline": {
    "lufsTarget": ${LUFS_TARGET},
    "truePeak": ${TRUE_PEAK},
    "fadeIn": "${FADE_IN_MS}ms",
    "fadeOut": "${FADE_OUT_MS}ms",
    "trimThreshold": "${TRIM_THRESHOLD}dB",
    "platforms": "${PLATFORMS}"
  },
  "assets": {
${MANIFEST_ENTRIES}
  }
}
EOF

# ============================================================
# Cleanup Staging
# ============================================================
rm -rf "$STAGE_DIR"

echo ""
echo "========================================"
echo "Pipeline Complete"
echo "========================================"
echo "Processed: $PROCESSED files"
echo "Failed:    $FAILED files"
echo "Manifest:  $OUTPUT_DIR/manifest.json"
echo ""

# Print size summary
echo "Size Summary:"
for dir in master desktop mobile web; do
  if [ -d "$OUTPUT_DIR/$dir" ]; then
    SIZE=$(du -sh "$OUTPUT_DIR/$dir" 2>/dev/null | cut -f1)
    COUNT=$(find "$OUTPUT_DIR/$dir" -type f | wc -l | tr -d ' ')
    echo "  $dir: $SIZE ($COUNT files)"
  fi
done
```

### Pipeline Usage Examples

```bash
# Basic: Process all WAV files with defaults
./audio_pipeline.sh raw_audio/ processed/

# Mobile-focused: Mono output, mobile+web only
./audio_pipeline.sh raw_audio/ processed/ --mono --platforms mobile,web

# Custom loudness for mobile game
./audio_pipeline.sh raw_audio/ processed/ --lufs -16 --platforms mobile

# Minimal processing (just normalize and convert)
./audio_pipeline.sh raw_audio/ processed/ --fade-in 0 --fade-out 0 --trim-threshold -60
```

### Sample Manifest Output

```json
{
  "generated": "2026-03-08T12:00:00Z",
  "pipeline": {
    "lufsTarget": -23,
    "truePeak": -1,
    "fadeIn": "10ms",
    "fadeOut": "50ms",
    "trimThreshold": "-40dB",
    "platforms": "desktop,mobile,web"
  },
  "assets": {
    "sfx_footstep_grass_v1": {
      "master": "master/sfx_footstep_grass_v1.wav",
      "duration": 0.45,
      "sampleRate": 48000,
      "channels": 1,
      "lufs": -23,
      "formats": {
        "desktop": "desktop/sfx_footstep_grass_v1.ogg",
        "mobile": "mobile/sfx_footstep_grass_v1.m4a",
        "web_ogg": "web/sfx_footstep_grass_v1.ogg",
        "web_mp3": "web/sfx_footstep_grass_v1.mp3"
      }
    },
    "bgm_battle_intro_v2": {
      "master": "master/bgm_battle_intro_v2.wav",
      "duration": 182.30,
      "sampleRate": 48000,
      "channels": 2,
      "lufs": -23,
      "formats": {
        "desktop": "desktop/bgm_battle_intro_v2.ogg",
        "mobile": "mobile/bgm_battle_intro_v2.m4a",
        "web_ogg": "web/bgm_battle_intro_v2.ogg",
        "web_mp3": "web/bgm_battle_intro_v2.mp3"
      }
    }
  }
}
```

---

## Appendix: Quick Reference Card

### Recommended Defaults by Asset Type

| Asset Type   | Format   | Quality       | Rate    | Channels | LUFS |
|-------------|----------|---------------|---------|----------|------|
| SFX (short) | OGG q6   | ~192kbps      | 48kHz   | Mono     | -23  |
| BGM         | OGG q8   | ~256kbps      | 48kHz   | Stereo   | -23  |
| Ambient     | OGG q4   | ~128kbps      | 48kHz   | Stereo   | -23  |
| UI Sound    | OGG q4   | ~128kbps      | 44.1kHz | Mono     | -23  |
| Voice       | OGG q4   | ~128kbps      | 44.1kHz | Mono     | -23  |
| Mobile SFX  | AAC 128k | 128kbps       | 44.1kHz | Mono     | -16  |
| Web SFX     | MP3+OGG  | 128-192kbps   | 44.1kHz | Mono     | -23  |

### Essential ffmpeg One-Liners

```bash
# Check file info
ffprobe -v error -show_format -show_streams input.wav

# Measure loudness (quick)
ffmpeg -i input.wav -af loudnorm=print_format=summary -f null -

# Convert WAV to OGG (game quality)
ffmpeg -i input.wav -c:a libvorbis -q:a 6 output.ogg

# Normalize + convert in one pass (single-pass, less accurate)
ffmpeg -i input.wav -af loudnorm=I=-23:TP=-1 -c:a libvorbis -q:a 6 output.ogg

# Trim + fade + convert (all-in-one for quick iteration)
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_threshold=-40dB,\
areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse,\
afade=t=in:d=0.01,afade=t=out:st=1.95:d=0.05" \
  -c:a libvorbis -q:a 6 output.ogg
```

# Model Setup Reference

Local model installation, GPU/CPU requirements, Docker configurations, and verification tests for Tone's audio generation stack.

## Tool/Model Overview

| Model/Tool | Size | VRAM | CPU-only | Primary Use | Setup Method |
|------------|------|------|----------|-------------|-------------|
| AudioCraft MusicGen-small | ~1 GB | 4 GB | Yes (slow) | BGM prototyping | pip / Docker |
| AudioCraft MusicGen-medium | ~3 GB | 8 GB | Possible | BGM production | pip / Docker |
| AudioCraft MusicGen-large | ~7 GB | 16 GB | No | BGM high quality | pip / Docker |
| Bark (Suno) | ~5 GB | 8 GB+ | Yes (very slow) | Voice / ambient | pip / Docker |
| JSFXR | ~100 KB | N/A | N/A | SFX / UI (browser/Node) | npm |
| ffmpeg | ~80 MB | N/A | N/A | Audio processing | brew / apt / choco |

### Model Selection Guide

- **Prototyping / Game Jam**: MusicGen-small + JSFXR + ffmpeg. Runs on CPU if needed.
- **Indie Production**: MusicGen-medium + Bark + JSFXR + ffmpeg. 8 GB VRAM recommended.
- **High Quality / Commercial**: MusicGen-large + Bark + JSFXR + ffmpeg. 16 GB VRAM required.

---

## API vs Local Decision Matrix

| Factor | Use API (Replicate/ElevenLabs) | Use Local |
|--------|-------------------------------|-----------|
| No GPU available | Yes | No (except CPU fallback with small models) |
| Privacy / data sensitivity | No | Yes |
| Batch generation (100+ assets) | Expensive | Cheaper long-term |
| One-off / few generations | Yes | Overkill |
| Offline required | No | Yes |
| Setup time budget | Minutes | Hours |
| Consistent output quality | Yes (versioned API) | Depends on hardware |
| Cost per generation | $0.01-0.10 per clip | Electricity only |
| Latency sensitivity | Network-bound | Hardware-bound |

**Recommendation**: Start with API for prototyping, switch to local for batch production or privacy-sensitive projects.

---

## Preflight Check Script

```bash
#!/bin/bash
# Preflight check for local audio AI model requirements
# Usage: bash preflight_check.sh

set -euo pipefail

echo "=== Audio AI Preflight Check ==="
echo ""

PASS=0
WARN=0
FAIL=0

# 1. GPU Check
echo "--- GPU ---"
if command -v nvidia-smi &> /dev/null; then
  echo "[PASS] NVIDIA GPU detected"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if [ "$VRAM" -ge 16000 ]; then
    echo "[PASS] VRAM ${VRAM} MB - all models supported"
    ((PASS++))
  elif [ "$VRAM" -ge 8000 ]; then
    echo "[WARN] VRAM ${VRAM} MB - medium models OK, large may OOM"
    ((WARN++))
  elif [ "$VRAM" -ge 4000 ]; then
    echo "[WARN] VRAM ${VRAM} MB - small models only"
    ((WARN++))
  else
    echo "[FAIL] VRAM ${VRAM} MB - insufficient for most models"
    ((FAIL++))
  fi
elif [[ "$(uname)" == "Darwin" ]] && system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Metal"; then
  echo "[WARN] Apple GPU detected - MPS backend available (limited support)"
  echo "       MusicGen-small works; larger models may be slow"
  ((WARN++))
else
  echo "[WARN] No GPU detected - API mode recommended"
  echo "       CPU fallback available for MusicGen-small only"
  ((WARN++))
fi
echo ""

# 2. Disk Space Check
echo "--- Disk Space ---"
AVAIL_GB=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || df -g . 2>/dev/null | tail -1 | awk '{print $4}')
if [ -n "$AVAIL_GB" ] && [ "$AVAIL_GB" -ge 20 ]; then
  echo "[PASS] ${AVAIL_GB} GB available (20 GB recommended for all models)"
  ((PASS++))
elif [ -n "$AVAIL_GB" ] && [ "$AVAIL_GB" -ge 10 ]; then
  echo "[WARN] ${AVAIL_GB} GB available - enough for small/medium models"
  ((WARN++))
else
  echo "[FAIL] Low disk space - need at least 10 GB for model downloads"
  ((FAIL++))
fi
echo ""

# 3. Python Check
echo "--- Python ---"
if command -v python3 &> /dev/null; then
  PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
  PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
  if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 9 ]; then
    echo "[PASS] Python ${PY_VER} (3.9+ required)"
    ((PASS++))
  else
    echo "[FAIL] Python ${PY_VER} - need 3.9+"
    ((FAIL++))
  fi
else
  echo "[FAIL] Python 3 not found"
  ((FAIL++))
fi
echo ""

# 4. ffmpeg Check
echo "--- ffmpeg ---"
if command -v ffmpeg &> /dev/null; then
  FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
  echo "[PASS] ffmpeg ${FFMPEG_VER}"
  if ffmpeg -filters 2>/dev/null | grep -q loudnorm; then
    echo "[PASS] loudnorm filter available"
    ((PASS++))
  else
    echo "[FAIL] loudnorm filter missing - reinstall ffmpeg with full codec support"
    ((FAIL++))
  fi
  ((PASS++))
else
  echo "[FAIL] ffmpeg not found"
  ((FAIL++))
fi
echo ""

# 5. Node.js Check (for JSFXR)
echo "--- Node.js ---"
if command -v node &> /dev/null; then
  NODE_VER=$(node --version)
  NODE_MAJOR=$(echo "$NODE_VER" | tr -d 'v' | cut -d. -f1)
  if [ "$NODE_MAJOR" -ge 16 ]; then
    echo "[PASS] Node.js ${NODE_VER} (16+ required for JSFXR)"
    ((PASS++))
  else
    echo "[WARN] Node.js ${NODE_VER} - upgrade to 16+ for JSFXR"
    ((WARN++))
  fi
else
  echo "[WARN] Node.js not found - needed only for JSFXR"
  ((WARN++))
fi
echo ""

# Summary
echo "=== Summary ==="
echo "PASS: ${PASS}  WARN: ${WARN}  FAIL: ${FAIL}"
if [ "$FAIL" -gt 0 ]; then
  echo "ACTION: Fix FAIL items before local model setup"
  echo "        Consider API mode (Replicate/ElevenLabs) as alternative"
elif [ "$WARN" -gt 0 ]; then
  echo "ACTION: Review WARN items - local setup possible with limitations"
else
  echo "STATUS: All checks passed - ready for local model setup"
fi
```

---

## AudioCraft / MusicGen Setup

AudioCraft is Meta's framework for music and audio generation. MusicGen is the primary model for BGM and ambient audio.

### pip Install (venv)

```bash
# Create and activate virtual environment
python3 -m venv tone-env
source tone-env/bin/activate  # Linux/macOS
# tone-env\Scripts\activate   # Windows

# Install AudioCraft (stable)
pip install audiocraft

# Or install latest from source
pip install git+https://github.com/facebookresearch/audiocraft.git

# For Apple Silicon (MPS backend)
pip install torch torchaudio
pip install audiocraft
```

### Docker Setup

```dockerfile
# AudioCraft Docker image
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install AudioCraft
RUN pip install --no-cache-dir audiocraft

WORKDIR /workspace
COPY generate_music.py .

# Default: run generation script
CMD ["python", "generate_music.py"]
```

```bash
# Build and run
docker build -t tone-musicgen .

# GPU mode
docker run --gpus all -v $(pwd)/output:/workspace/output tone-musicgen

# CPU mode (slow, small model only)
docker run -v $(pwd)/output:/workspace/output tone-musicgen python generate_music.py --model small --device cpu
```

### Verification Test

```python
"""MusicGen verification test.
Run: python verify_musicgen.py
Expected: test_output.wav (5 seconds, 32 kHz)
"""
import sys
try:
    from audiocraft.models import MusicGen
    import torchaudio
except ImportError:
    print("FAIL: audiocraft not installed. Run: pip install audiocraft")
    sys.exit(1)

try:
    model = MusicGen.get_pretrained('facebook/musicgen-small')
    model.set_generation_params(duration=5)
    wav = model.generate(['happy upbeat game menu music'])
    torchaudio.save('test_output.wav', wav[0].cpu(), 32000)
    print("MusicGen OK - test_output.wav generated (5s, 32kHz)")
except RuntimeError as e:
    if "CUDA" in str(e) or "out of memory" in str(e):
        print(f"FAIL: GPU error - {e}")
        print("TIP: Try CPU mode or smaller model")
    else:
        print(f"FAIL: {e}")
    sys.exit(1)
```

### Model Variants

| Variant | HuggingFace ID | Notes |
|---------|---------------|-------|
| small | `facebook/musicgen-small` | Best for prototyping, CPU-compatible |
| medium | `facebook/musicgen-medium` | Good quality/speed balance |
| large | `facebook/musicgen-large` | Highest quality, GPU required |
| melody | `facebook/musicgen-melody` | Accepts melody conditioning input |
| stereo-small | `facebook/musicgen-stereo-small` | Stereo output |
| stereo-medium | `facebook/musicgen-stereo-medium` | Stereo output, better quality |
| stereo-large | `facebook/musicgen-stereo-large` | Stereo output, highest quality |

---

## Bark Setup

Bark is Suno's text-to-audio model capable of speech, sound effects, music snippets, and non-verbal sounds (laughter, sighs).

### pip Install

```bash
# Activate your existing venv or create a new one
source tone-env/bin/activate

# Install Bark
pip install git+https://github.com/suno-ai/bark.git

# Alternative: PyPI package
pip install suno-bark
```

### Environment Variables

```bash
# Force CPU mode (if GPU issues)
export SUNO_USE_SMALL_MODELS=True    # Use smaller models (~2 GB instead of ~5 GB)
export SUNO_OFFLOAD_CPU=True         # Offload to CPU when VRAM is limited

# Cache directory (models download here)
export XDG_CACHE_HOME=/path/to/cache  # Default: ~/.cache
```

### Docker Setup

```dockerfile
# Bark Docker image
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir suno-bark scipy

WORKDIR /workspace
COPY generate_voice.py .

CMD ["python", "generate_voice.py"]
```

```bash
# Build and run
docker build -t tone-bark -f Dockerfile.bark .

# GPU mode
docker run --gpus all -v $(pwd)/output:/workspace/output tone-bark

# CPU mode with small models
docker run -e SUNO_USE_SMALL_MODELS=True -v $(pwd)/output:/workspace/output tone-bark
```

### Verification Test

```python
"""Bark verification test.
Run: python verify_bark.py
Expected: test_bark.wav with speech audio
"""
import sys
try:
    from bark import generate_audio, SAMPLE_RATE
    import scipy.io.wavfile
    import numpy as np
except ImportError:
    print("FAIL: bark not installed. Run: pip install suno-bark scipy")
    sys.exit(1)

try:
    audio = generate_audio("Hello, welcome to the game! [laughs]")
    # Bark returns float32 array, normalize to int16 for wav
    audio_int16 = (audio * 32767).astype(np.int16)
    scipy.io.wavfile.write("test_bark.wav", SAMPLE_RATE, audio_int16)
    print(f"Bark OK - test_bark.wav generated ({len(audio)/SAMPLE_RATE:.1f}s, {SAMPLE_RATE}Hz)")
except RuntimeError as e:
    if "CUDA" in str(e) or "out of memory" in str(e):
        print(f"FAIL: GPU error - {e}")
        print("TIP: Set SUNO_USE_SMALL_MODELS=True or SUNO_OFFLOAD_CPU=True")
    else:
        print(f"FAIL: {e}")
    sys.exit(1)
```

### Bark Speaker Presets

Bark supports speaker presets for consistent voice generation:

```python
# Use a specific speaker preset
audio = generate_audio(
    "Game over! Try again.",
    history_prompt="v2/en_speaker_6"  # Male, neutral
)

# Available language prefixes: en, zh, fr, de, hi, it, ja, ko, pl, pt, ru, es, tr
# Speaker range: 0-9 for each language
# Example: "v2/ja_speaker_3" for Japanese speaker 3
```

---

## JSFXR Setup

JSFXR is a lightweight procedural sound effect generator, ideal for retro game SFX and UI sounds.

### npm Install

```bash
# In your project directory
npm install jsfxr

# Or with yarn
yarn add jsfxr

# Or as a dev dependency for build-time generation
npm install --save-dev jsfxr
```

### Verification Test

```javascript
// verify_jsfxr.js
// Run: node verify_jsfxr.js

const jsfxr = require('jsfxr');

// Coin pickup preset parameters
const coinParams = {
  oldParams: true,
  wave_type: 0,      // Square wave
  p_env_attack: 0,
  p_env_sustain: 0.15,
  p_env_decay: 0.35,
  p_base_freq: 0.57,
  p_freq_ramp: 0.25,
  p_duty: 0.55,
  p_duty_ramp: 0.035,
  sound_vol: 0.5,
};

try {
  const buffer = jsfxr.synth(coinParams);
  if (buffer && buffer.length > 0) {
    console.log(`JSFXR OK - generated ${buffer.length} samples`);
  } else {
    console.error("FAIL: synth returned empty buffer");
    process.exit(1);
  }
} catch (e) {
  console.error(`FAIL: ${e.message}`);
  process.exit(1);
}
```

### Browser Usage

```html
<!-- Direct browser usage via CDN -->
<script src="https://unpkg.com/jsfxr/jsfxr.js"></script>
<script>
  // Generate and play a laser sound
  const laserUrl = jsfxr([2,,0.17,,0.24,0.45,,,,,,,,,,,,,1,,,,,0.5]);
  const audio = new Audio(laserUrl);
  audio.play();
</script>
```

---

## ffmpeg Setup

ffmpeg is required for all audio post-processing: LUFS normalization, format conversion, trimming, and looping.

### Installation

#### macOS

```bash
brew install ffmpeg
```

#### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y ffmpeg
```

#### Windows

```powershell
# Chocolatey
choco install ffmpeg

# Or winget
winget install ffmpeg

# Or scoop
scoop install ffmpeg
```

### Verification

```bash
#!/bin/bash
# Verify ffmpeg installation for Tone requirements

echo "--- ffmpeg Version ---"
ffmpeg -version | head -1

echo ""
echo "--- Required Filters ---"
REQUIRED_FILTERS="loudnorm afade volume atempo"
ALL_OK=true

for filter in $REQUIRED_FILTERS; do
  if ffmpeg -filters 2>/dev/null | grep -q "$filter"; then
    echo "[PASS] $filter"
  else
    echo "[FAIL] $filter - missing"
    ALL_OK=false
  fi
done

echo ""
echo "--- Required Formats ---"
REQUIRED_FORMATS="ogg mp3 wav flac"
for fmt in $REQUIRED_FORMATS; do
  if ffmpeg -formats 2>/dev/null | grep -q "$fmt"; then
    echo "[PASS] $fmt"
  else
    echo "[FAIL] $fmt - missing"
    ALL_OK=false
  fi
done

echo ""
if [ "$ALL_OK" = true ]; then
  echo "ffmpeg OK - all required filters and formats available"
else
  echo "WARN: Some filters/formats missing - reinstall ffmpeg with full codec support"
fi
```

---

## All-in-One Setup Script

```bash
#!/bin/bash
# Complete Tone local environment setup
# Usage: bash setup_tone_env.sh [--cpu-only] [--skip-bark] [--skip-musicgen]
#
# This script:
# 1. Runs preflight checks
# 2. Creates Python virtual environment
# 3. Installs AudioCraft (MusicGen)
# 4. Installs Bark
# 5. Installs JSFXR (npm)
# 6. Verifies ffmpeg
# 7. Runs verification tests

set -euo pipefail

CPU_ONLY=false
SKIP_BARK=false
SKIP_MUSICGEN=false

for arg in "$@"; do
  case $arg in
    --cpu-only) CPU_ONLY=true ;;
    --skip-bark) SKIP_BARK=true ;;
    --skip-musicgen) SKIP_MUSICGEN=true ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

echo "=== Tone Environment Setup ==="
echo "CPU-only: ${CPU_ONLY}"
echo ""

# Step 1: Check prerequisites
echo "--- Step 1: Prerequisites ---"
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 required"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "FAIL: ffmpeg required (brew install ffmpeg)"; exit 1; }
echo "Prerequisites OK"
echo ""

# Step 2: Create virtual environment
echo "--- Step 2: Virtual Environment ---"
VENV_DIR="tone-env"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  echo "Created ${VENV_DIR}"
else
  echo "Using existing ${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
echo ""

# Step 3: Install PyTorch
echo "--- Step 3: PyTorch ---"
if [ "$CPU_ONLY" = true ]; then
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
else
  pip install torch torchaudio
fi
echo ""

# Step 4: Install AudioCraft (MusicGen)
if [ "$SKIP_MUSICGEN" = false ]; then
  echo "--- Step 4: AudioCraft ---"
  pip install audiocraft
  echo ""

  echo "--- Verify MusicGen ---"
  python3 -c "
from audiocraft.models import MusicGen
import torchaudio
model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=3)
wav = model.generate(['test beep'])
torchaudio.save('verify_musicgen.wav', wav[0].cpu(), 32000)
print('MusicGen OK')
"
  rm -f verify_musicgen.wav
  echo ""
fi

# Step 5: Install Bark
if [ "$SKIP_BARK" = false ]; then
  echo "--- Step 5: Bark ---"
  pip install suno-bark scipy
  if [ "$CPU_ONLY" = true ]; then
    export SUNO_USE_SMALL_MODELS=True
    export SUNO_OFFLOAD_CPU=True
  fi
  echo ""

  echo "--- Verify Bark ---"
  python3 -c "
from bark import generate_audio, SAMPLE_RATE
import scipy.io.wavfile
import numpy as np
audio = generate_audio('Test.')
audio_int16 = (audio * 32767).astype(np.int16)
scipy.io.wavfile.write('verify_bark.wav', SAMPLE_RATE, audio_int16)
print('Bark OK')
"
  rm -f verify_bark.wav
  echo ""
fi

# Step 6: JSFXR (if Node.js available)
echo "--- Step 6: JSFXR ---"
if command -v node >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    npm install jsfxr 2>/dev/null || echo "WARN: npm install jsfxr failed"
    echo "JSFXR OK"
  fi
else
  echo "SKIP: Node.js not found (JSFXR optional)"
fi
echo ""

# Step 7: ffmpeg verification
echo "--- Step 7: ffmpeg ---"
if ffmpeg -filters 2>/dev/null | grep -q loudnorm; then
  echo "ffmpeg OK (loudnorm available)"
else
  echo "WARN: ffmpeg loudnorm filter missing"
fi
echo ""

echo "=== Setup Complete ==="
echo "Activate environment: source ${VENV_DIR}/bin/activate"
```

---

## Troubleshooting

### CUDA Out of Memory

```
RuntimeError: CUDA out of memory
```

**Solutions** (in order of preference):
1. Use a smaller model variant: `musicgen-small` instead of `musicgen-large`
2. Reduce generation duration: `model.set_generation_params(duration=5)`
3. Clear GPU cache before generation: `torch.cuda.empty_cache()`
4. Set environment variable for Bark: `SUNO_USE_SMALL_MODELS=True`
5. Fall back to CPU: `model = MusicGen.get_pretrained('facebook/musicgen-small', device='cpu')`
6. Use API mode (Replicate) instead of local generation

### PyTorch Not Compiled with CUDA

```
AssertionError: Torch not compiled with CUDA enabled
```

**Solution**: Reinstall PyTorch with CUDA support matching your driver version.

```bash
# Check CUDA version
nvidia-smi | grep "CUDA Version"

# Reinstall with correct CUDA
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121  # For CUDA 12.1
# See https://pytorch.org/get-started/locally/ for other versions
```

### Apple Silicon (MPS) Issues

```
RuntimeError: MPS backend out of memory
# or
NotImplementedError: MPS does not support ...
```

**Solutions**:
1. Use `device='cpu'` explicitly for unsupported operations
2. Set `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` to reduce memory fragmentation
3. Use `musicgen-small` only on MPS - larger models may hit unsupported ops

### ffmpeg loudnorm Not Found

```
No such filter: 'loudnorm'
```

**Solution**: Install ffmpeg with full codec/filter support.

```bash
# macOS - reinstall with all options
brew reinstall ffmpeg

# Ubuntu - install from source or use snap
sudo snap install ffmpeg

# Verify
ffmpeg -filters 2>/dev/null | grep loudnorm
```

### JSFXR Issues

- **Node.js version**: Requires Node.js >= 16. Check with `node --version`.
- **Import errors**: Use `require('jsfxr')` for CommonJS or `import` for ESM.
- **No audio output in browser**: Ensure user interaction before `audio.play()` (autoplay policy).

### Bark Model Download Stuck

Models download to `~/.cache/suno/bark_v0/` on first run (~5 GB total).

**Solutions**:
1. Check disk space: `df -h ~/.cache`
2. Set custom cache: `export XDG_CACHE_HOME=/path/with/space`
3. Use small models: `export SUNO_USE_SMALL_MODELS=True`
4. Manual download: fetch model files from HuggingFace and place in cache directory

### Docker GPU Access

```
docker: Error response from daemon: could not select device driver
```

**Solution**: Install NVIDIA Container Toolkit.

```bash
# Ubuntu
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

## Quick Reference: Device Selection

```python
import torch

def get_best_device():
    """Select the best available device for audio model inference."""
    if torch.cuda.is_available():
        return 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'  # Apple Silicon - limited model support
    else:
        return 'cpu'  # Slowest but always available

device = get_best_device()
print(f"Using device: {device}")
```

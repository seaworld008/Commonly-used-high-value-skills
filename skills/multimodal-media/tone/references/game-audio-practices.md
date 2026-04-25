# Game Audio Best Practices Reference

Comprehensive reference for game audio production, implementation, and optimization.
Covers loudness standards, mixing, spatial audio, adaptive music, sound design,
asset management, and platform-specific guidelines.

---

## Table of Contents

1. [LUFS Normalization Standards](#1-lufs-normalization-standards)
2. [Category Mix Levels](#2-category-mix-levels)
3. [Spatial Audio Basics](#3-spatial-audio-basics)
4. [Adaptive / Interactive Music Design](#4-adaptive--interactive-music-design)
5. [Sound Design Principles Per Category](#5-sound-design-principles-per-category)
6. [Asset Naming Conventions](#6-asset-naming-conventions)
7. [Memory Budget Guidelines Per Platform](#7-memory-budget-guidelines-per-platform)
8. [Audio Implementation Checklist](#8-audio-implementation-checklist)

---

## 1. LUFS Normalization Standards

### Overview

LUFS (Loudness Units relative to Full Scale) is the standard measurement for
perceived loudness in broadcast and interactive media. Game audio targets vary
by platform and context.

### Target Levels by Context

| Context              | Target LUFS | Standard        | Notes                                    |
|----------------------|-------------|-----------------|------------------------------------------|
| PC / Console Games   | -23 LUFS    | EBU R128        | European broadcast standard, widely adopted |
| Mobile Games         | -16 LUFS    | Custom / ATSC   | Louder to compensate for phone speakers  |
| Trailers / Cinematics| -16 LUFS    | ATSC A/85       | Competitive loudness for marketing       |
| VR / AR              | -23 LUFS    | EBU R128        | Comfort-focused, avoid listener fatigue  |
| In-Game Dialogue     | -24 to -18 LUFS | -            | Loudest category relative to mix         |
| Streaming Output     | -14 LUFS    | Platform-specific| YouTube/Twitch normalization targets     |

### True Peak Limiting

- **Target**: -1 dBTP (decibels True Peak)
- **Why**: Prevents inter-sample clipping during D/A conversion and codec encoding
- **Mobile exception**: -1.5 dBTP recommended due to lossy codec headroom
- **Streaming**: -2 dBTP for additional safety margin during transcoding

### Loudness Range (LRA)

- **Dialogue-heavy games**: LRA 5-10 LU (narrow range for intelligibility)
- **Action games**: LRA 10-20 LU (wide range for dramatic impact)
- **Mobile games**: LRA < 8 LU (consistent volume in noisy environments)
- **Ambient/exploration**: LRA 15-25 LU (natural dynamic feel)

### Measurement Tools

#### ffmpeg Loudness Analysis

```bash
# Measure integrated loudness (LUFS), true peak, and LRA
ffmpeg -i input.wav -af loudnorm=print_format=json -f null -

# Two-pass loudness normalization to -23 LUFS
# Pass 1: Measure
ffmpeg -i input.wav -af loudnorm=I=-23:TP=-1:LRA=11:print_format=json \
  -f null - 2>&1 | tail -12

# Pass 2: Apply (using measured values from pass 1)
ffmpeg -i input.wav -af loudnorm=I=-23:TP=-1:LRA=11:\
  measured_I=-20.5:measured_TP=-0.3:measured_LRA=8.2:\
  measured_thresh=-31.2:offset=0.5:linear=true \
  -ar 48000 output.wav
```

#### Single-Pass Normalization (Simpler but Less Precise)

```bash
# Quick normalization to -23 LUFS (single-pass, uses limiter)
ffmpeg -i input.wav -af loudnorm=I=-23:TP=-1:LRA=11 output.wav

# Mobile target (-16 LUFS)
ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=8 output_mobile.wav

# Trailer target (-16 LUFS, tighter peak)
ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1:LRA=12 output_trailer.wav
```

#### Batch Processing

```bash
# Normalize all WAV files in a directory to -23 LUFS
for f in *.wav; do
  ffmpeg -i "$f" -af loudnorm=I=-23:TP=-1:LRA=11 \
    -ar 48000 "normalized/${f}" -y
done
```

#### Python (pyloudnorm)

```python
import soundfile as sf
import pyloudnorm as pyln

# Load audio
data, rate = sf.read("input.wav")

# Measure loudness
meter = pyln.Meter(rate)
loudness = meter.integrated_loudness(data)
print(f"Integrated loudness: {loudness:.1f} LUFS")

# Normalize to target
target_lufs = -23.0
normalized = pyln.normalize.loudness(data, loudness, target_lufs)
sf.write("output.wav", normalized, rate)
```

### Quality Tiers and Tolerances

| Tier       | Tolerance   | Measurement                |
|------------|-------------|----------------------------|
| AAA        | +/- 0.5 LU  | Full EBU R128 compliance  |
| Standard   | +/- 1.0 LU  | Integrated loudness check |
| Indie/MVP  | +/- 2.0 LU  | Spot-check key assets     |

---

## 2. Category Mix Levels

### Reference Mix Structure

All levels are relative to the dialogue/voice channel, which serves as the
reference (0 dB). This hierarchy ensures speech intelligibility while
maintaining musical and atmospheric presence.

| Category       | Relative Level | Typical LUFS Range | Bus Priority | Notes                              |
|----------------|---------------|--------------------|--------------|------------------------------------|
| Voice/Dialogue | 0 dB (ref)    | -24 to -18 LUFS   | Highest      | Always intelligible, ducking anchor|
| SFX            | -6 dB         | -30 to -24 LUFS   | High         | Gameplay feedback, combat, impacts |
| UI             | -9 dB         | -32 to -26 LUFS   | Medium-High  | Consistent, never masked           |
| BGM            | -12 dB        | -36 to -30 LUFS   | Medium       | Ducked during dialogue             |
| Ambient        | -18 dB        | -42 to -36 LUFS   | Low          | Bed layer, subtle presence         |

### Ducking Configuration

Ducking temporarily lowers one audio category when another plays.

```
Trigger:       Voice/Dialogue active
Target:        BGM bus
Duck Amount:   -6 to -12 dB
Attack Time:   50-100 ms (fast fade down)
Hold Time:     Duration of dialogue + 200ms
Release Time:  500-1000 ms (gradual return)
```

#### Common Ducking Pairs

| Trigger       | Target    | Duck Amount | Attack  | Release  |
|---------------|-----------|-------------|---------|----------|
| Dialogue      | BGM       | -9 dB       | 80 ms   | 800 ms   |
| Dialogue      | Ambient   | -6 dB       | 80 ms   | 600 ms   |
| Loud SFX      | BGM       | -3 dB       | 50 ms   | 400 ms   |
| Cutscene      | All non-VO| -12 dB      | 100 ms  | 1000 ms  |
| UI Confirm    | BGM       | -3 dB       | 30 ms   | 300 ms   |

### Dynamic Range Compression Per Bus

| Bus       | Ratio  | Threshold  | Attack  | Release | Makeup  |
|-----------|--------|------------|---------|---------|---------|
| Voice     | 3:1    | -18 dBFS   | 5 ms    | 150 ms  | +3 dB   |
| SFX       | 2:1    | -12 dBFS   | 1 ms    | 100 ms  | +2 dB   |
| UI        | 4:1    | -20 dBFS   | 1 ms    | 50 ms   | +4 dB   |
| BGM       | 2:1    | -16 dBFS   | 10 ms   | 200 ms  | +2 dB   |
| Ambient   | 1.5:1  | -24 dBFS   | 20 ms   | 500 ms  | +1 dB   |

### Voice Priority System (Voice Stealing)

When multiple sounds compete for limited channels:

```
Priority Order (highest first):
1. Player dialogue / narrator
2. Critical gameplay SFX (damage, death, quest complete)
3. NPC dialogue (proximity-based)
4. Combat SFX
5. Environmental SFX
6. UI sounds
7. BGM stems
8. Ambient layers

Max Simultaneous Voices (typical):
- Mobile:  16-32 voices
- Console: 64-128 voices
- PC:      128-256 voices
```

### User-Facing Volume Controls

Expose these sliders to players:

| Slider          | Controls         | Default | Range     |
|-----------------|------------------|---------|-----------|
| Master Volume   | All buses        | 80%     | 0-100%    |
| Music           | BGM bus          | 70%     | 0-100%    |
| Sound Effects   | SFX + Ambient    | 80%     | 0-100%    |
| Voice           | Dialogue bus     | 100%    | 0-100%    |
| UI Sounds       | UI bus           | 70%     | 0-100%    |

---

## 3. Spatial Audio Basics

### Distance Attenuation Models

Distance attenuation controls how sound volume decreases as the listener
moves away from the source.

#### Linear Attenuation

```
gain = 1.0 - clamp((distance - minDistance) / (maxDistance - minDistance), 0, 1)
```

- Predictable, easy to tune
- Unrealistic (sound doesn't decay linearly in nature)
- Best for: UI-like world sounds, stylized games

#### Logarithmic Attenuation (Realistic)

```
gain = 1.0 / (1.0 + rolloffFactor * (distance - minDistance))
```

- Approximates inverse-square law
- Natural-sounding falloff
- Best for: realistic/immersive games

#### Inverse Distance (Web Audio API default)

```
gain = minDistance / (minDistance + rolloffFactor * (distance - minDistance))
```

- Smooth falloff curve
- Used by Web Audio API by default
- Best for: web games, general purpose

#### Exponential Attenuation

```
gain = pow(distance / minDistance, -rolloffFactor)
```

- Very steep near-field, gentle far-field
- Best for: dramatic close-range effects

### Recommended Distance Settings by Sound Type

| Sound Type         | Min Distance | Max Distance | Rolloff Factor | Model        |
|--------------------|-------------|-------------|----------------|--------------|
| Footsteps          | 1 m         | 20 m        | 1.5            | Logarithmic  |
| Gunshot            | 2 m         | 100 m       | 1.0            | Logarithmic  |
| Dialogue           | 0.5 m       | 15 m        | 2.0            | Logarithmic  |
| Ambient emitter    | 5 m         | 50 m        | 0.5            | Linear       |
| Explosion          | 5 m         | 200 m       | 0.8            | Logarithmic  |
| UI / Non-spatial   | N/A         | N/A         | N/A            | None (2D)    |
| Music emitter      | 3 m         | 30 m        | 1.0            | Linear       |
| Door creak         | 0.5 m       | 10 m        | 2.0            | Logarithmic  |
| Waterfall          | 10 m        | 80 m        | 0.5            | Logarithmic  |
| Campfire           | 1 m         | 15 m        | 1.5            | Logarithmic  |

### 3D Panning

- **Stereo panning**: Simple left-right based on angle to source
- **VBAP** (Vector Base Amplitude Panning): Multi-speaker, distributes across
  nearest speaker pair/triplet
- **Ambisonics**: Full-sphere encoding, decoded for any speaker layout
  - First-order (4 channels): adequate for most games
  - Third-order (16 channels): high spatial resolution for VR

### HRTF (Head-Related Transfer Function)

HRTFs simulate how the human ear perceives sound direction using headphones.

```
Key Concepts:
- ITD (Interaural Time Difference): ~0.6ms max delay between ears
- ILD (Interaural Level Difference): frequency-dependent shadowing
- Pinna filtering: spectral coloring that encodes elevation

Implementation Options:
- Web Audio API: PannerNode with panningModel = "HRTF"
- Steam Audio: Built-in HRTF with customizable profiles
- Resonance Audio (Google): Cross-platform HRTF
- Project Acoustics (Microsoft): Baked wave physics + HRTF
- Custom SOFA files: Personalized HRTF measurements
```

### Occlusion and Obstruction

**Occlusion**: Sound source and listener are in different acoustic spaces
(e.g., sound behind a closed door).

```
Effect: Low-pass filter + volume reduction
Typical LPF cutoff: 500-2000 Hz (depending on material)
Volume reduction: -6 to -20 dB

Material Multipliers:
  Thin wood:   0.7 (30% reduction)
  Thick wall:  0.3 (70% reduction)
  Glass:       0.5 (50% reduction)
  Metal door:  0.2 (80% reduction)
  Fabric/thin: 0.8 (20% reduction)
```

**Obstruction**: Direct path is blocked but sound can diffract around the object.

```
Effect: Mild low-pass filter, minimal volume reduction
Typical LPF cutoff: 2000-6000 Hz
Volume reduction: -2 to -6 dB
Diffraction model: Higher frequencies blocked more than lower
```

### Reverb Zones

Reverb simulates the acoustic properties of spaces.

| Space Type     | Pre-delay | Decay Time | Wet/Dry | HF Damping |
|----------------|-----------|------------|---------|------------|
| Small room     | 5-10 ms   | 0.3-0.8 s | 20-30%  | 0.6        |
| Large hall     | 20-40 ms  | 1.5-3.0 s | 30-50%  | 0.4        |
| Cathedral      | 40-80 ms  | 3.0-6.0 s | 40-60%  | 0.3        |
| Cave           | 30-60 ms  | 2.0-4.0 s | 50-70%  | 0.2        |
| Outdoor open   | 0-5 ms    | 0.1-0.3 s | 5-10%   | 0.8        |
| Bathroom       | 5-15 ms   | 0.8-1.5 s | 30-50%  | 0.5        |
| Corridor       | 10-20 ms  | 1.0-2.0 s | 25-40%  | 0.5        |
| Forest         | 5-15 ms   | 0.3-0.6 s | 10-20%  | 0.7        |
| Underwater     | 20-50 ms  | 1.5-3.0 s | 60-80%  | 0.1        |

#### Zone Transition Blending

```
When listener moves between reverb zones:
- Crossfade duration: 500-2000 ms
- Interpolate: decay time, wet/dry, pre-delay, HF damping
- Avoid abrupt changes (causes audible "popping")
- Use trigger volumes with overlap regions
```

---

## 4. Adaptive / Interactive Music Design

### Overview

Adaptive music responds to gameplay state, creating a dynamic soundtrack
that reinforces the player's experience without interruption.

### Approach 1: Horizontal Re-Sequencing

Arrange musical sections (segments) that play in different orders based
on game state.

```
Structure:
  [Intro] -> [Explore A] -> [Explore B] -> [Tension Build] -> [Combat] -> [Victory]
                  |              |               |
                  +<--- loop --->+               |
                                                 |
                  [Explore A] <------------------+

Transition Points:
- Each segment has defined exit points (beat boundaries)
- Next segment is queued at the nearest exit point
- Exit points typically at bar boundaries (every 4 or 8 beats)

Segment Design Rules:
- All segments share the same tempo and time signature
- Same key or related keys (relative major/minor)
- Harmonically compatible endpoints (end on V or I chord)
- Each segment: 8-32 bars (15-60 seconds typical)
```

#### Implementation Pattern

```python
class HorizontalSequencer:
    def __init__(self, bpm, time_signature=(4, 4)):
        self.bpm = bpm
        self.beat_duration = 60.0 / bpm
        self.bar_duration = self.beat_duration * time_signature[0]
        self.current_segment = None
        self.queued_segment = None

    def queue_segment(self, segment_name, transition="next_bar"):
        """Queue next segment at the specified transition point."""
        self.queued_segment = segment_name
        self.transition_type = transition
        # "next_bar": transition at next bar boundary
        # "next_beat": transition at next beat
        # "immediate": crossfade now

    def get_next_bar_time(self, current_time, segment_start_time):
        elapsed = current_time - segment_start_time
        bars_elapsed = int(elapsed / self.bar_duration)
        return segment_start_time + (bars_elapsed + 1) * self.bar_duration
```

### Approach 2: Vertical Layering (Stem-Based)

Multiple stems play simultaneously; layers are added/removed based on
game intensity or state.

```
Layer Stack (bottom to top):
  Layer 0: Pad / Drone        (always playing)
  Layer 1: Bass               (exploration+)
  Layer 2: Rhythm / Percussion (tension+)
  Layer 3: Melody / Lead      (combat+)
  Layer 4: Intensity / FX     (boss / climax)

Intensity Mapping:
  0.0 - 0.2  -> Layers 0
  0.2 - 0.4  -> Layers 0-1
  0.4 - 0.6  -> Layers 0-2
  0.6 - 0.8  -> Layers 0-3
  0.8 - 1.0  -> Layers 0-4

Stem Requirements:
  - All stems MUST be exactly the same length
  - All stems MUST share tempo, key, and time signature
  - All stems MUST be synchronized to the same start point
  - Export stems with identical sample count for perfect alignment
```

#### Layer Fade Implementation

```python
class VerticalLayerMixer:
    def __init__(self, stems, fade_duration=2.0):
        self.stems = stems  # dict: layer_name -> audio_source
        self.fade_duration = fade_duration
        self.target_volumes = {}

    def set_intensity(self, intensity):
        """Set game intensity (0.0 to 1.0) to control active layers."""
        thresholds = [0.0, 0.2, 0.4, 0.6, 0.8]
        for i, (name, stem) in enumerate(self.stems.items()):
            if i < len(thresholds):
                target = 1.0 if intensity >= thresholds[i] else 0.0
                self.target_volumes[name] = target
                # Fade to target over fade_duration

    def update(self, delta_time):
        """Smoothly interpolate volumes toward targets."""
        for name, stem in self.stems.items():
            target = self.target_volumes.get(name, 0.0)
            current = stem.volume
            if abs(current - target) > 0.01:
                rate = delta_time / self.fade_duration
                stem.volume += (target - current) * min(rate, 1.0)
```

### Approach 3: Stinger System

Short musical phrases (stingers) triggered by specific game events.

```
Stinger Types:
  - Victory fanfare:     2-5 seconds, triumphant
  - Death sting:         1-3 seconds, dramatic/somber
  - Discovery:           1-2 seconds, wonder/curiosity
  - Level up:            2-4 seconds, ascending, celebratory
  - Boss intro:          3-8 seconds, ominous buildup
  - Quest complete:      2-4 seconds, satisfying resolution
  - Secret found:        1-2 seconds, mysterious/playful
  - Danger warning:      1-2 seconds, tense, urgent

Implementation Rules:
  - Stingers duck current BGM (typically -6 to -12 dB)
  - Stinger plays on a separate bus from BGM
  - Queue stingers; do not stack multiple simultaneously
  - After stinger completes, restore BGM level over 500-1000ms
  - Stingers should be key-compatible with current BGM or atonal
```

### Transition Types

| Type         | Duration    | Use Case                          | Complexity |
|--------------|-------------|-----------------------------------|------------|
| Hard Cut     | 0 ms        | Dramatic shifts, horror           | Low        |
| Crossfade    | 1-4 s       | General purpose, mood shifts      | Low        |
| Beat-Synced  | To next beat| Rhythmic music, action games      | Medium     |
| Bar-Synced   | To next bar | Structured music, RPGs            | Medium     |
| Transition segment | 2-8 s | Composed bridge between states   | High       |
| Tail + Intro | Variable    | Segment tail plays over new intro | Medium     |

### Music State Machine

```
States:
  MENU         -> ambient pad, simple melody
  EXPLORATION  -> medium layers, relaxed tempo
  TENSION      -> add percussion, raise intensity
  COMBAT       -> full layers, aggressive
  BOSS         -> unique theme, maximum intensity
  VICTORY      -> stinger + return to exploration
  DEATH        -> stinger + fade to silence
  CUTSCENE     -> scripted music cues

Transitions:
  MENU -> EXPLORATION        : on game_start         (crossfade 3s)
  EXPLORATION -> TENSION     : on enemy_nearby        (bar-synced)
  TENSION -> COMBAT          : on combat_start        (beat-synced)
  COMBAT -> TENSION          : on enemies_thinning    (bar-synced)
  TENSION -> EXPLORATION     : on combat_end          (crossfade 2s)
  COMBAT -> BOSS             : on boss_encounter      (transition segment)
  BOSS -> VICTORY            : on boss_defeated       (stinger)
  COMBAT -> DEATH            : on player_death        (stinger)
  ANY -> CUTSCENE            : on cutscene_trigger    (crossfade 1s)
  CUTSCENE -> EXPLORATION    : on cutscene_end        (crossfade 2s)

Cooldowns:
  - Minimum time in state: 5 seconds (prevents rapid flickering)
  - Combat exit delay: 3 seconds after last enemy engagement
  - Tension decay: gradual over 10-15 seconds after threat removed
```

---

## 5. Sound Design Principles Per Category

### 5.1 SFX (Sound Effects)

#### Layering Model

Every complex SFX consists of three components:

```
[Transient] + [Body] + [Tail]
   |             |         |
   |             |         +-- Reverb, decay, release
   |             +------------ Core tonal content, sustain
   +-------------------------- Initial attack, click, impact
```

| Component  | Frequency Focus  | Duration    | Purpose                  |
|------------|------------------|-------------|--------------------------|
| Transient  | 2-8 kHz          | 5-50 ms     | Presence, "punch"        |
| Body       | 100 Hz - 4 kHz   | 50-500 ms   | Character, substance     |
| Tail       | Full spectrum    | 200ms-3s    | Space, weight, resonance |

#### Variation Generation

Avoid repetition by creating multiple variations of each sound:

```
Techniques:
  1. Pitch shift:   +/- 2-5 semitones (subtle) or +/- 1 octave (dramatic)
  2. Time stretch:  +/- 10-30% (keep pitch or allow drift)
  3. Reverse:       Layer reversed transient for pre-impact "suck"
  4. Layer swap:    Replace one layer with an alternative
  5. Filter sweep:  Vary cutoff frequency per instance
  6. Start offset:  Randomize playback start position (0-50ms)

Minimum Variations by Priority:
  - Critical SFX (footsteps, gunshots): 5-8 variations
  - Standard SFX (impacts, pickups): 3-5 variations
  - Background SFX (debris, cloth): 2-3 variations
  - One-shot SFX (boss death, cutscene): 1 variation OK

Round-Robin or Random Selection:
  - Never play same variation twice in a row
  - Weighted random: recently played = lower weight
```

#### Impact Sound Design (Attack-Sustain-Release)

```
Attack (0-20ms):
  - Hard transient for metal, wood, stone
  - Soft attack for cloth, flesh, snow

Sustain (20-200ms):
  - Resonance of material (metallic ring, wooden thud)
  - Crunch/crackle for destruction (glass, bones)

Release (200ms-2s):
  - Debris scatter, echo, reverb tail
  - Longer for larger objects/spaces
  - Environmental response (splashing, rattling)
```

#### Footstep System

```
Matrix: Surface Type x Shoe Type x Speed

Surface Types:
  concrete, wood, metal, grass, gravel, sand,
  mud, water_shallow, water_deep, snow, ice, carpet, tile

Shoe Types:
  barefoot, boots, sneakers, heels, armor

Speed States:
  walk, run, sprint, crouch_walk, land (from jump)

Total Variations Needed:
  13 surfaces x 5 shoes x 5 speeds x 4 variations = 1,300 assets
  (In practice, reduce to key combinations: ~200-400 assets)

Prioritization:
  1. Cover all surfaces for the player's default footwear
  2. Add shoe-type variations for the most common surfaces
  3. Speed variations can be achieved via pitch/speed manipulation
  4. Fill remaining gaps with processing (EQ, pitch, layering)
```

### 5.2 BGM (Background Music)

#### Loop Point Selection

```
Good Loop Points:
  - End of a musical phrase (every 4 or 8 bars)
  - After a resolution chord (tonic/I chord)
  - At a rhythmically quiet moment
  - Where the waveform crosses zero or near-zero

Bad Loop Points:
  - Mid-phrase or mid-note
  - During a crescendo/build
  - At a rhythmic accent
  - Where there's a loud sustained note (causes click)

Crossfade at Loop Point:
  - Apply 10-50ms crossfade at the loop boundary
  - Longer crossfade (100-500ms) for sustained/ambient music
  - Test with headphones at high volume to catch clicks
```

#### Intro + Loop Body Structure

```
File Structure Options:

Option A: Single file with loop markers
  [Intro (one-time)] [Loop Start >>>>>>>>>> Loop End]
  Metadata stores loop start sample position

Option B: Separate files
  bgm_level1_intro.ogg     (plays once)
  bgm_level1_loop.ogg      (loops indefinitely)
  Sequenced by the audio engine

Option C: Seamless single loop (no intro)
  bgm_level1_loop.ogg      (loop from start)
  Simplest, most compatible
```

#### Stem Separation for Adaptive Systems

```
Recommended Stem Groups:
  1. Drums / Percussion
  2. Bass
  3. Harmony / Chords (keys, pads, rhythm guitar)
  4. Melody / Lead
  5. FX / Textures (risers, impacts, ear candy)
  6. Vocals (if applicable)

Export Requirements:
  - Same sample rate, bit depth, and length for ALL stems
  - Identical start point (silence-padded if needed)
  - Same loudness processing applied uniformly
  - Test playback of all stems simultaneously = full mix
```

#### Tempo and Key Considerations

```
Tempo Guidelines by Game State:
  Menu / Title:      70-90 BPM    (relaxed, inviting)
  Exploration:       80-110 BPM   (moderate, steady)
  Tension:           100-130 BPM  (building energy)
  Combat:            120-160 BPM  (driving, aggressive)
  Boss:              130-180 BPM  (intense, urgent)
  Victory:           100-120 BPM  (triumphant, resolving)
  Sad / Loss:        60-80 BPM    (slow, reflective)

Key Selection:
  - Minor keys: tension, sadness, mystery, danger
  - Major keys: triumph, joy, exploration, safety
  - Modal: Dorian (heroic minor), Mixolydian (adventurous major)
  - Consistent key relationships across states for smooth transitions
```

### 5.3 Voice / Dialogue

#### Dialogue Production Pipeline

```
1. Recording
   - Sample rate: 48 kHz (standard) or 44.1 kHz (acceptable)
   - Bit depth: 24-bit (recording), 16-bit (delivery)
   - Environment: treated room, noise floor < -60 dBFS
   - Microphone: large-diaphragm condenser, consistent placement
   - Pop filter + shock mount mandatory

2. Editing
   - Remove breaths (or reduce by -12 dB for natural feel)
   - Cut silence to consistent length (200-500ms between lines)
   - Remove mouth clicks, lip smacks, room noise
   - Align timing to script/subtitle cues

3. De-essing
   - Target frequencies: 4-8 kHz (sibilance range)
   - Threshold: -20 to -15 dBFS
   - Ratio: 4:1 to 8:1
   - Apply per-speaker (different voices need different settings)

4. Compression
   - Ratio: 3:1 to 4:1
   - Threshold: -18 to -12 dBFS
   - Attack: 5-10 ms (preserve articulation)
   - Release: 100-200 ms
   - Makeup gain to target level

5. Normalization
   - Target: -24 to -18 LUFS (dialogue reference level)
   - True peak: -1 dBTP
   - Consistency across all dialogue files is critical
```

#### Lip Sync Timing Markers

```
Marker Types:
  - Phoneme markers: individual mouth shapes per phoneme
  - Viseme markers: grouped mouth shapes (typically 12-15 visemes)
  - Word boundaries: start/end of each word
  - Emphasis markers: stressed syllables for animation blend

Common Viseme Set (Oculus/standard):
  sil   : silence, closed mouth
  PP    : p, b, m
  FF    : f, v
  TH    : th (dental)
  DD    : t, d, n
  kk    : k, g
  CH    : ch, j, sh
  SS    : s, z
  nn    : n, l
  RR    : r
  aa    : a (open)
  E     : e (half open)
  ih    : i (narrow)
  oh    : o (round)
  ou    : u (tight round)
```

#### Bark System

Short, repeated voice phrases for non-scripted gameplay moments.

```
Bark Categories:
  - Idle chatter:        "All quiet..." / "Nothing here."
  - Combat callouts:     "Enemy spotted!" / "Reloading!"
  - Damage reactions:    "Ugh!" / "I'm hit!"
  - Acknowledgements:    "Got it." / "On my way."
  - Environmental:       "It's cold..." / "Watch your step."
  - Death:               "No...!" / *death sound*

Design Rules:
  - 3-8 variations per bark type per character
  - Cooldown timer: 10-30 seconds between same-type barks
  - Interrupt priority: damage > combat > environmental > idle
  - Keep barks under 3 seconds each
  - Record with consistent energy/mic distance per session
```

#### Localization Considerations

```
Planning:
  - Budget 20-40% more duration for translated dialogue
    (German, French, Spanish tend to be longer than English)
  - Use consistent naming: vo_npc_merchant_greeting_01_en.wav
  - Maintain metadata spreadsheet: file, character, line, language
  - Leave room in UI for longer subtitle text

Technical:
  - Same sample rate and format across all languages
  - Separate voice bus allows per-language volume adjustment
  - Fallback to default language if localized file missing
  - Lip sync may need per-language viseme data
```

### 5.4 Ambient

#### Seamless Looping Techniques

```
Method 1: Crossfade Loop
  - Overlap last 2-5 seconds with first 2-5 seconds
  - Apply equal-power crossfade at overlap
  - Total loop length: 30-120 seconds (longer = less noticeable repeat)

Method 2: Granular/Procedural
  - Break ambient into small grains (50-500ms)
  - Engine randomly selects and overlaps grains
  - Natural variation without obvious loops
  - Higher CPU cost, lower memory

Method 3: Long Recording
  - Record 3-5 minutes of continuous ambient
  - Find a natural loop point (quiet moment)
  - Apply subtle crossfade at boundaries
  - Larger file size, most natural result

Testing:
  - Listen for rhythmic patterns that reveal the loop
  - Play loop for 10+ minutes to catch repetition fatigue
  - Test at different playback speeds if engine supports it
```

#### Layer Mixing (Base + Detail + Event)

```
Base Layer (always playing):
  - Continuous texture: wind, room tone, crowd murmur
  - Looped, very long (60-180 seconds minimum)
  - Low volume, subtle

Detail Layer (semi-random):
  - Specific sounds on random timers
  - Bird chirps, distant traffic, creaking wood
  - Randomized: position, pitch (+/- 2 semitones), volume (+/- 3 dB)
  - Timer: 3-15 seconds between events

Event Layer (triggered):
  - One-shot environmental events
  - Thunder, distant explosion, animal call
  - Triggered by: timer, gameplay event, random chance
  - Timer: 30-120 seconds between events
  - Can be conditional (thunder only during rain state)
```

#### Time-of-Day System

```
Periods:
  Dawn    (05:00-07:00): Bird dawn chorus, gentle wind
  Morning (07:00-12:00): Active birds, moderate activity
  Midday  (12:00-14:00): Insects, heat shimmer, less wind
  Afternoon (14:00-17:00): Moderate activity, lengthening shadows
  Dusk    (17:00-19:00): Evening birds, cricket onset
  Night   (19:00-23:00): Crickets, owls, distant activity
  Late Night (23:00-03:00): Minimal, deep quiet, occasional sounds
  Pre-Dawn (03:00-05:00): Early birds begin, stillness

Transition:
  - Crossfade between period ambient beds over 30-60 seconds
  - Detail layer sounds swap gradually (remove day sounds, add night)
  - Event layer adjusts probabilities per period
```

#### Weather Systems

```
Weather States:
  Clear     -> base ambient + sun/wind detail
  Cloudy    -> muted base, wind increase
  Light Rain -> rain layer (gentle), reduced birds
  Heavy Rain -> rain layer (intense), thunder events, no birds
  Storm     -> rain + wind + thunder + lightning flash cues
  Snow      -> muted base, wind, crunch detail (footsteps change)
  Fog       -> dampened base, increased reverb, reduced detail range

Layering:
  Each weather state adds/modifies:
  - Base ambient modification (EQ, volume)
  - Weather-specific loop (rain, wind)
  - Weather events (thunder with random timing)
  - Effect on other sounds (rain adds reverb/filtering)
```

### 5.5 UI Sounds

#### Consistent Sonic Palette

```
Choose ONE synthesis approach and use it across all UI sounds:
  - Subtractive synthesis: warm, analog feel (RPGs, narrative games)
  - FM synthesis: clean, digital, precise (sci-fi, tech themes)
  - Granular: organic, textured (nature themes, art games)
  - Physical modeling: realistic, tactile (simulation games)
  - Sample-based: flexible, can match any aesthetic

Consistency Checklist:
  - Same reverb/room character across all UI sounds
  - Shared frequency range (avoid outliers)
  - Consistent volume envelope shape
  - Related tonal elements (same scale, harmonics)
```

#### Micro-Feedback Sound Design

| Action          | Character            | Duration | Pitch/Tone          |
|-----------------|----------------------|----------|---------------------|
| Hover           | Soft, subtle         | 30-80ms  | Mid-high, gentle    |
| Press/Click     | Crisp, defined       | 50-120ms | Mid, satisfying snap|
| Release         | Light, airy          | 30-60ms  | Slightly higher     |
| Success/Confirm | Warm, ascending      | 200-400ms| Ascending interval  |
| Error/Deny      | Harsh, dissonant     | 150-300ms| Descending, buzzy   |
| Toggle On       | Bright, activating   | 80-150ms | Higher pitch        |
| Toggle Off      | Muted, deactivating  | 80-150ms | Lower pitch         |
| Slider Move     | Continuous, tonal    | Per frame| Pitch maps to value |
| Tab Switch      | Quick, lateral       | 50-100ms | Neutral, clean      |
| Back/Cancel     | Retreating, soft     | 100-200ms| Descending, quiet   |
| Notification    | Attention-getting    | 300-600ms| Distinctive, clear  |
| Reward/Unlock   | Celebratory, layered | 500-1500ms| Ascending, rich    |

#### Duration Guidelines

```
Ultra-short (<100ms):
  Hover, focus changes, minor state changes

Short (100-200ms):
  Button clicks, toggles, tab switches, selections

Medium (200-500ms):
  Confirmations, success/error feedback, menu open/close

Long (500ms-1.5s):
  Rewards, achievements, level complete, notifications

Very Long (>1.5s):
  Avoid for UI unless it's a celebration or critical alert
  Always allow interruption for very long UI sounds
```

#### Frequency Range Guidelines

```
Avoid:
  - Sub-bass (<80 Hz): inaudible on most devices, wastes energy
  - Ultra-high (>12 kHz): fatiguing, may cause discomfort

Prefer:
  - Mid-range (500 Hz - 4 kHz): clearest on all devices
  - Mid-high (2 kHz - 8 kHz): presence, clarity, attention

Mobile Considerations:
  - Phone speakers reproduce ~200 Hz - 15 kHz
  - Fundamental frequencies should be above 300 Hz
  - Use harmonics to imply bass (psychoacoustic bass)
  - Test on actual device speakers, not just headphones
```

---

## 6. Asset Naming Conventions

### Standard Format

```
{category}_{context}_{descriptor}_{variation}.{ext}
```

### Category Prefixes

| Prefix | Category          | Example                              |
|--------|-------------------|--------------------------------------|
| `sfx`  | Sound Effects     | `sfx_player_jump_01.wav`             |
| `bgm`  | Background Music  | `bgm_level1_exploration_loop.ogg`    |
| `vo`   | Voice / Dialogue  | `vo_npc_merchant_greeting_01.wav`    |
| `amb`  | Ambient           | `amb_forest_daytime_base.ogg`        |
| `ui`   | UI Sounds         | `ui_button_click_01.wav`             |
| `mus`  | Music Stinger     | `mus_stinger_victory_01.ogg`         |
| `fol`  | Foley             | `fol_cloth_rustle_light_01.wav`      |

### Context Examples

```
Player actions:      player_jump, player_attack, player_death
NPC:                 npc_guard, npc_merchant, npc_villager
Weapon:              weapon_sword, weapon_rifle, weapon_bow
Vehicle:             vehicle_car, vehicle_helicopter
Environment:         env_door, env_switch, env_explosion
Level/Location:      level1, dungeon, forest, city
Menu:                menu_main, menu_pause, menu_inventory
```

### Descriptor Examples

```
Action:              attack, hit, miss, block, dodge, idle
State:               start, stop, loop, intro, outro
Modifier:            heavy, light, fast, slow, big, small
Material:            metal, wood, stone, glass, flesh
Surface:             concrete, grass, gravel, water
```

### Variation Numbering

```
Always use zero-padded two-digit numbers:
  sfx_player_footstep_concrete_01.wav
  sfx_player_footstep_concrete_02.wav
  sfx_player_footstep_concrete_03.wav

For large sets (>99 variations), use three digits:
  fol_crowd_chatter_001.wav

Special suffixes:
  _loop     : file is designed to loop seamlessly
  _oneshot  : file plays once (optional, assumed default)
  _intro    : introductory segment before loop
  _outro    : ending segment after loop
  _lfe      : LFE (subwoofer) channel content
```

### Localization Suffix

```
Append language code before extension for voice files:
  vo_npc_merchant_greeting_01_en.wav
  vo_npc_merchant_greeting_01_ja.wav
  vo_npc_merchant_greeting_01_de.wav

Or use directory structure:
  audio/vo/en/npc_merchant_greeting_01.wav
  audio/vo/ja/npc_merchant_greeting_01.wav
```

### Directory Structure

```
audio/
  sfx/
    player/
    npc/
    weapon/
    environment/
    vehicle/
  bgm/
    menu/
    level1/
    level2/
    boss/
    cutscene/
  vo/
    en/
      npc/
      player/
      narrator/
    ja/
      npc/
      player/
      narrator/
  amb/
    forest/
    city/
    dungeon/
    weather/
  ui/
    button/
    notification/
    menu/
  mus/
    stingers/
    transitions/
```

---

## 7. Memory Budget Guidelines Per Platform

### Budget Overview

| Platform   | Total Audio Budget | Streaming BGM   | Loaded SFX    | Voice Strategy |
|------------|-------------------|------------------|---------------|----------------|
| Desktop PC | 500 MB - 2 GB    | 128-256 kbps OGG | WAV or OGG    | Stream         |
| Mobile     | 50 - 200 MB      | 96-128 kbps OGG/AAC | OGG mono  | Stream         |
| Web        | 20 - 50 MB       | 128 kbps MP3+OGG | MP3 or OGG   | Stream         |
| Console    | 256 MB - 1 GB    | 128-256 kbps     | Platform codec | Stream        |
| VR         | 256 MB - 1 GB    | 128-256 kbps OGG | WAV or OGG    | Stream        |

### Format Selection Guide

| Format   | Quality   | Size      | Decode CPU | Browser Support   | Use Case            |
|----------|-----------|-----------|------------|-------------------|---------------------|
| WAV      | Lossless  | Large     | None       | Universal         | SFX source, desktop |
| OGG      | Lossy     | Small     | Low        | Most (not Safari) | BGM, desktop/mobile |
| MP3      | Lossy     | Small     | Low        | Universal         | Web fallback        |
| AAC      | Lossy     | Small     | Low        | Safari/iOS/Android| Mobile primary      |
| FLAC     | Lossless  | Medium    | Low        | Most              | Archival, desktop   |
| Opus     | Lossy     | Very small| Low        | Most modern       | Voice, streaming    |
| ADPCM    | Lossy     | Medium    | Very low   | Engine-specific   | Console SFX         |

### Bitrate Guidelines

| Content Type         | Minimum    | Recommended | High Quality |
|----------------------|------------|-------------|--------------|
| BGM (stereo)         | 96 kbps    | 128 kbps    | 192-256 kbps |
| BGM (mono)           | 64 kbps    | 96 kbps     | 128 kbps     |
| SFX (stereo)         | 96 kbps    | 128 kbps    | WAV/FLAC     |
| SFX (mono)           | 48 kbps    | 64 kbps     | WAV/FLAC     |
| Voice (mono)         | 48 kbps    | 64 kbps     | 96 kbps      |
| Ambient (stereo)     | 96 kbps    | 128 kbps    | 160 kbps     |
| UI (mono)            | 48 kbps    | 64 kbps     | WAV          |

### Sample Rate Guidelines

| Content        | Mobile    | Desktop   | Notes                       |
|----------------|-----------|-----------|-----------------------------|
| BGM            | 44.1 kHz  | 44.1 kHz  | Standard music rate         |
| SFX            | 22.05 kHz | 44.1 kHz  | Lower rate OK for mobile    |
| Voice          | 22.05 kHz | 44.1 kHz  | Intelligible at lower rates |
| Ambient        | 22.05 kHz | 44.1 kHz  | Background, less critical   |
| UI             | 22.05 kHz | 44.1 kHz  | Short, simple sounds        |

### Mono vs Stereo Decision Matrix

| Content             | Mobile  | Desktop/Console | Rationale                    |
|---------------------|---------|-----------------|------------------------------|
| BGM                 | Stereo  | Stereo          | Musical width important      |
| SFX (3D positioned) | Mono    | Mono            | Engine handles spatialization|
| SFX (2D / global)   | Mono    | Stereo          | Save memory on mobile        |
| Voice               | Mono    | Mono            | Center-panned, save space    |
| Ambient (positioned)| Mono    | Mono            | Spatialized by engine        |
| Ambient (global bed)| Stereo  | Stereo          | Width for immersion          |
| UI                  | Mono    | Mono            | No spatial positioning       |

### Memory Optimization Strategies

```
1. Streaming vs. Pre-loaded
   Stream:  BGM, long ambient loops, dialogue, cutscene audio
   Preload: SFX, UI sounds, short stingers, frequent barks
   Rule:    Stream anything > 5 seconds; preload anything < 5 seconds

2. Compression
   - Mobile: OGG Vorbis q2-q4 (64-96 kbps mono)
   - Desktop: OGG Vorbis q5-q7 (128-192 kbps stereo)
   - Web: Provide both MP3 and OGG for browser compatibility

3. Pooling and Unloading
   - Load audio per-level/per-scene
   - Unload previous level's audio on scene transition
   - Pool common sounds (footsteps, UI) in persistent memory
   - Use reference counting to prevent premature unloading

4. Reduction Techniques
   - Convert stereo SFX to mono (50% size reduction)
   - Reduce sample rate for non-critical sounds (50% reduction)
   - Trim silence from file start/end
   - Shorter variation count on mobile (3 instead of 6)
```

### ffmpeg Format Conversion Commands

```bash
# WAV to OGG (quality 4, good for desktop)
ffmpeg -i input.wav -c:a libvorbis -q:a 4 output.ogg

# WAV to OGG (quality 2, good for mobile)
ffmpeg -i input.wav -c:a libvorbis -q:a 2 -ac 1 -ar 22050 output_mobile.ogg

# WAV to MP3 (128kbps, web fallback)
ffmpeg -i input.wav -c:a libmp3lame -b:a 128k output.mp3

# WAV to AAC (96kbps, iOS/Android)
ffmpeg -i input.wav -c:a aac -b:a 96k -ac 1 output.m4a

# WAV to Opus (64kbps, voice/streaming)
ffmpeg -i input.wav -c:a libopus -b:a 64k output.opus

# Stereo to Mono
ffmpeg -i input_stereo.wav -ac 1 output_mono.wav

# Resample to 22.05 kHz
ffmpeg -i input.wav -ar 22050 output_22k.wav

# Batch convert directory
for f in *.wav; do
  ffmpeg -i "$f" -c:a libvorbis -q:a 4 "${f%.wav}.ogg" -y
done

# Trim silence from start and end
ffmpeg -i input.wav -af silenceremove=start_periods=1:start_silence=0.05:\
start_threshold=-50dB,areverse,silenceremove=start_periods=1:\
start_silence=0.05:start_threshold=-50dB,areverse output.wav
```

---

## 8. Audio Implementation Checklist

### 8.1 Pre-Production Checklist

```
[ ] Define audio style guide (genre, mood, reference games/tracks)
[ ] Establish target platforms and memory budgets
[ ] Choose audio middleware (FMOD, Wwise, Unity Audio, custom)
[ ] Define asset naming convention (see Section 6)
[ ] Create directory structure template
[ ] Identify required sound categories and estimated asset counts
[ ] Plan adaptive music system complexity level
[ ] Define voice pipeline (casting, recording, processing)
[ ] Establish loudness standards and QC process
[ ] Document audio bus hierarchy and routing
[ ] Plan localization requirements (languages, voice recording)
[ ] Create asset tracking spreadsheet/database
[ ] Set milestone deliverables and review cadence
```

### 8.2 Production Checklist

```
Asset Creation:
[ ] All SFX layered with transient + body + tail where appropriate
[ ] Minimum variation count met per SFX priority tier
[ ] BGM loops tested for seamless playback (10+ minute test)
[ ] BGM stems aligned and synchronized
[ ] Dialogue processed through full pipeline (edit > de-ess > compress > normalize)
[ ] Ambient loops tested for seamlessness
[ ] UI sounds consistent in palette, volume, and duration
[ ] Stingers composed and timed to game events

Technical:
[ ] All assets meet loudness standards (+/- tolerance for tier)
[ ] True peak below -1 dBTP on all assets
[ ] Correct sample rate and bit depth per platform target
[ ] File format matches platform requirements
[ ] Naming convention followed consistently
[ ] No clipping or digital distortion in any asset
[ ] Silence trimmed from file boundaries
[ ] Loop points verified in target engine/player
```

### 8.3 Integration Checklist

```
Engine Setup:
[ ] Audio bus hierarchy created (Master > Music, SFX, Voice, UI, Ambient)
[ ] Per-bus compression and EQ configured
[ ] Ducking system configured (voice ducks music)
[ ] Voice priority/stealing system tested
[ ] Spatial audio configured (distance models, HRTF if applicable)
[ ] Reverb zones placed and tuned
[ ] Occlusion/obstruction system tested

Gameplay Integration:
[ ] Player actions trigger correct SFX
[ ] Footstep system responds to surface type
[ ] Dialogue triggers and sequences function correctly
[ ] Music state machine transitions tested for all state pairs
[ ] Ambient layers respond to time-of-day and weather
[ ] UI sounds attached to all interactive elements
[ ] Stingers trigger on correct game events
[ ] Volume controls (sliders) functional and saved to preferences

Platform:
[ ] Memory budget within limits on target platform
[ ] No audio dropouts or glitches during stress tests
[ ] Streaming audio loads without gaps or delays
[ ] Headphone and speaker output both sound correct
```

### 8.4 QC Pass Requirements by Quality Tier

#### Tier 1: AAA Quality

```
Loudness:
[ ] Every asset measured and within +/- 0.5 LU of target
[ ] True peak verified with EBU R128 compliant metering
[ ] Full LRA analysis per category

Technical:
[ ] Zero clipping across entire asset library
[ ] All loops verified with automated loop-point checker
[ ] Spectral analysis on all assets (no DC offset, no ultrasonic noise)
[ ] A/B comparison with reference tracks per category

Gameplay:
[ ] Full playthrough recording analyzed for mix balance
[ ] Blind listening test with 3+ testers
[ ] Accessibility review (subtitles, visual audio cues)
[ ] Platform certification requirements met
[ ] Localization audio QC per language

Performance:
[ ] Memory profiling on minimum-spec hardware
[ ] CPU profiling of audio thread under load
[ ] Latency measurement (input to sound < 50ms for critical SFX)
[ ] Streaming buffer tested on slow storage media
```

#### Tier 2: Standard Quality

```
Loudness:
[ ] Spot-check 20% of assets, all within +/- 1.0 LU
[ ] True peak verified on dialogue and music
[ ] Overall mix balance validated

Technical:
[ ] Manual listen pass on all unique assets
[ ] Loops verified by 3-minute playback test
[ ] No audible artifacts or quality issues

Gameplay:
[ ] Key gameplay moments have audio coverage
[ ] No missing audio for player-facing actions
[ ] Volume sliders function correctly
[ ] Basic accessibility (subtitles present)

Performance:
[ ] Memory within budget on target platform
[ ] No audible dropouts during normal gameplay
[ ] Load times acceptable
```

#### Tier 3: Indie / MVP Quality

```
Loudness:
[ ] All assets roughly in same loudness range (no jarring outliers)
[ ] Music and SFX balanced relative to each other
[ ] No clipping on any asset

Technical:
[ ] Quick listen pass on all assets
[ ] Loops play without obvious clicks
[ ] Correct format for target platform

Gameplay:
[ ] Core gameplay actions have sound feedback
[ ] Music plays and loops correctly
[ ] At least master volume control works

Performance:
[ ] Game runs without audio-related crashes
[ ] Audio loads without blocking gameplay
```

### 8.5 Common Audio Bugs to Check

```
Critical:
- Audio causes crash or hang
- Memory leak from unreleased audio handles
- Audio continues playing after scene unload
- Stuck looping sounds that cannot be stopped

Major:
- Missing audio for player actions
- Wrong sound plays for an event
- Music doesn't transition between states
- Volume spikes (sudden loud sounds)
- Audio desync with animation/visuals

Minor:
- Audible loop point click
- Variation randomization not working (same sound repeats)
- Slight delay on UI sound feedback
- Reverb doesn't change between spaces
- Footstep sound doesn't match surface

Polish:
- Ducking too aggressive or too subtle
- Transition timing slightly off
- Spatial audio falloff feels unnatural
- Ambient detail sounds too frequent/infrequent
```

---

## Quick Reference: Key Numbers

```
Loudness:
  Game:     -23 LUFS (EBU R128)
  Mobile:   -16 LUFS
  Peak:     -1 dBTP

Mix Levels (relative to dialogue):
  Voice:     0 dB (reference)
  SFX:      -6 dB
  UI:       -9 dB
  BGM:     -12 dB
  Ambient: -18 dB

Durations:
  UI click:    50-120 ms
  UI confirm:  200-400 ms
  SFX impact:  100-500 ms
  Bark:        <3 seconds
  BGM loop:    30-120 seconds
  Ambient loop: 60-180 seconds

Variations:
  Critical SFX:  5-8
  Standard SFX:  3-5
  Background:    2-3

Voice Count:
  Mobile:  16-32
  Console: 64-128
  PC:      128-256
```

---

*This reference is maintained as part of the Tone game audio agent ecosystem.
For generation-specific patterns, see the Tone SKILL.md and related references.*

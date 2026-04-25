# Suno AI Prompt Guide for Game BGM

Comprehensive reference for crafting Suno AI prompts optimized for game background music generation. Covers prompt structure, metatags, genre templates, and game-specific patterns.

## Suno AI Overview

| Attribute | Detail |
|-----------|--------|
| **Provider** | Suno AI |
| **Strength** | Full song / instrumental BGM from text prompts with vocal + instrumental separation |
| **Category** | BGM (primary), Ambient |
| **Input** | Style prompt + optional lyrics with metatags |
| **Pricing** | Credit-based (~10 credits/generation, plans from free tier to $30/mo) |
| **Output** | MP3/WAV (stereo, 48kHz) |
| **Duration** | Up to 4 minutes per generation |
| **Latest Model** | Suno v5.5 (March 2026) |

### When to Choose Suno AI over Other Providers

| Scenario | Suno AI | Stable Audio | MusicGen |
|----------|---------|--------------|---------|
| Full song with structure (intro→verse→chorus→outro) | Best | Limited | No |
| Instrumental game BGM with genre control | Excellent | Good | Good |
| Loop-friendly ambient tracks | Good | Best | Good |
| Specific BPM/key control | Via style tags | Direct param | Direct param |
| Stem separation (vocal/instrument) | Built-in | No | No |
| Cost per generation | ~$0.10-0.30 | ~$0.03-0.10 | ~$0.02-0.08 |

**Use Suno when:** You need structured, genre-specific game BGM with rich instrumentation and arrangement control.
**Use Stable Audio when:** You need precise duration control, seamless loops, or lower cost per generation.
**Use MusicGen when:** You need melody continuation or local/offline generation.

---

## Prompt Architecture

Suno separates input into two distinct fields in Custom Mode:

### 1. Style Prompt (Sonic Blueprint)

Defines the overall sound. Use comma-separated descriptors, not prose sentences.

**Formula:** `[Genre] + [Tempo-feel] + [Instruments] + [Vocal intent] + [Mix intent] + [Mood axis]`

**Rules:**
- Keep it about **sound only** — no story, no lyrics, no production notes
- Place the most important descriptors first (first 20-30 words have strongest impact)
- Use 4-8 style tags for best results
- Too few tags = too much AI freedom; too many tags = conflicting signals
- Describe, don't command (write "epic orchestral" not "create an epic orchestral track")

### 2. Lyrics Field (Structure + Words)

For game BGM, use this field exclusively for **metatags** (structure tags) since BGM is typically instrumental.

**Critical rule:** Keep the style prompt about sound, keep the lyrics prompt about lyrics and structure.

---

## Metatags Reference

Metatags are bracketed `[Tag]` directives placed in the lyrics field to control song structure and arrangement.

### Structure Tags

| Tag | Purpose | Game BGM Usage |
|-----|---------|----------------|
| `[Intro]` | Instrumental opening, 8-16 bars | Menu screen fade-in |
| `[Instrumental Intro]` | Explicitly instrumental opening | Title screen music |
| `[Verse]` | Main narrative section | Exploration phase |
| `[Pre-Chorus]` | Build-up before chorus | Tension escalation |
| `[Chorus]` | Main hook / repeated section | Action climax |
| `[Bridge]` | Contrasting mid-song variation | Scene transition |
| `[Break]` | Stripped-down contrast | Quiet moment |
| `[Build]` / `[Buildup]` | Tension increase | Pre-boss encounter |
| `[Drop]` | High-energy release (EDM/electronic) | Boss phase transition |
| `[Instrumental]` | Vocal-free section | General BGM body |
| `[Solo]` | Featured instrument spotlight | Victory fanfare |
| `[Outro]` | Closing section | Level complete |
| `[Fade Out]` | Gradual volume decrease | Scene end |
| `[End]` | Abrupt stop | Game over |

### Instrumental / BGM Control Tags

For game BGM, always set **Instrumental: ON** in Suno's UI, or use these tags:

```
[Instrumental]
[Intro]
[Verse]
[Chorus]
[Bridge]
[Outro]
[Fade Out]
```

### Mood & Energy Tags

| Tag | Effect | Game Context |
|-----|--------|--------------|
| `[Uplifting]` | Positive, inspiring | Victory, reward |
| `[Melancholic]` | Sad, reflective | Story cutscene, loss |
| `[Dark]` | Brooding, ominous | Dungeon, villain |
| `[Epic]` | Grand, heroic | Boss fight, finale |
| `[Nostalgic]` | Wistful, retrospective | Flashback, memories |
| `[Dreamy]` | Ethereal, hazy | Dream sequence |
| `[Intimate]` | Personal, close | Dialogue, campfire |
| `[Driving]` | Propulsive forward motion | Chase, racing |
| `[High Energy]` | Maximum intensity | Combat, action |
| `[Chill]` | Minimal, relaxed | Shop, safe zone |
| `[Atmospheric]` | Spacious, ambient | Exploration, open world |
| `[Tense]` | Suspenseful | Stealth, horror |

### Texture & Production Tags

| Tag | Effect |
|-----|--------|
| `[Lo-fi]` | Warm, degraded quality |
| `[Clean]` | Polished, clear |
| `[Lush]` | Rich, full sound |
| `[Sparse]` | Minimal, open |
| `[Punchy]` | Tight, impactful |
| `[Warm]` | Rich low-mids |
| `[Bright]` | Enhanced highs |

---

## Genre Tags for Game BGM

### Action / Combat

| Style Prompt | Game Context |
|--------------|--------------|
| `epic orchestral, 140 bpm, driving percussion, brass fanfare, cinematic, high energy` | Boss fight |
| `heavy metal, aggressive drums, distorted guitar, 160 bpm, intense` | Action combat |
| `electronic rock, synth bass, punchy drums, 130 bpm, adrenaline` | Mech combat |
| `drum and bass, breakbeat, dark synths, 174 bpm, relentless` | Chase sequence |

### Exploration / Overworld

| Style Prompt | Game Context |
|--------------|--------------|
| `orchestral, gentle strings, flute melody, 90 bpm, adventurous, warm` | Overworld map |
| `indie folk, acoustic guitar, soft percussion, 100 bpm, wanderlust` | Village exploration |
| `ambient electronic, synth pads, gentle arpeggios, 80 bpm, atmospheric` | Sci-fi exploration |
| `celtic folk, fiddle, bodhrán, tin whistle, 110 bpm, joyful` | Fantasy village |

### Menu / UI

| Style Prompt | Game Context |
|--------------|--------------|
| `lo-fi chill, piano, soft synth pad, 75 bpm, relaxed, warm` | Main menu |
| `ambient, ethereal pads, minimal, 60 bpm, dreamy` | Title screen |
| `jazz lounge, smooth piano, upright bass, brush drums, 85 bpm` | Character select |
| `synthwave, retro synths, 100 bpm, nostalgic, neon` | Retro game menu |

### Horror / Suspense

| Style Prompt | Game Context |
|--------------|--------------|
| `dark ambient, dissonant strings, low drone, atonal, unsettling` | Horror exploration |
| `industrial, metallic percussion, distorted textures, 90 bpm, oppressive` | Industrial horror |
| `minimal, sparse piano, reverb, 50 bpm, eerie silence` | Psychological horror |

### Puzzle / Casual

| Style Prompt | Game Context |
|--------------|--------------|
| `chiptune, 8-bit synths, upbeat, 120 bpm, playful` | Retro puzzle |
| `marimba, xylophone, light percussion, 110 bpm, cheerful` | Casual puzzle |
| `bossa nova, acoustic guitar, light jazz, 95 bpm, pleasant` | Relaxing puzzle |

### Victory / Defeat

| Style Prompt | Game Context |
|--------------|--------------|
| `orchestral fanfare, triumphant brass, timpani, 120 bpm, heroic` | Victory theme |
| `melancholic strings, slow piano, 60 bpm, somber` | Defeat / game over |
| `uplifting pop-rock, bright guitar, 130 bpm, celebratory` | Level complete |

---

## Game BGM Prompt Crafting Best Practices

### 1. Use Decades for Sonic Precision

Adding era descriptors dramatically changes output:

- `80s synthwave` → retro arcade feel with analog synths
- `90s boom bap` → nostalgic hip-hop rhythm
- `2000s trance` → euphoric electronic energy
- `70s prog rock` → complex arrangements, long passages

### 2. Instrument Limitation Rule

Mention **2-4 key instruments** for best results. Too many creates conflicting output.

```
Good:  "orchestral, strings, French horn, timpani"
Bad:   "orchestral, strings, French horn, timpani, flute, oboe, clarinet, harp, celesta, glockenspiel"
```

### 3. Avoid Conflicting Tags

Never combine contradictory descriptors:

| Conflict | Problem |
|----------|---------|
| `[High Energy]` + `[Chill]` | Contradictory energy levels |
| `[Fast]` + `[Slow Ballad]` | Contradictory tempo |
| `[Aggressive]` + `[Peaceful]` | Contradictory mood |
| `[Lo-fi]` + `[Clean]` | Contradictory production |

### 4. Front-Load Critical Descriptors

The first 20-30 words of the style prompt have the strongest influence on output.

```
Good:  "epic orchestral, 140 bpm, cinematic, driving percussion, brass, dark fantasy"
Bad:   "a track that could work for a dark fantasy game with epic orchestral instruments at 140 bpm"
```

### 5. Loopable BGM Strategy

For game BGM that needs to loop seamlessly:

**Style prompt approach:**
```
ambient electronic, seamless loop, steady groove, consistent texture, 90 bpm, atmospheric
```

**Structure tag approach (lyrics field):**
```
[Instrumental]
[Intro]
[Verse]
[Verse]
[Outro]
[Fade Out]
```

**Post-processing (via ffmpeg):**
After Suno generates the track, use crossfade processing for seamless loops — see `format-optimization.md`.

### 6. Adaptive Music Layers

Generate multiple Suno tracks with the same genre but different energy levels for adaptive/dynamic music:

```
# Low intensity (exploration)
Style: "orchestral, gentle strings, soft flute, 80 bpm, peaceful, sparse"

# Medium intensity (alert)
Style: "orchestral, strings, snare roll, 80 bpm, tense, building"

# High intensity (combat)
Style: "orchestral, full brass, driving percussion, 80 bpm, epic, intense"
```

Keep **tempo and key** consistent across layers for smooth transitions.

### 7. Prompt Library Pattern

Maintain reusable base prompts and swap single variables:

```
# Base: Fantasy overworld
Base: "orchestral, [LEAD_INSTRUMENT], [PERCUSSION], [BPM] bpm, [MOOD], fantasy"

# Variation 1: Forest
"orchestral, flute melody, light percussion, 90 bpm, serene, fantasy"

# Variation 2: Mountain
"orchestral, French horn, timpani, 100 bpm, majestic, fantasy"

# Variation 3: Swamp
"orchestral, bassoon, muted drums, 75 bpm, mysterious, fantasy"
```

---

## Suno API Integration

### Unofficial API (suno-api)

Suno does not currently offer an official public API. The community-maintained `suno-api` project provides a reverse-engineered interface.

**Environment Variables:**

| Variable | Description |
|----------|-------------|
| `SUNO_COOKIE` | Browser session cookie from suno.com |
| `SUNO_BASE_URL` | API server URL (default: `http://localhost:3000`) |

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate` | POST | Generate from simple text prompt |
| `/api/custom_generate` | POST | Generate with style + lyrics + title |
| `/api/get?ids=` | GET | Retrieve generation status and audio URL |
| `/api/get_limit` | GET | Check remaining credits |
| `/api/extend_audio` | POST | Extend existing audio |
| `/api/generate_stems` | POST | Separate vocal and instrumental stems |

### Python Integration

```python
import os
import time
import httpx


SUNO_BASE_URL = os.environ.get("SUNO_BASE_URL", "http://localhost:3000")
SUNO_COOKIE = os.environ["SUNO_COOKIE"]


def generate_game_bgm(
    style_prompt: str,
    title: str = "Game BGM",
    make_instrumental: bool = True,
    structure_tags: str = "",
) -> dict:
    """Generate game BGM via Suno API.

    Args:
        style_prompt: Genre + tempo + instruments + mood (no prose).
        title: Track title for metadata.
        make_instrumental: True for BGM without vocals.
        structure_tags: Metatag structure (e.g. "[Intro]\\n[Verse]\\n[Chorus]\\n[Outro]").

    Returns:
        dict with generation IDs and status.
    """
    # Cost estimate: ~10 credits per generation (2 variations)
    payload = {
        "prompt": style_prompt,
        "tags": style_prompt,
        "title": title,
        "make_instrumental": make_instrumental,
        "wait_audio": False,
    }
    if structure_tags:
        payload["prompt"] = structure_tags

    response = httpx.post(
        f"{SUNO_BASE_URL}/api/custom_generate",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def poll_suno_result(audio_ids: str, max_attempts: int = 60, interval: float = 5.0) -> list:
    """Poll until Suno generation completes.

    Args:
        audio_ids: Comma-separated generation IDs.
        max_attempts: Maximum polling attempts.
        interval: Seconds between polls.

    Returns:
        List of completed audio objects with audio_url.
    """
    for _ in range(max_attempts):
        response = httpx.get(
            f"{SUNO_BASE_URL}/api/get?ids={audio_ids}",
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json()

        if all(r.get("status") == "streaming" for r in results):
            return results

        time.sleep(interval)

    raise TimeoutError(f"Suno generation did not complete within {max_attempts * interval}s")


def check_suno_credits() -> dict:
    """Check remaining Suno credits."""
    response = httpx.get(f"{SUNO_BASE_URL}/api/get_limit", timeout=10.0)
    response.raise_for_status()
    return response.json()


# --- Usage Example: Battle BGM ---
if __name__ == "__main__":
    # Check credits before generating
    credits = check_suno_credits()
    print(f"Credits remaining: {credits.get('credits_left', 'unknown')}")

    # Generate battle BGM
    result = generate_game_bgm(
        style_prompt="epic orchestral, 140 bpm, driving percussion, brass fanfare, cinematic, high energy, dark fantasy",
        title="Battle Theme - Dark Forest",
        make_instrumental=True,
        structure_tags="[Instrumental]\n[Intro]\n[Verse]\n[Chorus]\n[Bridge]\n[Chorus]\n[Outro]",
    )

    # Poll for completion
    ids = ",".join(r["id"] for r in result)
    completed = poll_suno_result(ids)
    for track in completed:
        print(f"Track: {track['title']} -> {track['audio_url']}")
```

### JavaScript/TypeScript Integration

```typescript
const SUNO_BASE_URL = process.env.SUNO_BASE_URL ?? "http://localhost:3000";

interface SunoGenerateParams {
  stylePrompt: string;
  title?: string;
  makeInstrumental?: boolean;
  structureTags?: string;
}

interface SunoResult {
  id: string;
  status: string;
  title: string;
  audio_url: string;
}

async function generateGameBGM({
  stylePrompt,
  title = "Game BGM",
  makeInstrumental = true,
  structureTags = "",
}: SunoGenerateParams): Promise<SunoResult[]> {
  const payload: Record<string, unknown> = {
    prompt: structureTags || stylePrompt,
    tags: stylePrompt,
    title,
    make_instrumental: makeInstrumental,
    wait_audio: false,
  };

  const res = await fetch(`${SUNO_BASE_URL}/api/custom_generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) throw new Error(`Suno API error: ${res.status}`);
  return res.json();
}

async function pollSunoResult(
  audioIds: string,
  maxAttempts = 60,
  intervalMs = 5000,
): Promise<SunoResult[]> {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`${SUNO_BASE_URL}/api/get?ids=${audioIds}`);
    if (!res.ok) throw new Error(`Suno poll error: ${res.status}`);

    const results: SunoResult[] = await res.json();
    if (results.every((r) => r.status === "streaming")) return results;

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Suno generation timed out");
}
```

---

## Post-Processing Pipeline for Game BGM

After generating with Suno, apply standard game audio post-processing:

```bash
#!/bin/bash
# Post-process Suno BGM for game integration
# Usage: ./process_suno_bgm.sh input.mp3 output_name

INPUT="$1"
OUTPUT_NAME="${2:-processed_bgm}"

# 1. Convert to WAV (game-engine-friendly)
ffmpeg -i "$INPUT" -ar 44100 -ac 2 "${OUTPUT_NAME}_raw.wav"

# 2. LUFS normalize to -23 LUFS (game standard)
ffmpeg -i "${OUTPUT_NAME}_raw.wav" \
  -af loudnorm=I=-23:TP=-1:LRA=11 \
  "${OUTPUT_NAME}_normalized.wav"

# 3. Trim silence from start/end
ffmpeg -i "${OUTPUT_NAME}_normalized.wav" \
  -af "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,areverse" \
  "${OUTPUT_NAME}_trimmed.wav"

# 4. Create loop-ready version (crossfade last 2s with first 2s)
DURATION=$(ffprobe -i "${OUTPUT_NAME}_trimmed.wav" -show_entries format=duration -v quiet -of csv="p=0")
FADE_DURATION=2
ffmpeg -i "${OUTPUT_NAME}_trimmed.wav" \
  -af "afade=t=in:st=0:d=${FADE_DURATION},afade=t=out:st=$(echo "$DURATION - $FADE_DURATION" | bc):d=${FADE_DURATION}" \
  "${OUTPUT_NAME}_loop.wav"

# 5. Export game formats
ffmpeg -i "${OUTPUT_NAME}_loop.wav" -c:a libvorbis -q:a 6 "${OUTPUT_NAME}.ogg"   # Desktop/Console
ffmpeg -i "${OUTPUT_NAME}_loop.wav" -c:a aac -b:a 192k "${OUTPUT_NAME}.m4a"       # Mobile
ffmpeg -i "${OUTPUT_NAME}_loop.wav" -c:a libopus -b:a 128k "${OUTPUT_NAME}.opus"  # Web

echo "Done: ${OUTPUT_NAME}.ogg / .m4a / .opus"
```

---

## Anti-Patterns for Suno Game BGM

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Prose-style prompts | "Please create an epic battle song for my RPG" | Use comma-separated tags: "epic orchestral, battle, RPG, 140 bpm" |
| Overstuffed style prompt | 10+ genre tags + 8 instruments + 5 moods | Limit to 1-2 genres, 2-4 instruments, 1-2 moods |
| No structure tags for BGM | Suno decides arrangement randomly | Always provide `[Intro] [Verse] [Chorus] [Outro]` structure |
| Conflicting descriptors | "aggressive chill dark uplifting" | Pick one mood axis per generation |
| Ignoring instrumental flag | Gets vocals in game BGM | Always set `make_instrumental: true` |
| Single generation | Relying on one output | Generate 3+ variations and pick best |
| Skipping post-processing | Raw Suno output in game | Always normalize LUFS + trim + format convert |
| No tempo consistency | Different BPMs across game areas | Define BPM palette per game (e.g., explore=80, combat=140) |

---

## Licensing Notes

- Suno free tier: generated music is **not** commercially licensable.
- Suno Pro/Premier plans: generated music **can** be used commercially, including in games.
- Always verify current licensing terms at suno.com before shipping.
- The unofficial suno-api uses cookie-based authentication and may violate Suno's ToS — evaluate risk for production use.
- For production games, consider generating with Suno for prototyping/direction, then commissioning or using officially licensed alternatives.

---

## Sources

- [How to Structure Prompts for Suno AI](https://howtopromptsuno.com/making-music)
- [Suno Tags List: Complete Guide (Musci.io)](https://musci.io/blog/suno-tags)
- [Complete List of Prompts & Styles for Suno AI (Medium)](https://travisnicholson.medium.com/complete-list-of-prompts-styles-for-suno-ai-music-2024-33ecee85f180)
- [Suno AI Metatags Guide (sunometatagcreator.com)](https://sunometatagcreator.com/metatags-guide)
- [suno-api (GitHub)](https://github.com/gcui-art/suno-api)
- [Guide to Suno AI Prompting: Metatags Explained (TitanXT)](https://www.titanxt.io/post/guide-to-suno-ai-prompting-metatags-explained)
- [Suno AI Music Prompt Guide (AvenueAR)](https://avenuear.com/2025/10/28/suno-ai-music-prompt-guide/)

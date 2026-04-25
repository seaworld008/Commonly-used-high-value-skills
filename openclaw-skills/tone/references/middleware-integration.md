# Audio Middleware Integration Reference

Comprehensive guide to integrating game audio through middleware solutions (FMOD, Wwise)
and native engine audio systems (Unity, Unreal, Godot, Web).

---

## 1. Audio Middleware Overview

### Middleware vs Native Engine Audio

| Feature | FMOD / Wwise | Native Engine Audio |
|---------|-------------|-------------------|
| Adaptive music systems | Built-in, visual authoring | Manual implementation |
| Real-time mixing | Professional-grade DSP | Basic to moderate |
| Designer workflow | Standalone authoring tool | In-engine only |
| Parameter-driven variation | First-class support | Manual scripting |
| Occlusion / propagation | Built-in or plugin | Engine-dependent |
| Cost | Per-title licensing | Free (included) |
| Platform support | All major platforms | Engine-dependent |
| Learning curve | Moderate (separate tool) | Low (integrated) |

### When to Use Middleware

**Choose FMOD or Wwise when:**
- Dedicated sound designers need independent authoring tools
- Complex adaptive music or layered ambience is required
- Advanced DSP chains (convolution reverb, granular synthesis) are needed
- Cross-engine portability matters (same sound design across Unity/UE/custom)
- The project has a large audio asset count requiring bank management

**Choose native engine audio when:**
- The project has simple audio needs (UI sounds, basic SFX, looping BGM)
- Team lacks dedicated audio designers
- Minimizing external dependencies is a priority
- Budget constraints prevent middleware licensing
- Rapid prototyping is the goal

### FMOD vs Wwise Comparison

| Aspect | FMOD Studio | Wwise |
|--------|------------|-------|
| Authoring UI | Timeline + parameter sheets | Actor-Mixer hierarchy |
| Scripting model | Events + parameters | Events + RTPCs + switches |
| Spatial audio | Built-in (resonance) | Built-in + Reflect plugin |
| Pricing | Revenue-based tiers | Revenue-based tiers |
| Indie-friendly | Free under $200K rev | Free under 200 assets |
| Community | Moderate | Large, extensive docs |
| Best for | Music-heavy, small teams | AAA, large asset pipelines |

---

## 2. FMOD Studio Integration

### Unity C# Integration

#### Basic Playback

```csharp
using FMODUnity;
using FMOD.Studio;

public class AudioManager : MonoBehaviour
{
    // Play one-shot (fire-and-forget, auto-released)
    public void PlayExplosion()
    {
        RuntimeManager.PlayOneShot("event:/SFX/Explosion", transform.position);
    }

    // Persistent instance with parameter control
    private EventInstance bgmInstance;

    public void StartBGM()
    {
        bgmInstance = RuntimeManager.CreateInstance("event:/BGM/Level1");
        bgmInstance.setParameterByName("Intensity", 0.8f);
        bgmInstance.start();
    }

    public void SetBGMIntensity(float intensity)
    {
        bgmInstance.setParameterByName("Intensity", intensity);
    }

    public void StopBGM()
    {
        bgmInstance.stop(FMOD.Studio.STOP_MODE.ALLOWFADEOUT);
        bgmInstance.release();
    }
}
```

#### 3D Positioned Audio

```csharp
using FMODUnity;
using FMOD.Studio;

public class FootstepAudio : MonoBehaviour
{
    [EventRef]
    public string footstepEvent = "event:/SFX/Footstep";

    public void PlayFootstep(string surfaceType)
    {
        EventInstance footstep = RuntimeManager.CreateInstance(footstepEvent);
        footstep.set3DAttributes(RuntimeUtils.To3DAttributes(transform));
        footstep.setParameterByNameWithLabel("Surface", surfaceType);
        footstep.start();
        footstep.release(); // Auto-cleanup after playback
    }
}
```

#### Attaching to Moving Objects

```csharp
public class EngineSound : MonoBehaviour
{
    private EventInstance engineInstance;

    void Start()
    {
        engineInstance = RuntimeManager.CreateInstance("event:/SFX/Engine");
        RuntimeManager.AttachInstanceToGameObject(
            engineInstance, transform, GetComponent<Rigidbody>()
        );
        engineInstance.start();
    }

    void OnDestroy()
    {
        engineInstance.stop(FMOD.Studio.STOP_MODE.IMMEDIATE);
        engineInstance.release();
    }
}
```

### Event Design Patterns

#### One-Shot vs Persistent Instances

| Pattern | Use Case | Lifecycle |
|---------|----------|-----------|
| One-shot (`PlayOneShot`) | Short SFX (clicks, hits, pickups) | Auto-released |
| Persistent instance | Looping sounds, parameter-driven | Manual start/stop/release |
| Attached instance | Moving 3D sources (vehicles, NPCs) | Tied to GameObject |

#### Parameter-Driven Variation

FMOD parameters enable dynamic audio behavior without code changes:

```
Parameter: Surface (Labeled)
  Labels: Wood, Metal, Grass, Stone, Water
  -> Each label triggers different samples/processing

Parameter: Speed (Continuous, 0.0 - 1.0)
  -> Crossfades between walk/jog/run layers

Parameter: Damage (Continuous, 0.0 - 1.0)
  -> Increases distortion, reduces high frequencies

Parameter: TimeOfDay (Continuous, 0.0 - 24.0)
  -> Blends between day/night ambience layers
```

#### Snapshots for Global Effects

```csharp
// Apply underwater effect snapshot
EventInstance underwaterSnapshot;

public void EnterWater()
{
    underwaterSnapshot = RuntimeManager.CreateInstance("snapshot:/Underwater");
    underwaterSnapshot.start();
}

public void ExitWater()
{
    underwaterSnapshot.stop(FMOD.Studio.STOP_MODE.ALLOWFADEOUT);
    underwaterSnapshot.release();
}
```

Common snapshot uses:
- **Pause menu**: Low-pass filter + volume reduction on gameplay audio
- **Underwater**: Heavy low-pass, chorus, reverb
- **Indoor/Outdoor**: Reverb and reflection changes
- **Slow motion**: Pitch reduction, reverb increase
- **Focus mode**: Duck all buses except target

#### Bus Routing

```
Master Bus
  +-- BGM (music, adaptive layers)
  +-- SFX (gameplay sound effects)
  |     +-- SFX_Player (footsteps, attacks, abilities)
  |     +-- SFX_Environment (physics, destruction)
  |     +-- SFX_Enemy (enemy actions, deaths)
  +-- Voice (dialogue, narration)
  +-- UI (menu sounds, notifications)
  +-- Ambient (environmental loops, weather)
```

### Bank Management

#### Bank Loading Strategy

```csharp
using FMODUnity;

public class BankLoader : MonoBehaviour
{
    // Master bank: always loaded (contains routing, snapshots, shared assets)
    // Loaded automatically by FMOD Studio Listener

    // Level-specific banks: load/unload per scene
    public void LoadLevelAudio(string levelName)
    {
        RuntimeManager.LoadBank($"Level_{levelName}", true);
        RuntimeManager.LoadBank($"Level_{levelName}_Music", true);
    }

    public void UnloadLevelAudio(string levelName)
    {
        RuntimeManager.UnloadBank($"Level_{levelName}");
        RuntimeManager.UnloadBank($"Level_{levelName}_Music");
    }
}
```

#### Bank Organization

| Bank | Contents | Loading |
|------|----------|---------|
| Master | Bus layout, snapshots, VCAs | Always loaded |
| Master.strings | Event path lookup table | Always loaded |
| SFX_Common | Shared SFX (UI, player basics) | Always loaded |
| Level_Forest | Forest-specific SFX and ambience | Per-scene |
| Level_Forest_Music | Forest BGM stems | Per-scene, streaming |
| VO_Chapter1 | Chapter 1 dialogue | Per-chapter |

---

## 3. Wwise Integration

### SoundBank Structure

#### Bank Hierarchy

```
Init.bnk          -> Engine initialization (always loaded first)
Default.bnk       -> Common events, switches, RTPCs
SFX_Player.bnk    -> Player-related sound events
SFX_Weapons.bnk   -> Weapon sounds
BGM_Level01.bnk   -> Level 1 music
ENV_Forest.bnk    -> Forest ambience
VO_EN_Chapter1.bnk -> English voice-over, chapter 1
```

#### Event Naming Convention

```
Play_SFX_Explosion
Play_SFX_Footstep
Play_BGM_Level1
Stop_BGM_Level1
Pause_BGM_All
Resume_BGM_All
Set_State_GameState_Combat
Set_Switch_Surface_Wood
```

### RTPC (Real-Time Parameter Control)

```cpp
#include <AK/SoundEngine/Common/AkSoundEngine.h>

// Register game object (required before posting events)
AK::SoundEngine::RegisterGameObj(PLAYER_ID, "Player");
AK::SoundEngine::RegisterGameObj(ENEMY_ID, "Enemy_01");

// Set RTPC value (continuous parameter)
AK::SoundEngine::SetRTPCValue("Health", playerHealth, PLAYER_ID);
AK::SoundEngine::SetRTPCValue("Speed", playerSpeed, PLAYER_ID);
AK::SoundEngine::SetRTPCValue("RPM", engineRPM, VEHICLE_ID);

// Post event
AK::SoundEngine::PostEvent("Play_SFX_Jump", PLAYER_ID);

// Post event with callback
AK::SoundEngine::PostEvent(
    "Play_VO_Dialogue",
    NPC_ID,
    AK_EndOfEvent,
    DialogueCallback,
    nullptr
);

// Set 3D position
AkSoundPosition soundPos;
soundPos.SetPosition(x, y, z);
soundPos.SetOrientation(fwdX, fwdY, fwdZ, upX, upY, upZ);
AK::SoundEngine::SetPosition(PLAYER_ID, soundPos);

// Unregister when done
AK::SoundEngine::UnregisterGameObj(PLAYER_ID);
```

### Switch and State Patterns

#### Switch Groups (Per-Object)

Switches change behavior per game object (e.g., different footstep sounds per surface):

```
Switch Group: Surface
  Switches: Wood, Metal, Grass, Stone, Water, Sand, Snow

Switch Group: Weapon_Type
  Switches: Sword, Axe, Staff, Bow, Fist

Switch Group: Material
  Switches: Flesh, Armor, Shield, Wood, Stone
```

```cpp
// Set switch on specific game object
AK::SoundEngine::SetSwitch("Surface", "Wood", PLAYER_ID);
AK::SoundEngine::PostEvent("Play_SFX_Footstep", PLAYER_ID);

AK::SoundEngine::SetSwitch("Surface", "Metal", PLAYER_ID);
AK::SoundEngine::PostEvent("Play_SFX_Footstep", PLAYER_ID);
// Same event, different sound based on switch
```

#### State Groups (Global)

States affect all sounds globally (e.g., game state changes reverb/mix):

```
State Group: GameState
  States: Menu, Exploration, Combat, Boss, Cutscene, GameOver

State Group: Environment
  States: Outdoor, Indoor, Cave, Underwater

State Group: TimeOfDay
  States: Dawn, Day, Dusk, Night
```

```cpp
// Set global state
AK::SoundEngine::SetState("GameState", "Combat");
// All sounds respond: music transitions, SFX volumes shift, reverb changes

AK::SoundEngine::SetState("Environment", "Underwater");
// Low-pass filter engages, reverb changes, ambience swaps
```

### Wwise + Unity Integration

```csharp
using AK.Wwise;

public class WwiseAudioController : MonoBehaviour
{
    public AK.Wwise.Event jumpEvent;
    public AK.Wwise.RTPC healthRTPC;
    public AK.Wwise.Switch surfaceSwitch;

    void Start()
    {
        AkSoundEngine.RegisterGameObj(gameObject);
    }

    public void PlayJump()
    {
        jumpEvent.Post(gameObject);
    }

    public void UpdateHealth(float health)
    {
        healthRTPC.SetValue(gameObject, health);
    }

    public void SetSurface(string surface)
    {
        AkSoundEngine.SetSwitch("Surface", surface, gameObject);
    }

    void OnDestroy()
    {
        AkSoundEngine.UnregisterGameObj(gameObject);
    }
}
```

---

## 4. Native Engine Audio

### Unity AudioSource / AudioMixer

#### Basic AudioSource Setup

```csharp
using UnityEngine;
using UnityEngine.Audio;

public class SFXPlayer : MonoBehaviour
{
    [SerializeField] private AudioMixer masterMixer;
    [SerializeField] private AudioMixerGroup sfxGroup;

    public void PlaySFX(AudioClip clip, Vector3 position)
    {
        GameObject sfxObj = new GameObject("SFX_OneShot");
        sfxObj.transform.position = position;

        AudioSource source = sfxObj.AddComponent<AudioSource>();
        source.clip = clip;
        source.outputAudioMixerGroup = sfxGroup;
        source.spatialBlend = 1.0f;   // Full 3D
        source.rolloffMode = AudioRolloffMode.Logarithmic;
        source.maxDistance = 50f;
        source.Play();

        Destroy(sfxObj, clip.length + 0.1f);
    }

    // Volume control via exposed AudioMixer parameter
    public void SetBGMVolume(float volume)
    {
        // Convert linear (0-1) to decibels
        float dB = volume > 0.0001f ? Mathf.Log10(volume) * 20f : -80f;
        masterMixer.SetFloat("BGMVolume", dB);
    }

    // Snapshot transitions
    public void ApplyPauseEffect(AudioMixerSnapshot pauseSnapshot)
    {
        pauseSnapshot.TransitionTo(0.5f);
    }

    public void ApplyNormalMix(AudioMixerSnapshot normalSnapshot)
    {
        normalSnapshot.TransitionTo(0.3f);
    }
}
```

#### Audio Pool Pattern

```csharp
using UnityEngine;
using System.Collections.Generic;

public class AudioPool : MonoBehaviour
{
    [SerializeField] private int poolSize = 16;
    private Queue<AudioSource> availableSources = new Queue<AudioSource>();

    void Awake()
    {
        for (int i = 0; i < poolSize; i++)
        {
            AudioSource source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            availableSources.Enqueue(source);
        }
    }

    public AudioSource Play(AudioClip clip, float volume = 1f, float pitch = 1f)
    {
        if (availableSources.Count == 0) return null;

        AudioSource source = availableSources.Dequeue();
        source.clip = clip;
        source.volume = volume;
        source.pitch = pitch;
        source.Play();

        StartCoroutine(ReturnToPool(source, clip.length / pitch));
        return source;
    }

    private System.Collections.IEnumerator ReturnToPool(AudioSource source, float delay)
    {
        yield return new WaitForSeconds(delay + 0.05f);
        source.Stop();
        source.clip = null;
        availableSources.Enqueue(source);
    }
}
```

### Unreal Engine 5 MetaSounds

#### Basic Sound Playback

```cpp
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundCue.h"
#include "Components/AudioComponent.h"

// Fire-and-forget at location
UGameplayStatics::PlaySoundAtLocation(
    GetWorld(), ExplosionSoundCue, HitLocation, FRotator::ZeroRotator,
    1.0f,  // Volume multiplier
    1.0f,  // Pitch multiplier
    0.0f,  // Start time
    AttenuationSettings,
    nullptr,  // Concurrency settings
    nullptr   // Owning actor
);

// Spawned audio component for ongoing control
UAudioComponent* EngineAudio = UGameplayStatics::SpawnSoundAtLocation(
    GetWorld(), EngineMetaSound, GetActorLocation(),
    FRotator::ZeroRotator,
    1.0f, 1.0f, 0.0f,
    AttenuationSettings, nullptr, true  // bAutoDestroy
);

// Set MetaSound parameters at runtime
EngineAudio->SetFloatParameter("RPM", CurrentRPM);
EngineAudio->SetFloatParameter("Load", EngineLoad);
EngineAudio->SetBoolParameter("IsElectric", bIsElectric);
```

#### Sound Class and Mix Hierarchy

```
Master
  +-- Music
  |     +-- Music_BGM
  |     +-- Music_Stinger
  +-- SFX
  |     +-- SFX_Player
  |     +-- SFX_World
  |     +-- SFX_Weapon
  +-- Voice
  |     +-- Voice_Dialogue
  |     +-- Voice_Bark
  +-- UI
  +-- Ambient
```

#### Audio Volumes and Submixes

```cpp
// Blueprint-callable volume control
UFUNCTION(BlueprintCallable)
void SetMusicVolume(float Volume)
{
    if (MusicSoundMix && MusicSoundClass)
    {
        UGameplayStatics::SetSoundMixClassOverride(
            GetWorld(), MusicSoundMix, MusicSoundClass,
            Volume, 1.0f, 0.5f, true
        );
    }
}
```

### Godot AudioStreamPlayer

#### 2D and 3D Audio

```gdscript
extends Node

# 2D audio (non-positional)
func play_ui_sound(sound: AudioStream) -> void:
    var player := AudioStreamPlayer.new()
    player.stream = sound
    player.bus = "UI"
    player.pitch_scale = randf_range(0.95, 1.05)
    add_child(player)
    player.play()
    player.finished.connect(player.queue_free)

# 3D positional audio
func play_3d_sound(sound: AudioStream, position: Vector3) -> void:
    var player := AudioStreamPlayer3D.new()
    player.stream = sound
    player.bus = "SFX"
    player.unit_size = 10.0
    player.max_distance = 50.0
    player.position = position
    add_child(player)
    player.play()
    player.finished.connect(player.queue_free)
```

#### Bus Effects and Volume Control

```gdscript
extends Node

func _ready() -> void:
    # Configure SFX bus volume
    var bus_idx := AudioServer.get_bus_index("SFX")
    AudioServer.set_bus_volume_db(bus_idx, -6.0)

    # Add reverb effect to Ambient bus
    var ambient_idx := AudioServer.get_bus_index("Ambient")
    var reverb := AudioEffectReverb.new()
    reverb.room_size = 0.8
    reverb.damping = 0.5
    reverb.wet = 0.3
    AudioServer.add_bus_effect(ambient_idx, reverb)

func set_master_volume(linear_volume: float) -> void:
    var bus_idx := AudioServer.get_bus_index("Master")
    AudioServer.set_bus_volume_db(bus_idx, linear_to_db(linear_volume))

func mute_bus(bus_name: String, mute: bool) -> void:
    var bus_idx := AudioServer.get_bus_index(bus_name)
    AudioServer.set_bus_mute(bus_idx, mute)
```

---

## 5. Web Audio API

### Raw Web Audio API

#### Basic Playback and Routing

```javascript
const ctx = new AudioContext();
const bufferCache = new Map();

async function loadSound(url) {
  if (bufferCache.has(url)) return bufferCache.get(url);

  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
  bufferCache.set(url, audioBuffer);
  return audioBuffer;
}

async function playSound(url, options = {}) {
  const buffer = await loadSound(url);
  const { volume = 1.0, pitch = 1.0, loop = false } = options;

  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.playbackRate.value = pitch;
  source.loop = loop;

  const gainNode = ctx.createGain();
  gainNode.gain.value = volume;

  source.connect(gainNode).connect(ctx.destination);
  source.start();
  return source;
}

// Resume context after user interaction (browser policy)
document.addEventListener('click', () => {
  if (ctx.state === 'suspended') ctx.resume();
}, { once: true });
```

#### Effects Chain

```javascript
function createEffectsChain(ctx) {
  // Low-pass filter (muffled/underwater)
  const lowPass = ctx.createBiquadFilter();
  lowPass.type = 'lowpass';
  lowPass.frequency.value = 2000;

  // Convolver reverb
  const convolver = ctx.createConvolver();

  // Compressor
  const compressor = ctx.createDynamicsCompressor();
  compressor.threshold.value = -24;
  compressor.ratio.value = 4;

  // Master gain
  const masterGain = ctx.createGain();
  masterGain.gain.value = 0.8;

  // Chain: source -> lowPass -> convolver -> compressor -> masterGain -> output
  lowPass.connect(convolver);
  convolver.connect(compressor);
  compressor.connect(masterGain);
  masterGain.connect(ctx.destination);

  return { input: lowPass, masterGain };
}
```

### Howler.js

#### BGM and SFX Sprites

```javascript
import { Howl, Howler } from 'howler';

// Background music (streaming)
const bgm = new Howl({
  src: ['audio/bgm/level1.ogg', 'audio/bgm/level1.mp3'],
  loop: true,
  volume: 0.5,
  html5: true, // Use HTML5 Audio for streaming (lower memory)
  onend: function () {
    console.log('BGM loop complete');
  },
});

// SFX sprite sheet (single file, multiple sounds)
const sfxSprite = new Howl({
  src: ['audio/sprites/ui.ogg', 'audio/sprites/ui.mp3'],
  sprite: {
    click:   [0, 200],
    hover:   [300, 150],
    confirm: [500, 400],
    cancel:  [1000, 300],
    error:   [1400, 500],
  },
});

// Play sprite sounds
sfxSprite.play('click');
sfxSprite.play('confirm');

// Volume control
Howler.volume(0.8); // Global volume

// Fade BGM
bgm.fade(0.5, 0.0, 2000); // from, to, duration ms

// Spatial audio with Howler
const ambient = new Howl({
  src: ['audio/ambient/waterfall.ogg'],
  loop: true,
  volume: 0.6,
});
const id = ambient.play();
ambient.pos(10, 0, 5, id);  // x, y, z
```

### Phaser 3 Audio

```javascript
class GameScene extends Phaser.Scene {
  preload() {
    // Provide multiple formats for cross-browser support
    this.load.audio('bgm', ['audio/bgm.ogg', 'audio/bgm.mp3']);
    this.load.audio('jump', ['audio/sfx/jump.ogg', 'audio/sfx/jump.mp3']);
    this.load.audio('coin', ['audio/sfx/coin.ogg', 'audio/sfx/coin.mp3']);
  }

  create() {
    // BGM with looping
    this.bgm = this.sound.add('bgm', {
      loop: true,
      volume: 0.5,
    });
    this.bgm.play();

    // SFX with randomized pitch for variation
    this.input.keyboard.on('keydown-SPACE', () => {
      this.sound.play('jump', {
        volume: 0.8,
        rate: Phaser.Math.FloatBetween(0.9, 1.1),
      });
    });

    // Audio markers (sprite-like regions in a single file)
    const sfxSheet = this.sound.add('ui_sounds');
    sfxSheet.addMarker({ name: 'click', start: 0, duration: 0.2 });
    sfxSheet.addMarker({ name: 'hover', start: 0.3, duration: 0.15 });
    sfxSheet.play('click');
  }
}
```

### Three.js PositionalAudio

```javascript
import * as THREE from 'three';

// Listener (attach to camera)
const listener = new THREE.AudioListener();
camera.add(listener);

// Non-positional background music
const bgm = new THREE.Audio(listener);
const audioLoader = new THREE.AudioLoader();
audioLoader.load('audio/bgm/ambient.ogg', (buffer) => {
  bgm.setBuffer(buffer);
  bgm.setLoop(true);
  bgm.setVolume(0.4);
  bgm.play();
});

// Positional 3D audio (attached to a mesh)
const waterfallSound = new THREE.PositionalAudio(listener);
audioLoader.load('audio/sfx/waterfall.ogg', (buffer) => {
  waterfallSound.setBuffer(buffer);
  waterfallSound.setRefDistance(10);
  waterfallSound.setRolloffFactor(1);
  waterfallSound.setDistanceModel('exponential');
  waterfallSound.setMaxDistance(100);
  waterfallSound.setLoop(true);
  waterfallSound.play();
});
waterfallMesh.add(waterfallSound);

// Audio analysis (for visualizations)
const analyser = new THREE.AudioAnalyser(bgm, 256);
// In render loop:
const frequencyData = analyser.getFrequencyData(); // Uint8Array
const averageFreq = analyser.getAverageFrequency();
```

---

## 6. Asset Import Automation

### Unity Editor Script

```csharp
using UnityEditor;
using UnityEngine;

public class AudioImportProcessor : AssetPostprocessor
{
    void OnPreprocessAudio()
    {
        AudioImporter importer = (AudioImporter)assetImporter;
        string filename = System.IO.Path.GetFileNameWithoutExtension(importer.assetPath);

        AudioImporterSampleSettings settings = importer.defaultSampleSettings;

        if (filename.StartsWith("sfx_"))
        {
            // SFX: Mono, Decompress on Load, small files
            importer.forceToMono = true;
            settings.loadType = AudioClipLoadType.DecompressOnLoad;
            settings.compressionFormat = AudioCompressionFormat.Vorbis;
            settings.quality = 0.7f;
            settings.sampleRateSetting = AudioSampleRateSetting.OptimizeSampleRate;
        }
        else if (filename.StartsWith("bgm_"))
        {
            // BGM: Stereo, Streaming, large files
            importer.forceToMono = false;
            settings.loadType = AudioClipLoadType.Streaming;
            settings.compressionFormat = AudioCompressionFormat.Vorbis;
            settings.quality = 0.6f;
        }
        else if (filename.StartsWith("ui_"))
        {
            // UI: Mono, Decompress on Load, 2D
            importer.forceToMono = true;
            settings.loadType = AudioClipLoadType.DecompressOnLoad;
            settings.compressionFormat = AudioCompressionFormat.ADPCM;
        }
        else if (filename.StartsWith("vo_"))
        {
            // Voice: Mono, Compressed in Memory
            importer.forceToMono = true;
            settings.loadType = AudioClipLoadType.CompressedInMemory;
            settings.compressionFormat = AudioCompressionFormat.Vorbis;
            settings.quality = 0.5f;
        }
        else if (filename.StartsWith("amb_"))
        {
            // Ambience: Stereo, Streaming
            importer.forceToMono = false;
            settings.loadType = AudioClipLoadType.Streaming;
            settings.compressionFormat = AudioCompressionFormat.Vorbis;
            settings.quality = 0.5f;
        }

        importer.defaultSampleSettings = settings;
    }
}
```

### Godot Import Presets

```tres
# res://.import_defaults.tres
# Default import settings for audio files

[gd_resource type="ImportDefaults"]

[resource]
importers = {
  "ogg_vorbis": {
    "loop": false,
    "loop_offset": 0.0,
    "bar_beats": 4,
    "beat_count": 0,
    "bpm": 0.0
  },
  "wav": {
    "force/8_bit": false,
    "force/mono": false,
    "force/max_rate": false,
    "force/max_rate_hz": 44100,
    "edit/trim": false,
    "edit/normalize": false,
    "edit/loop_mode": 0,
    "compress/mode": 0
  }
}
```

#### Godot Audio Bus Layout

```tres
# res://default_bus_layout.tres
[gd_resource type="AudioBusLayout"]

[resource]
bus/0/name = "Master"
bus/0/volume_db = 0.0

bus/1/name = "BGM"
bus/1/send = "Master"
bus/1/volume_db = -3.0

bus/2/name = "SFX"
bus/2/send = "Master"
bus/2/volume_db = 0.0

bus/3/name = "Voice"
bus/3/send = "Master"
bus/3/volume_db = 0.0

bus/4/name = "UI"
bus/4/send = "Master"
bus/4/volume_db = -3.0

bus/5/name = "Ambient"
bus/5/send = "Master"
bus/5/volume_db = -6.0
```

### Build Script for Asset Pipeline

```bash
#!/usr/bin/env bash
# copy_audio_to_engine.sh
# Copy platform-optimized audio assets to engine project directories

set -euo pipefail

SOURCE_DIR="${1:?Usage: $0 <source_dir> <target_engine_dir>}"
TARGET_DIR="${2:?Usage: $0 <source_dir> <target_engine_dir>}"

echo "Syncing processed audio from ${SOURCE_DIR} to ${TARGET_DIR}"

# Copy OGG files (preferred for Unity/Godot)
rsync -av --include='*/' --include='*.ogg' --exclude='*' \
    "${SOURCE_DIR}/processed/" "${TARGET_DIR}/Assets/Audio/"

# Copy WAV files only for short SFX (< 1MB, better for decompressed playback)
find "${SOURCE_DIR}/processed/sfx" -name '*.wav' -size -1M \
    -exec cp -v {} "${TARGET_DIR}/Assets/Audio/SFX/" \;

# Generate file manifest
find "${TARGET_DIR}/Assets/Audio" -type f \( -name '*.ogg' -o -name '*.wav' \) \
    | sort > "${TARGET_DIR}/Assets/Audio/manifest.txt"

echo "Audio sync complete. Files:"
wc -l "${TARGET_DIR}/Assets/Audio/manifest.txt"
```

### FMOD Bank Build Script

```bash
#!/usr/bin/env bash
# build_fmod_banks.sh
# Build FMOD banks and copy to engine project

set -euo pipefail

FMOD_PROJECT="${1:?Usage: $0 <fmod_project_dir> <target_dir>}"
TARGET_DIR="${2:?Usage: $0 <fmod_project_dir> <target_dir>}"

# Build banks using FMOD CLI (macOS path)
FMOD_CLI="/Applications/FMOD Studio.app/Contents/MacOS/fmodstudiocl"

if [ ! -x "${FMOD_CLI}" ]; then
    echo "Error: FMOD Studio CLI not found at ${FMOD_CLI}"
    exit 1
fi

"${FMOD_CLI}" build "${FMOD_PROJECT}" --platform Desktop

# Copy built banks to target
BANK_DIR="${FMOD_PROJECT}/Build/Desktop"
rsync -av --include='*.bank' --include='*.strings.bank' --exclude='*' \
    "${BANK_DIR}/" "${TARGET_DIR}/Assets/StreamingAssets/FMOD/"

echo "FMOD banks deployed to ${TARGET_DIR}"
```

# Anti-Patterns Reference

Common pitfalls in AI 3D model generation workflows and how to avoid them.

## Ship Raw AI Output

**Problem**: Approximately 90% of AI-generated 3D models need post-processing before they are game-ready. Shipping raw output leads to topology issues, poor UV maps, excessive poly counts, and visual artifacts in-engine.

**Symptoms**:
- Non-manifold edges causing rendering artifacts.
- Inconsistent face winding producing black faces.
- Poly count 5-10x higher than budget.
- Missing or broken UV coordinates.
- Floating geometry fragments.

**Fix**: Always include a QC validation step in every generation workflow. Use the validation script from `quality-validation.md` and require a minimum "game-ready" tier pass before integration.

```python
# WRONG: Generate and use directly
model = generate_3d(prompt)
export_to_engine(model)

# RIGHT: Generate, validate, fix, then use
model = generate_3d(prompt)
report = validate_model(model, poly_budget=10000)
if not report["pass"]:
    model = run_retopo_pipeline(model)
    report = validate_model(model, poly_budget=10000)
export_to_engine(model)
```

## Hero Asset Misuse

**Problem**: Using AI generation for focal/hero objects that players examine closely. AI excels at background filler, environmental props, and distant objects, but hero assets (player character, key items, boss enemies) require manual artistry that AI cannot reliably deliver.

**Symptoms**:
- Uncanny valley effect on AI-generated characters.
- Loss of brand-specific style or personality.
- Player complaints about "soulless" or "generic" key assets.

**Fix**: Reserve AI generation for:
- Background and filler objects (crates, barrels, rocks, foliage).
- Distant environment pieces.
- Prototype and concepting phases.
- Variation generation (10 rock variants from 1 reference).

Use manual modeling (or AI + heavy manual refinement) for:
- Player characters and NPCs.
- Key story items.
- Boss enemies and unique creatures.
- UI-facing 3D elements.

## LOD Amnesia

**Problem**: Placing AI-generated assets without Level of Detail configuration causes catastrophic performance at scale. A single high-poly model looks fine in isolation, but 100 instances without LOD can drop frame rates below playability.

**Symptoms**:
- Frame rate drops when many instances are visible.
- GPU memory exhaustion in complex scenes.
- Draw call explosion.
- "It works in the editor but not in-game."

**Fix**: LOD generation is mandatory for every game asset. Include LOD configuration in every Clay deliverable.

```python
# WRONG: Single mesh, no LOD
export_model(mesh, "asset.fbx")

# RIGHT: Always generate LOD chain
generate_lod_chain(
    mesh,
    lod_ratios=[1.0, 0.5, 0.25, 0.1],
    output_dir="assets/props/crate/",
)
```

**Exception**: UE5 Nanite handles LOD internally for static meshes. When targeting Nanite, export full-res mesh without manual LOD chain, but still validate total scene geometry budget.

Rule of thumb: if an asset will appear more than once in a scene, it needs LOD.

## UV Blindness

**Problem**: Ignoring UV quality metrics after AI generation. AI models often have poor UV layouts with wildly inconsistent texel density, causing some parts to appear blurry while others are crisp.

**Symptoms**:
- Texture resolution varies dramatically across the model surface.
- Seams visible at UV island boundaries.
- Texture bleeding at UV edges.
- Wasted UV space (coverage < 50%).

**Fix**: Include UV analysis in every QC step. Target > 80% UV coverage and texel density variance < 0.3.

```python
uv_report = analyze_uv(mesh)
if uv_report["uv_coverage"] < 0.80:
    print("UV coverage too low - repack needed")
if uv_report["texel_density_variance"] > 0.3:
    print("Texel density too variable - re-unwrap needed")
```

## Janus Problem

**Problem**: Score Distillation Sampling (SDS) based text-to-3D methods can produce models with duplicated features when viewed from different angles (e.g., a character with faces on both front and back).

**Symptoms**:
- Duplicate facial features on opposite sides.
- Symmetric features where asymmetry is expected.
- "Totem pole" effect with repeated patterns around the model.

**Fix**:
1. Use providers that employ multi-view diffusion (MVDream, Zero123++). Hunyuan3D 2.0, Trellis, and newer Tripo/Meshy models have largely solved this.
2. Prefer FlexiCubes mesh extraction over naive marching cubes.
3. Provide multi-view reference images to constrain generation.
4. Add negative constraints: "single face, consistent appearance from all angles".
5. Validate by rendering 4+ views before accepting the model.
6. When possible, prefer image-to-3D over text-to-3D (image provides consistent reference).

## Batch Without Preview

**Problem**: Submitting large batch generation jobs (50+ models) without previewing a small sample first. This leads to cost explosion when the prompt produces poor results and all credits are wasted.

**Symptoms**:
- Large API bills for unusable output.
- Entire batch fails the same way (prompt issue).
- Hours of generation time wasted on a bad prompt.

**Fix**: Always preview 1-3 models before batch runs.

```python
# WRONG: Batch 100 models immediately
for i in range(100):
    generate_model(prompt, mode="refine")

# RIGHT: Preview first, then batch
preview_results = [generate_model(prompt, mode="preview") for _ in range(3)]
# Review preview_results manually or with QC
if previews_acceptable(preview_results):
    for i in range(100):
        generate_model(prompt, mode="refine")
```

Cost estimation before batch runs is mandatory. See `api-integration.md` for the cost estimation pattern.

## Single Provider Lock-in

**Problem**: Hardcoding a specific provider's API throughout the codebase. When that provider changes pricing, rate limits, or API shape, the entire pipeline breaks.

**Symptoms**:
- Provider API change breaks all generation scripts.
- Cannot switch to a cheaper/better provider without rewriting code.
- Testing requires live API calls (no mock layer).

**Fix**: Use the provider abstraction from `api-integration.md`.

```python
# WRONG: Provider-specific code everywhere
resp = httpx.post("https://api.meshy.ai/openapi/v2/text-to-3d", ...)

# RIGHT: Abstract provider interface
provider = MeshyProvider()  # or TripoProvider(), RodinProvider()
task_id = provider.text_to_3d(config)
result = provider.poll_until_complete(task_id)
```

## Topology Ignorance

**Problem**: Accepting AI output because it "looks fine" in a preview render without checking topology. Visual appearance does not guarantee game-engine compatibility.

**Symptoms**:
- Model looks perfect in Blender but has artifacts in Unity/UE.
- Physics collisions behave unexpectedly.
- Skinning/rigging produces distortions.
- Import warnings in game engines.

**Fix**: Always run topology validation. "Looks fine" is not a substitute for manifold checks.

```python
report = check_topology(mesh)
assert report["non_manifold_edges"] == 0, "Non-manifold edges detected"
assert report["degenerate_faces"] == 0, "Degenerate faces detected"
assert report["is_winding_consistent"], "Inconsistent face winding"
assert report["floating_fragments"] == 0, "Floating geometry detected"
```

## Gaussian Splatting Direct Use

**Problem**: Using 3D Gaussian Splatting (3DGS) output directly in game engines. 3DGS is excellent for photorealistic rendering but is not compatible with standard game engine rendering pipelines (rasterization, physics, shadows, LOD).

**Symptoms**:
- Cannot apply standard materials or shaders.
- No physics collision support.
- No shadow casting/receiving.
- Cannot use LOD system.
- Extreme memory usage.
- No animation/skinning support.

**Fix**: Always convert 3DGS to mesh before game engine integration.

```python
# WRONG: Use 3DGS directly in game engine
splat_file = generate_3dgs(image)
import_to_unity(splat_file)  # Will not work

# RIGHT: Convert to mesh first
splat_file = generate_3dgs(image)
mesh_file = gaussian_to_mesh(splat_file, method="sugar")
validate_model(mesh_file, poly_budget=10000)
import_to_unity(mesh_file)
```

Acceptable uses of 3DGS without conversion:
- Web-based 3D viewers (using dedicated splat renderers)
- Architectural visualization (where photorealism matters more than interactivity)
- Cinematic sequences (pre-rendered or dedicated renderer)

## Texture Compression Neglect

**Problem**: Delivering game assets with uncompressed PNG textures. This wastes GPU memory, increases download sizes, and prevents GPU-native texture decoding.

**Symptoms**:
- Excessive VRAM usage (a 2048x2048 RGBA PNG uses 16MB uncompressed on GPU).
- Long loading times due to large texture files.
- Mobile devices running out of texture memory.
- Web apps with slow initial load.

**Fix**: Always compress textures for the target platform.

```python
# WRONG: Ship raw PNG textures
export_textures(model, format="png")

# RIGHT: Compress for target platform
if target == "web":
    compress_textures(textures, method="ktx2")  # GPU-decoded, universal
elif target == "mobile":
    compress_textures(textures, method="ktx2", profile="etc1s")  # Smallest
elif target == "pc":
    compress_textures(textures, method="ktx2", profile="uastc")  # Best quality
```

| Format | On-GPU Size (2048x2048) | File Size | GPU Decode |
|--------|------------------------|-----------|------------|
| PNG (uncompressed) | 16 MB | 2-5 MB | No (CPU) |
| KTX2 UASTC | 16 MB | 3-8 MB | Yes |
| KTX2 ETC1S | 4 MB | 0.5-2 MB | Yes |
| BC7 (DDS) | 16 MB | 8 MB | Yes |
| ASTC 4x4 | 16 MB | 8 MB | Yes |

## Rigging Without Validation

**Problem**: Auto-rigging AI-generated models without checking if the mesh is suitable for rigging. AI-generated meshes often have topology issues (non-manifold, floating parts, inconsistent normals) that cause rigging failures.

**Symptoms**:
- Bone weights fail to paint correctly.
- Mesh explodes during animation.
- Joints bend incorrectly (candy wrapper effect).
- Auto-rig tools crash or produce garbage results.

**Fix**: Validate mesh before rigging. Auto-rigging requirements are stricter than rendering requirements.

```python
# WRONG: Auto-rig immediately after generation
model = generate_3d(prompt)
rigged = auto_rig(model)  # May fail or produce bad results

# RIGHT: Validate rigging readiness first
model = generate_3d(prompt)
topo = check_topology(model)
rigging_ready = (
    topo["non_manifold_edges"] == 0 and
    topo["floating_fragments"] == 0 and
    topo["is_watertight"] and
    topo["connected_components"] == 1  # Single mesh required
)
if rigging_ready:
    rigged = auto_rig(model)
else:
    model = retopo_for_rigging(model)  # Fix topology first
    rigged = auto_rig(model)
```

## API Version Drift

**Problem**: Not pinning provider API versions or model versions. When providers update their APIs or models, generation results change silently, breaking asset consistency in a project.

**Symptoms**:
- Same prompt produces different results over time.
- Asset style consistency breaks mid-project.
- Scripts stop working after provider updates.
- Regenerated assets look different from original batch.

**Fix**: Always pin API versions and model versions explicitly.

```python
# WRONG: Use latest version implicitly
resp = httpx.post(f"{BASE_URL}/task", json={"prompt": prompt})

# RIGHT: Pin model version explicitly
resp = httpx.post(f"{BASE_URL}/task", json={
    "prompt": prompt,
    "model_version": "v2.5-20250123",  # Pin specific version
    "api_version": "2024-12-01",        # Pin API version if supported
})

# Document in metadata
metadata = {
    "provider": "tripo",
    "model_version": "v2.5-20250123",
    "api_version": "2024-12-01",
    "generation_date": "2026-01-15",
    "prompt": prompt,
}
```

Also: store all generated assets with their exact generation parameters in metadata JSON for reproducibility.

## Summary Table

| Anti-Pattern | Risk Level | Detection | Prevention |
|-------------|------------|-----------|------------|
| Ship Raw AI Output | High | QC validation | Always validate before integration |
| Hero Asset Misuse | Medium | Design review | AI for filler, manual for heroes |
| LOD Amnesia | High | Performance profiling | Mandatory LOD chain for all assets |
| UV Blindness | Medium | UV analysis script | Check coverage and texel density |
| Janus Problem | Medium | Multi-view render check | Use multi-view aware providers |
| Batch Without Preview | High | Cost monitoring | Preview 1-3 before batch |
| Single Provider Lock-in | Low | Code review | Abstract provider interface |
| Topology Ignorance | High | Topology check script | Validate manifold/watertight |
| Gaussian Splatting Direct Use | High | Engine import test | Convert 3DGS to mesh first |
| Texture Compression Neglect | Medium | File size audit | KTX2/ASTC for all game textures |
| Rigging Without Validation | Medium | Pre-rig topology check | Validate before auto-rigging |
| API Version Drift | Medium | Metadata audit | Pin all versions explicitly |

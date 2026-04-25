# Prompt Engineering Reference

Prompt architecture, provider-specific tips, negative constraints, style transfer, multi-view strategies, and example prompts for text-to-3D and image-to-3D generation.

## Prompt Architecture

Structure prompts in five layers:

```
[Subject] + [Style] + [Material] + [Topology] + [Scale]
```

| Layer | Purpose | Example |
|-------|---------|---------|
| Subject | What to generate | "Medieval wooden treasure chest" |
| Style | Visual treatment | "low-poly stylized, hand-painted texture" |
| Material | Surface properties | "weathered oak wood with tarnished iron bands" |
| Topology | Mesh requirements | "clean quad topology, game-ready, no internal faces" |
| Scale | Size context | "prop scale, 1 meter wide, fits on a table" |

### Full Prompt Example

```
Medieval wooden treasure chest with iron bands and padlock,
low-poly stylized with hand-painted textures,
weathered oak wood with tarnished iron fittings,
clean topology suitable for game engine, no floating geometry,
prop scale approximately 1 meter wide
```

## Prompt Length Guidelines

| Length | Words | Recommendation |
|--------|-------|----------------|
| Optimal | 30-60 | Best balance of control and quality |
| Good | 60-100 | More detail, still reliable |
| Acceptable | 100-150 | May lose coherence on some providers |
| Avoid | > 150 | Diminishing returns, conflicting instructions |

Rules:
- Lead with the subject noun.
- Place style after subject, material next.
- Keep topology/technical terms at the end.
- Use commas to separate clauses, not complex sentences.
- Be specific but not contradictory.

## Provider-Specific Tips

### Meshy

- Supports `art_style` parameter: `realistic`, `sculpture`, `cartoon`, `low-poly`, `pbr`.
- Set style via parameter rather than prompt text when possible.
- Works well with detailed material descriptions ("weathered bronze", "polished marble").
- `topology: "quad"` parameter produces cleaner results for game assets.
- Preview mode (~30s): use for iteration. Refine mode (~2-5min): production quality.
- Text-to-texture: can re-skin existing models with new prompts.
- Newer models support negative prompts via `negative_prompt` parameter.

### Tripo

- Excels at organic shapes (characters, creatures, plants).
- Shorter prompts (20-40 words) often outperform long ones.
- Supports multi-view input for image-to-3D; provide front + side views.
- Model version significantly affects output; always specify `model_version`.
- v2.5 produces significantly better topology than v1.x.
- Built-in auto-rigging and animation for humanoid characters.
- Supports style transfer via reference images.

### Hunyuan3D 2.0

- Open-source with commercial license (Tencent).
- Generates PBR textures natively (albedo, normal, roughness).
- Benefits from explicit geometric terms ("smooth surface", "sharp edges", "beveled corners").
- Self-hosted: adjust inference steps for quality vs speed (30 steps=fast, 75 steps=quality).
- For image-to-3D: single clean image with white background produces best results.
- Supports both text-to-3D and image-to-3D in a single model.
- Uses multi-view diffusion internally, largely immune to Janus problem.

### Rodin

- Best for high-detail assets (characters, organic forms, complex props).
- Accepts multi-view condition images alongside text prompts.
- Higher cost but consistently better topology quality.
- Responds well to artistic style references ("in the style of Pixar", "Ghibli aesthetic").
- Supports condition image + text prompt combined input.
- Geometry detail level can be controlled via API parameters.

### Sloyd

- Parametric approach: works differently from pure AI generation.
- Best for: architectural elements, furniture, simple props, modular pieces.
- Outputs pre-retopologized meshes (already game-ready topology).
- Prompt as a specification rather than a description.
- Supports parameter-based variation (adjust dimensions, style).
- Fastest generation time (~5-15s) among all providers.

### Stability (Stable Fast 3D)

- Single-image-to-3D specialist (no text-to-3D).
- Ultra-fast inference (~1s per model).
- Input image quality directly determines output quality.
- White or transparent background strongly recommended.
- Best for: rapid prototyping, concept validation.
- Supports remesh parameter for controlling output topology.
- Returns model synchronously (no polling needed).

### Trellis (Microsoft)

- Open-source, self-hosted.
- Dual output: 3D Gaussian Splatting + extracted mesh.
- Image-to-3D only (no text-to-3D).
- Best for: photorealistic reconstructions, objects with complex materials.
- Uses SLAT (Structured LATent) representation internally.
- Mesh quality depends on `mesh_simplify` parameter.

### Luma Genie

- Supports text-to-3D, image-to-3D, and video-to-3D.
- Video-to-3D: excellent for capturing real objects from phone video.
- Text prompts respond well to descriptive language about shape and form.
- 3D Gaussian Splatting output for photorealistic rendering.
- Requires conversion to mesh for game engine use.

## Negative Constraints

Include these to avoid common AI generation artifacts:

| Issue | Negative Constraint Phrase |
|-------|--------------------------|
| Janus (multi-face) | "single continuous surface, no duplicate features, consistent from all angles" |
| Floating geometry | "no floating parts, all geometry connected, single solid mesh" |
| Internal faces | "no internal faces, clean exterior surface only, no hidden geometry" |
| Excessive detail | "game-ready detail level, no micro-geometry, clean silhouette" |
| Broken symmetry | "symmetrical design, mirror symmetry on central axis" |
| Scale ambiguity | Include explicit size reference and context |
| Z-fighting | "no coplanar faces, no overlapping surfaces" |
| Self-intersection | "no self-intersecting geometry, clean mesh" |
| Disconnected parts | "single connected mesh, no separate floating pieces" |

### Negative Prompt Template

```
[Positive prompt],
no floating geometry, no internal faces,
single continuous mesh, consistent appearance from all angles,
game-ready topology, no micro-detail noise
```

## Style Transfer Techniques

### Style Vocabulary

| Style | Keywords | Best Provider | Use Case |
|-------|----------|---------------|----------|
| Stylized/Cartoon | "stylized, cartoon, cel-shaded, bold colors" | Meshy, Tripo | Mobile games, casual |
| Low-poly | "low-poly, flat shaded, geometric, faceted" | Meshy (low-poly mode), Sloyd | Retro games, minimalist |
| Realistic/PBR | "photorealistic, PBR materials, detailed surface" | Rodin, Hunyuan3D 2.0 | AAA games, archviz |
| Hand-painted | "hand-painted textures, painterly, diffuse-only" | Meshy, Tripo | World of Warcraft style |
| Voxel | "voxelized, blocky, minecraft-style, cubic" | Meshy | Voxel games |
| Pixel art 3D | "pixel art style, low resolution textures, retro" | Meshy | Retro-3D, indie |
| Anime/Manga | "anime style, cel-shaded, Japanese animation" | Rodin, Tripo | Anime games, VTuber |
| Sci-fi | "futuristic, sci-fi, metallic, holographic" | Rodin, Meshy | Sci-fi games |
| Fantasy | "fantasy, magical, enchanted, mystical" | Meshy, Rodin | RPG games |

### Style Consistency Across Assets

For consistent style across multiple assets in a project:

```
# Define a style template
STYLE_TEMPLATE = """
{subject},
stylized hand-painted textures with warm color palette,
slightly exaggerated proportions, rounded edges,
game-ready for Unity, clean topology,
consistent with medieval fantasy art direction
"""

# Generate variants
prompts = [
    STYLE_TEMPLATE.format(subject="Wooden barrel with metal bands"),
    STYLE_TEMPLATE.format(subject="Stone well with wooden roof"),
    STYLE_TEMPLATE.format(subject="Market stall with canvas awning"),
]
```

## Image-to-3D Reference Preparation

### Optimal Input

1. **Multi-view images** (best): front, side, back, 3/4 angle.
2. **Single image** (acceptable): front or 3/4 view with clean background.
3. **Turntable video** (for Luma): smooth rotation around object.

### Image Requirements

| Requirement | Specification |
|-------------|--------------|
| Background | White, solid color, or transparent |
| Lighting | Even, diffuse, no harsh shadows |
| Subject fill | 70-80% of frame |
| Resolution | 512x512 minimum, 1024x1024 recommended |
| Format | PNG (preferred) or JPEG (quality 95+) |
| Ground shadows | Remove or minimize |
| Occlusion | Avoid heavy self-occlusion |
| Color consistency | Same white balance across views |
| Orientation | Subject upright, facing camera |

### AI Image-to-3D Pipeline (Sketch -> Clay)

When receiving images from Sketch agent (Gemini API):

```python
def prepare_sketch_output_for_3d(image_path: str, output_path: str):
    """Prepare Sketch-generated image for image-to-3D.

    Sketch generates images that may need preprocessing:
    1. Background removal
    2. Centering and scaling
    3. Resolution adjustment
    """
    from PIL import Image
    import numpy as np

    img = Image.open(image_path).convert("RGBA")

    # Simple background removal (white background)
    data = np.array(img)
    white_threshold = 240
    mask = np.all(data[:, :, :3] > white_threshold, axis=2)
    data[mask, 3] = 0  # Make white pixels transparent

    # Center and crop to subject
    alpha = data[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Add padding (15% of larger dimension)
    h, w = rmax - rmin, cmax - cmin
    pad = int(max(h, w) * 0.15)
    rmin = max(0, rmin - pad)
    rmax = min(data.shape[0], rmax + pad)
    cmin = max(0, cmin - pad)
    cmax = min(data.shape[1], cmax + pad)

    cropped = data[rmin:rmax, cmin:cmax]

    # Resize to 1024x1024
    result = Image.fromarray(cropped)
    result = result.resize((1024, 1024), Image.Resampling.LANCZOS)
    result.save(output_path, "PNG")
```

### Multi-View Consistency

For multi-view input (Tripo, Rodin):
- Use consistent lighting across all views.
- Maintain consistent color/exposure.
- Keep the same camera height and distance.
- Use turntable-style rotation (every 90 degrees for 4 views, every 45 for 8).
- Ensure the object is centered in frame across all views.
- Use the same focal length/FOV for all views.

## Multi-View Consistency and Janus Problem

The "Janus problem" occurs when SDS-based (Score Distillation Sampling) methods create models with duplicate features (e.g., two faces on a character). Mitigation strategies:

1. **Use multi-view aware providers**: Hunyuan3D 2.0, Trellis, and newer Tripo/Meshy models use multi-view diffusion (MVDream, Zero123++) which largely eliminates Janus artifacts.
2. **Specify view consistency**: "consistent appearance from all angles, single face only".
3. **Use FlexiCubes extraction**: Produces more coherent surfaces than naive marching cubes.
4. **Provide multi-view reference images**: Constrains generation to consistent geometry.
5. **Validate with multi-view render**: Always render 4+ views before accepting the model.
6. **Prefer newer providers**: 2025+ generation models have largely solved this issue.

## Prompt Chaining for Complex Assets

For complex assets that need multiple generation passes:

```python
# Step 1: Generate base shape
base_prompt = """
Medieval stone tower, cylindrical shape,
3 stories with arched windows,
clean exterior surface, solid geometry,
game environment piece, 10 meters tall
"""

# Step 2: Generate decorative elements separately
details = [
    "Stone gargoyle perched on a ledge, small prop, 30cm tall",
    "Wooden door with iron studs, flat prop, 2m x 1m",
    "Banner flag on a pole, cloth simulation ready, 1m long",
]

# Step 3: Combine in Blender (code generated by Clay)
# - Import base tower
# - Import detail pieces
# - Position and attach
# - Merge or keep as hierarchy
# - Export as single asset or LOD-friendly group
```

## Example Prompt Library

### Characters

```
# Stylized character (casual/mobile game)
Chibi fantasy warrior character, large head proportions,
simple armor with sword and shield, stylized cartoon aesthetic,
bright saturated colors, clean topology for rigging,
T-pose, game-ready, approximately 1000 triangles

# Realistic character (AAA/mid-core)
Realistic medieval knight in full plate armor,
detailed surface with scratches and wear, PBR materials,
A-pose for rigging, high detail for hero asset,
approximately 180cm tall, 30000 triangle budget

# NPC / background character
Simple villager NPC, medieval clothing,
low-poly with hand-painted textures,
game-ready background character, 2000 triangle budget,
no complex accessories, clean silhouette

# Creature
Fantasy dragon with spread wings,
stylized proportions, scales texture,
game-ready with clean topology,
wingspan approximately 3 meters, idle pose
```

### Props

```
# Simple prop
Wooden barrel with metal bands,
low-poly stylized, hand-painted texture look,
game-ready prop, approximately 1 meter tall,
no internal geometry, single mesh

# Interactive prop
Ornate treasure chest with gold trim and gemstones,
semi-realistic style, clean quad topology,
openable lid as separate mesh, hinge point clearly defined,
prop scale 80cm wide, 2000 triangle budget

# Weapon
Fantasy sword with ornate handle and glowing runes,
stylized game asset, clean topology,
no floating geometry, symmetrical blade,
120cm total length, held in one hand

# Food / consumable
Roasted chicken on a wooden plate,
stylized hand-painted look, warm colors,
simple prop for inventory UI or table decoration,
30cm wide, under 500 triangles
```

### Environment

```
# Nature element
Stylized oak tree with thick trunk and full canopy,
low-poly foliage cards arranged in clusters,
game environment asset, LOD-friendly silhouette,
approximately 5 meters tall, no internal geometry

# Building
Medieval stone cottage with thatched roof,
modular walls and roof as separate pieces,
stylized game environment, hand-painted textures,
approximately 4 meters wide, tileable wall sections

# Terrain feature
Rocky cliff face with moss and vines,
stylized game terrain piece, tileable edges,
approximately 5 meters wide, flat back for placement,
LOD chain friendly, no floating rocks

# Interior
Wooden bookshelf filled with colorful books,
stylized fantasy library style, warm lighting bake,
game prop for indoor scenes, 2 meters tall,
books as texture, not individual geometry
```

### Vehicles

```
# Fantasy vehicle
Steampunk airship with propellers and wooden hull,
stylized game asset, clean topology,
approximately 15 meters long, no internal geometry,
visible deck with simple details, floating orientation

# Realistic vehicle
Military jeep with canvas top and mounted spotlight,
realistic proportions and PBR surface detail,
game-ready vehicle, LOD-appropriate detail,
4 meters long, separate wheel meshes for animation

# Mount / rideable
Fantasy horse with ornate saddle and armor,
stylized medieval game mount,
rigging-ready with clean joint areas,
1.6 meters at shoulder height, walk/run animation ready
```

## Prompt Iteration Strategy

1. **Start with a draft prompt** (30 words) and generate 1-3 previews.
2. **Evaluate results** using multi-view renders (front, side, back, 3/4).
3. **Identify issues**: check for Janus, floating geometry, scale, style match.
4. **Refine by category**:
   - Shape wrong -> adjust subject description
   - Style wrong -> adjust style/material terms
   - Topology wrong -> adjust topology constraints
   - Scale wrong -> add explicit dimensions
5. **Lock the prompt** when results are acceptable.
6. **Generate full quality** using refine/high mode.
7. **Document the final prompt** in metadata JSON for reproducibility.

### Iteration Decision Tree

```
Result OK? -> Accept and proceed to pipeline
  |
  No -> What's wrong?
  |
  Shape/Form -> Rewrite subject layer, try different angle words
  Style/Look -> Change art_style parameter or style keywords
  Artifacts -> Add negative constraints, try different provider
  Too complex -> Simplify prompt, remove conflicting terms
  Janus issue -> Add "consistent from all angles", use multi-view provider
  Scale wrong -> Add explicit dimensions in meters/cm
```

## Provider Prompt Compatibility Matrix

| Prompt Feature | Meshy | Tripo | Hunyuan3D | Rodin | Sloyd | Stability |
|---------------|-------|-------|-----------|-------|-------|-----------|
| Detailed descriptions | Good | Medium | Good | Excellent | Poor | N/A |
| Style keywords | Excellent | Good | Good | Excellent | Medium | N/A |
| Material descriptions | Excellent | Good | Good | Good | Poor | N/A |
| Topology instructions | Good | Medium | Medium | Medium | Excellent | N/A |
| Size/scale in prompt | Medium | Medium | Medium | Good | Good | N/A |
| Negative prompts | Good | Poor | Medium | Medium | Poor | N/A |
| Reference style | Medium | Good | Medium | Excellent | Poor | N/A |
| Short prompts (<30w) | Good | Excellent | Good | Good | Excellent | N/A |
| Long prompts (>100w) | Good | Poor | Medium | Good | Poor | N/A |

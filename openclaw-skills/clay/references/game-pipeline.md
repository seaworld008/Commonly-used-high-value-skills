# Game Pipeline Reference

Full pipeline from AI generation to engine-ready assets: LOD, retopology, UV packing, texture baking, texture compression, auto-rigging, and engine import. Covers modern techniques including Nanite, meshoptimizer, KTX2, and CI/CD asset pipelines.

## Full Pipeline Overview

```
AI Generation -> Integrity Check -> Retopology -> UV Unwrap -> Texture Bake
    -> Texture Compress -> LOD Generation -> Auto-Rig (optional) -> QC Gate
    -> Engine Import -> Asset Registry
```

Each step produces code (Blender Python or pipeline scripts), not manual instructions.

## End-to-End Orchestration Script

```python
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineConfig:
    """Configuration for the full asset pipeline."""
    input_file: str
    output_dir: str
    asset_name: str
    target_engine: str = "unity"          # unity | ue5 | web | mobile
    quality_tier: str = "game-ready"      # draft | game-ready | production
    poly_budget: int = 10000
    texture_resolution: int = 1024
    lod_levels: int = 4
    lod_ratios: list = field(default_factory=lambda: [1.0, 0.5, 0.25, 0.1])
    with_rigging: bool = False
    texture_compression: str = "ktx2"     # ktx2 | webp | png
    mesh_compression: str = "draco"       # draco | meshopt | none

@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    output_files: list = field(default_factory=list)
    validation_report: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """Execute the full asset pipeline.

    This function generates a Blender script and executes it.
    """
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    script = generate_blender_pipeline_script(config)
    script_path = out / "pipeline.py"
    script_path.write_text(script)

    # Execute in Blender headless
    result = subprocess.run(
        ["blender", "--background", "--python", str(script_path)],
        capture_output=True, text=True, timeout=600,
    )

    # Parse results
    report_path = out / "pipeline_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        return PipelineResult(
            success=report.get("pass", False),
            output_files=report.get("output_files", []),
            validation_report=report,
            warnings=report.get("warnings", []),
            errors=report.get("errors", []),
        )

    return PipelineResult(
        success=False,
        errors=[f"Pipeline failed: {result.stderr[:500]}"],
    )


def generate_blender_pipeline_script(config: PipelineConfig) -> str:
    """Generate comprehensive Blender Python pipeline script."""
    return f'''
import bpy
import json
from pathlib import Path

# Pipeline configuration
CONFIG = {{
    "input": "{config.input_file}",
    "output_dir": "{config.output_dir}",
    "asset_name": "{config.asset_name}",
    "target_engine": "{config.target_engine}",
    "quality_tier": "{config.quality_tier}",
    "poly_budget": {config.poly_budget},
    "texture_resolution": {config.texture_resolution},
    "lod_levels": {config.lod_levels},
    "lod_ratios": {config.lod_ratios},
    "with_rigging": {config.with_rigging},
}}

report = {{"pass": True, "output_files": [], "warnings": [], "errors": []}}
out = Path(CONFIG["output_dir"])

# Step 1: Import
bpy.ops.wm.read_homefile(use_empty=True)
ext = Path(CONFIG["input"]).suffix.lower()
if ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=CONFIG["input"])
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=CONFIG["input"])
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=CONFIG["input"])

obj = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = obj

# Step 2: Integrity check
tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
report["original_tris"] = tri_count

# Step 3: Retopology (if over budget)
if tri_count > CONFIG["poly_budget"]:
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = CONFIG["poly_budget"] / tri_count
    bpy.ops.object.modifier_apply(modifier=mod.name)
    report["retopo_applied"] = True

# Step 4: UV unwrap
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.005)
bpy.ops.object.mode_set(mode="OBJECT")

# Step 5: LOD generation + export
for i, ratio in enumerate(CONFIG["lod_ratios"]):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()
    lod = bpy.context.active_object
    lod.name = f"{{CONFIG['asset_name']}}_lod{{i}}"

    if ratio < 1.0:
        mod = lod.modifiers.new(f"Decimate_LOD{{i}}", "DECIMATE")
        mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)

    lod_tris = sum(len(p.vertices) - 2 for p in lod.data.polygons)

    # Export
    bpy.ops.object.select_all(action="DESELECT")
    lod.select_set(True)
    bpy.context.view_layer.objects.active = lod

    if CONFIG["target_engine"] in ("unity", "ue5"):
        filepath = str(out / f"{{lod.name}}.fbx")
        bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True,
                                  use_mesh_modifiers=True, path_mode="COPY",
                                  embed_textures=True)
    else:
        filepath = str(out / f"{{lod.name}}.glb")
        bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True,
                                   export_format="GLB",
                                   export_draco_mesh_compression_enable=True)

    report["output_files"].append(filepath)
    bpy.ops.object.delete(use_global=False)

# Step 6: Final validation
final_tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
report["final_tris"] = final_tris
report["within_budget"] = final_tris <= CONFIG["poly_budget"]

# Save report
(out / "pipeline_report.json").write_text(json.dumps(report, indent=2))
print(f"Pipeline complete: {{len(report['output_files'])}} files exported")
'''
```

## LOD (Level of Detail) Generation

### Blender Decimate LOD Script

```python
import bpy
from pathlib import Path

def generate_lod_chain(obj_name: str, output_dir: str,
                       lod_ratios: list = None, export_format: str = "glb",
                       preserve_uvs: bool = True):
    """Generate LOD chain using Blender's decimate modifier.

    Args:
        obj_name: Name of the source mesh object.
        lod_ratios: Reduction ratios per LOD level.
        export_format: "fbx", "glb", or "usdc".
        preserve_uvs: Use UV-aware decimation (slower but better quality).
    """
    if lod_ratios is None:
        lod_ratios = [1.0, 0.5, 0.25, 0.1, 0.05]

    src = bpy.data.objects[obj_name]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    lod_report = []

    for i, ratio in enumerate(lod_ratios):
        bpy.ops.object.select_all(action='DESELECT')
        src.select_set(True)
        bpy.context.view_layer.objects.active = src
        bpy.ops.object.duplicate()
        lod_obj = bpy.context.active_object
        lod_obj.name = f"{obj_name}_lod{i}"

        if ratio < 1.0:
            mod = lod_obj.modifiers.new(f"Decimate_LOD{i}", 'DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = ratio
            if preserve_uvs:
                mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=mod.name)

        tri_count = sum(len(p.vertices) - 2 for p in lod_obj.data.polygons)
        vert_count = len(lod_obj.data.vertices)

        lod_report.append({
            "level": i, "ratio": ratio,
            "tris": tri_count, "verts": vert_count,
        })
        print(f"LOD{i}: ratio={ratio}, tris={tri_count}, verts={vert_count}")

        # Export
        bpy.ops.object.select_all(action='DESELECT')
        lod_obj.select_set(True)
        bpy.context.view_layer.objects.active = lod_obj

        filepath = str(out / f"{obj_name}_lod{i}")
        exporters = {
            "fbx": lambda: bpy.ops.export_scene.fbx(
                filepath=filepath + ".fbx", use_selection=True,
                use_mesh_modifiers=True, mesh_smooth_type='FACE',
                path_mode='COPY', embed_textures=True),
            "glb": lambda: bpy.ops.export_scene.gltf(
                filepath=filepath + ".glb", use_selection=True,
                export_format='GLB',
                export_draco_mesh_compression_enable=True,
                export_draco_mesh_compression_level=6),
            "usdc": lambda: bpy.ops.wm.usd_export(
                filepath=filepath + ".usdc", selected_objects_only=True),
        }
        exporters[export_format]()
        bpy.ops.object.delete(use_global=False)

    return lod_report
```

### LOD Distance Thresholds

| LOD Level | Typical Ratio | Screen Coverage | Use Case |
|-----------|--------------|-----------------|----------|
| LOD0 | 100% | > 50% screen | Close-up, hero view |
| LOD1 | 50% | 25-50% screen | Mid-range |
| LOD2 | 25% | 10-25% screen | Background |
| LOD3 | 10% | 5-10% screen | Far distance |
| LOD4 | 5% | < 5% screen | Extreme distance / impostor |
| Billboard | N/A | < 2% screen | Replace with 2D sprite |

### Nanite-Aware Strategy (UE5)

UE5 Nanite virtualizes geometry and eliminates the need for manual LOD chains for static meshes. When targeting UE5:

```python
def prepare_for_nanite(obj_name: str, output_path: str):
    """Prepare mesh for UE5 Nanite (virtual geometry).

    Nanite handles LOD internally at the cluster level.
    Key: provide the highest quality mesh possible.
    No need for manual LOD chain - Nanite does it automatically.

    Requirements for Nanite:
    - Static mesh only (no skeletal/morphing)
    - Opaque or masked material (no translucency)
    - No vertex animation / WPO
    - Triangle mesh (quads get triangulated)
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj

    # For Nanite, export at full resolution (no decimation)
    # Nanite handles millions of triangles efficiently
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        # High quality normals for Nanite
        use_tspace=True,
    )
    print(f"Nanite-ready export: {output_path}")
    print("NOTE: Enable Nanite in UE5 mesh asset settings after import")
    print("NOTE: Nanite supports up to ~16M triangles per mesh efficiently")


def generate_hybrid_lod(obj_name: str, output_dir: str, use_nanite: bool = False):
    """Generate LOD appropriate for target engine.

    - UE5 with Nanite: export full-res mesh (Nanite handles LOD)
    - UE5 without Nanite: traditional LOD chain + HLOD
    - Unity: traditional LOD chain
    - Web/Mobile: aggressive LOD chain + impostor at LOD4
    """
    if use_nanite:
        prepare_for_nanite(obj_name, f"{output_dir}/{obj_name}_nanite.fbx")
    else:
        generate_lod_chain(obj_name, output_dir)
```

### Unity LOD Group Script

```csharp
// C# reference for Unity LOD Group setup
// Clay generates this as a code template
/*
LODGroup lodGroup = gameObject.AddComponent<LODGroup>();
LOD[] lods = new LOD[4];
lods[0] = new LOD(0.6f, new Renderer[] { lod0Renderer });
lods[1] = new LOD(0.3f, new Renderer[] { lod1Renderer });
lods[2] = new LOD(0.1f, new Renderer[] { lod2Renderer });
lods[3] = new LOD(0.01f, new Renderer[] { lod3Renderer });
lodGroup.SetLODs(lods);
lodGroup.RecalculateBounds();
*/
```

### Impostor / Billboard LOD

```python
def generate_impostor(obj_name: str, output_dir: str, resolution: int = 512,
                       num_angles: int = 8):
    """Generate billboard impostor for extreme LOD distances.

    Renders the model from multiple angles and creates a billboard atlas.
    Use as LOD4+ replacement for distant objects.
    """
    import math
    from pathlib import Path

    obj = bpy.data.objects[obj_name]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'

    cam = scene.camera
    distance = max(obj.dimensions) * 2.0
    center = obj.location

    for i in range(num_angles):
        angle = (2 * math.pi * i) / num_angles
        cam.location = (
            center.x + distance * math.cos(angle),
            center.y + distance * math.sin(angle),
            center.z + distance * 0.3,
        )
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        scene.render.filepath = str(out / f"impostor_{i:02d}.png")
        bpy.ops.render.render(write_still=True)

    print(f"Impostor atlas rendered: {num_angles} angles at {resolution}px")
```

## Retopology

### Blender Auto-Retopo

```python
import bpy

def auto_retopo(obj_name: str, target_faces: int = 5000,
                method: str = "voxel", symmetry: bool = False):
    """Automatic retopology using Blender's built-in tools.

    Args:
        method: "voxel" for voxel remesh, "quadriflow" for quad-based.
        symmetry: Enable symmetry-aware retopo (for characters).
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj

    if method == "voxel":
        mod = obj.modifiers.new("Remesh", 'REMESH')
        mod.mode = 'VOXEL'
        bbox = obj.dimensions
        volume = bbox.x * bbox.y * bbox.z
        mod.voxel_size = (volume / target_faces) ** (1/3) * 2
        if symmetry:
            mod.use_mirror_x = True
        bpy.ops.object.modifier_apply(modifier=mod.name)

    elif method == "quadriflow":
        bpy.ops.object.quadriflow_remesh(
            target_faces=target_faces,
            use_preserve_sharp=True,
            use_preserve_boundary=True,
            use_mesh_symmetry=symmetry,
        )

    tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"Retopo complete: {tri_count} tris (target: {target_faces})")
    return tri_count


def instant_meshes_retopo(input_path: str, output_path: str,
                           target_faces: int = 5000):
    """Retopology using Instant Meshes (external tool).

    Produces high-quality quad-dominant topology.
    Install: https://github.com/wjakob/instant-meshes
    """
    import subprocess
    result = subprocess.run([
        "instant-meshes", input_path,
        "-o", output_path,
        "-f", str(target_faces),
        "-D",  # Deterministic
        "--smooth", "2",
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Instant Meshes failed: {result.stderr}")
    print(f"Instant Meshes retopo complete: {output_path}")
```

## UV Unwrapping and Packing

### Blender UV Unwrap Script

```python
import bpy

def auto_uv_unwrap(obj_name: str, method: str = "smart", margin: float = 0.005,
                    texel_density_target: float = None):
    """Automatic UV unwrapping with quality metrics.

    Args:
        method: "smart" for Smart UV Project, "angle" for angle-based.
        texel_density_target: Target pixels per unit (e.g., 512 for 512px/m).
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    if method == "smart":
        bpy.ops.uv.smart_project(
            angle_limit=66.0,
            margin_method='SCALED',
            island_margin=margin,
            scale_to_bounds=True,
        )
    elif method == "angle":
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
    elif method == "lightmap":
        # Lightmap UV packing (non-overlapping, for baking)
        bpy.ops.uv.lightmap_pack(PREF_MARGIN_DIV=margin * 100)

    bpy.ops.object.mode_set(mode='OBJECT')

    coverage = estimate_uv_coverage(obj)
    print(f"UV coverage: {coverage:.1%}")
    if coverage < 0.80:
        print("WARNING: UV coverage below 80% target. Consider repacking.")
    return coverage


def estimate_uv_coverage(obj: bpy.types.Object) -> float:
    """Estimate UV space utilization (0.0-1.0)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0.0

    total_uv_area = 0.0
    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        n = len(uvs)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += uvs[i].x * uvs[j].y - uvs[j].x * uvs[i].y
        total_uv_area += abs(area) / 2.0

    bm.free()
    return min(total_uv_area, 1.0)
```

### UV Island Optimization

```python
def optimize_uv_islands(obj_name: str, target_texel_density: float = 10.24):
    """Normalize texel density across UV islands.

    Ensures consistent texture resolution across the model surface.
    target_texel_density: pixels per Blender unit (e.g., 10.24 = 1024px/100 units).
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Average Islands Scale normalizes texel density
    bpy.ops.uv.average_islands_scale()

    # Pack islands efficiently
    bpy.ops.uv.pack_islands(margin=0.005, rotate=True, shape_method='CONCAVE')

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"UV islands optimized for {obj_name}")
```

## Texture Baking

### PBR Texture Baking

```python
import bpy
from pathlib import Path

def bake_pbr_maps(obj_name: str, output_dir: str, resolution: int = 2048,
                   maps: list = None):
    """Bake PBR texture maps with proper color space handling."""
    if maps is None:
        maps = ["DIFFUSE", "NORMAL", "ROUGHNESS", "AO", "EMIT"]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 128

    bake_configs = {
        "DIFFUSE":   {"type": "DIFFUSE",   "suffix": "albedo",    "color_space": "sRGB"},
        "NORMAL":    {"type": "NORMAL",     "suffix": "normal",    "color_space": "Non-Color"},
        "ROUGHNESS": {"type": "ROUGHNESS",  "suffix": "roughness", "color_space": "Non-Color"},
        "AO":        {"type": "AO",         "suffix": "ao",        "color_space": "Non-Color"},
        "EMIT":      {"type": "EMIT",       "suffix": "emissive",  "color_space": "sRGB"},
    }

    for map_type in maps:
        config = bake_configs.get(map_type)
        if not config:
            continue

        filename = f"{obj_name}_{config['suffix']}.png"
        img = bpy.data.images.new(filename, resolution, resolution)
        img.colorspace_settings.name = config["color_space"]

        # Set bake target
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if not mat or not mat.use_nodes:
                continue
            nodes = mat.node_tree.nodes
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.select = True
            nodes.active = tex_node

        bpy.ops.object.bake(type=config["type"])
        img.filepath_raw = str(out / filename)
        img.file_format = 'PNG'
        img.save()
        print(f"Baked: {filename} ({resolution}x{resolution})")

    # Generate ORM packed texture (Occlusion/Roughness/Metallic)
    _pack_orm(obj_name, out, resolution)


def _pack_orm(obj_name: str, output_dir: Path, resolution: int):
    """Pack AO, Roughness, Metallic into single ORM texture.

    R = Ambient Occlusion
    G = Roughness
    B = Metallic
    """
    import numpy as np
    from PIL import Image

    ao_path = output_dir / f"{obj_name}_ao.png"
    rough_path = output_dir / f"{obj_name}_roughness.png"
    # Metallic may not exist - use black (0.0) as default
    metal_path = output_dir / f"{obj_name}_metallic.png"

    ao = np.array(Image.open(ao_path).convert('L')) if ao_path.exists() else np.full((resolution, resolution), 255, dtype=np.uint8)
    roughness = np.array(Image.open(rough_path).convert('L')) if rough_path.exists() else np.full((resolution, resolution), 128, dtype=np.uint8)
    metallic = np.array(Image.open(metal_path).convert('L')) if metal_path.exists() else np.zeros((resolution, resolution), dtype=np.uint8)

    orm = np.stack([ao, roughness, metallic], axis=-1)
    Image.fromarray(orm).save(output_dir / f"{obj_name}_orm.png")
    print(f"Packed ORM texture: {obj_name}_orm.png")
```

### Texture Atlas Generation

```python
def create_texture_atlas(objects: list, output_dir: str,
                          atlas_resolution: int = 4096):
    """Combine textures from multiple objects into a single atlas.

    Reduces draw calls from N to 1 for batched rendering.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Join UV maps
    bpy.ops.object.select_all(action='DESELECT')
    for obj_name in objects:
        bpy.data.objects[obj_name].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[objects[0]]

    # Create atlas UV map
    for obj_name in objects:
        obj = bpy.data.objects[obj_name]
        if "Atlas_UV" not in obj.data.uv_layers:
            obj.data.uv_layers.new(name="Atlas_UV")

    # Pack into atlas space
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Atlas created for {len(objects)} objects at {atlas_resolution}px")
    print(f"Draw calls reduced: {len(objects)} -> 1")
```

### Draw Call Reduction via Atlasing

| Scenario | Without Atlas | With Atlas | Improvement |
|----------|--------------|------------|-------------|
| 20 unique props | 20 draw calls | 1-2 draw calls | ~10-20x |
| 50 environment objects | 50 draw calls | 3-5 draw calls | ~10-17x |

Target: keep total draw calls under 200 for mobile, under 2000 for PC.

## Texture Compression

### gltf-transform Pipeline

```bash
# Install: npm install -g @gltf-transform/cli

# Full optimization pipeline for web/mobile
gltf-transform optimize input.glb output.glb \
  --compress draco \
  --texture-compress webp

# KTX2 + Basis Universal compression (best for games)
gltf-transform ktx2 input.glb output.glb \
  --compress uastc \
  --quality 128

# Meshoptimizer compression (alternative to Draco, better for streaming)
gltf-transform meshopt input.glb output.glb

# Full pipeline with all optimizations
gltf-transform optimize input.glb output.glb \
  --compress meshopt \
  --texture-compress ktx2 \
  --texture-size 1024
```

### Python Texture Compression Script

```python
import subprocess
from pathlib import Path

def compress_textures(input_dir: str, output_dir: str,
                       method: str = "ktx2", quality: int = 128):
    """Compress textures for game use.

    Methods:
    - "ktx2": KTX2 with Basis Universal (best cross-platform support)
    - "webp": WebP (good for web, smaller than PNG)
    - "astc": ASTC (best for mobile GPU)
    - "bc7": BC7/DXT (best for desktop GPU)
    """
    inp = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for png in inp.glob("*.png"):
        if method == "ktx2":
            output_file = out / png.with_suffix(".ktx2").name
            subprocess.run([
                "toktx", "--t2", "--encode", "uastc",
                "--uastc_quality", str(quality),
                "--zcmp", "5",
                str(output_file), str(png),
            ], check=True)

        elif method == "webp":
            output_file = out / png.with_suffix(".webp").name
            subprocess.run([
                "cwebp", "-q", str(min(quality, 95)),
                str(png), "-o", str(output_file),
            ], check=True)

        print(f"Compressed: {png.name} -> {output_file.name}")

    # Report compression ratio
    orig_size = sum(f.stat().st_size for f in inp.glob("*.png"))
    comp_size = sum(f.stat().st_size for f in out.iterdir())
    ratio = comp_size / orig_size if orig_size > 0 else 0
    print(f"Compression ratio: {ratio:.1%} ({orig_size/1024:.0f}KB -> {comp_size/1024:.0f}KB)")
```

### Compression Format Selection

| Format | Best For | GPU Decode | File Size | Quality |
|--------|----------|------------|-----------|---------|
| KTX2 (UASTC) | Universal game use | Yes | Medium | High |
| KTX2 (ETC1S) | Mobile, low memory | Yes | Small | Medium |
| BC7 (DDS) | PC/Console DirectX | Yes | Medium | High |
| ASTC | Mobile (iOS/Android) | Yes | Small-Medium | High |
| WebP | Web delivery | No (CPU) | Small | High |
| PNG | Source / archival | No (CPU) | Large | Lossless |

Rule of thumb:
- Game engines (Unity/UE5): KTX2 with UASTC or platform-native (BC7/ASTC)
- Web (Three.js/Babylon): KTX2 with Basis Universal (auto-transcodes to GPU format)
- Mobile web: KTX2 with ETC1S (smallest, GPU-decoded)

## Auto-Rigging

### Tripo Auto-Rig Integration

```python
def auto_rig_via_tripo(model_task_id: str) -> str:
    """Auto-rig a generated model using Tripo's built-in rigging.

    Tripo supports automatic skeleton generation and skinning
    for humanoid and quadruped characters.
    """
    import os
    import httpx

    api_key = os.environ["TRIPO_API_KEY"]
    resp = httpx.post(
        "https://api.tripo3d.ai/v2/openapi/task",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "type": "animate_rig",
            "original_model_task_id": model_task_id,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["data"]["task_id"]
```

### Mixamo Auto-Rig Pattern

```python
def prepare_for_mixamo(obj_name: str, output_path: str):
    """Prepare model for Mixamo auto-rigging.

    Mixamo requirements:
    - FBX format
    - Single mesh (join if multiple)
    - T-pose or A-pose
    - Facing +Z
    - < 100K triangles recommended
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj

    # Ensure single mesh
    mesh_objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if len(mesh_objects) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in mesh_objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.object.join()

    # Export for Mixamo
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        use_mesh_modifiers=True,
        bake_anim=False,
    )
    print(f"Mixamo-ready export: {output_path}")
    print("Upload to mixamo.com for auto-rigging and animation library")
```

## Engine Export Settings

### FBX (Unity / Unreal Engine)

```python
def export_for_unity(obj_name: str, output_path: str):
    """Export with Unity-optimized FBX settings."""
    obj = bpy.data.objects[obj_name]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        path_mode='COPY',
        embed_textures=True,
        bake_anim=False,
    )

def export_for_ue5(obj_name: str, output_path: str, nanite: bool = False):
    """Export with UE5-optimized FBX settings."""
    obj = bpy.data.objects[obj_name]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='X',       # UE5 forward axis
        axis_up='Z',            # UE5 up axis
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        path_mode='COPY',
        embed_textures=True,
        use_tspace=True,        # Important for Nanite normal quality
    )
    if nanite:
        print("NOTE: Enable Nanite in UE5 Static Mesh Editor after import")
```

### glTF (Web / Mobile)

```python
def export_for_web(obj_name: str, output_path: str,
                    compression: str = "draco"):
    """Export with web-optimized glTF settings."""
    obj = bpy.data.objects[obj_name]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    use_draco = compression == "draco"
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        use_selection=True,
        export_format='GLB',
        export_draco_mesh_compression_enable=use_draco,
        export_draco_mesh_compression_level=6,
        export_image_format='WEBP',
        export_image_quality=85,
        export_apply=True,
    )
    # Post-process with gltf-transform for meshopt or KTX2
    if compression == "meshopt":
        import subprocess
        subprocess.run([
            "npx", "@gltf-transform/cli", "meshopt",
            output_path, output_path,
        ], check=True)
```

## FlexiCubes (NVIDIA)

FlexiCubes is the recommended approach for differentiable mesh extraction from neural fields. Produces significantly better topology than marching cubes.

Key advantages:
- Adaptive resolution at surface boundaries
- Flexible vertex positioning (not grid-locked)
- Differentiable (integrates into training pipelines)
- Cleaner quad-dominant topology
- Used by leading providers (Trellis, Hunyuan3D 2.0)

```python
# FlexiCubes is available via NVIDIA Kaolin
# pip install kaolin

# Usage pattern:
# 1. Train neural field (SDF or occupancy)
# 2. Extract mesh with FlexiCubes
# 3. Fine-tune mesh with differentiable rendering
# 4. Export final mesh

# For implementation: https://github.com/nv-tlabs/FlexiCubes
```

## MaterialX / OpenPBR

For interchange between DCC tools and engines, use MaterialX with OpenPBR:

```xml
<?xml version="1.0"?>
<materialx version="1.39">
  <open_pbr_surface name="game_material" type="surfaceshader">
    <input name="base_color" type="color3" value="0.8, 0.6, 0.4" />
    <input name="base_metalness" type="float" value="0.0" />
    <input name="specular_roughness" type="float" value="0.5" />
    <input name="coat_weight" type="float" value="0.0" />
    <input name="emission_luminance" type="float" value="0.0" />
  </open_pbr_surface>
</materialx>
```

MaterialX is supported by: USD, Blender 4.x, Maya, Substance, UE5, Karma.

## Platform Budgets

| Platform | Verts/Scene | Tris/Model (avg) | Texture Memory | Draw Calls | Notes |
|----------|------------|-------------------|----------------|------------|-------|
| Mobile (low) | < 50K | < 3K | < 64MB | < 100 | Aggressive atlas + LOD |
| Mobile (mid) | < 100K | < 5K | < 128MB | < 200 | KTX2 ETC1S textures |
| Web (mid-range) | < 500K | < 20K | < 256MB | < 500 | Draco + WebP/KTX2 |
| PC (mid-range) | < 3M | < 100K | < 2GB | < 2000 | Standard pipeline |
| PC (high-end) | < 10M | < 500K | < 4GB | < 5000 | Full PBR, SSAO, SSR |
| Console (current gen) | < 5M | < 200K | < 4GB | < 3000 | Platform-specific compression |
| UE5 Nanite | < 100M+ | < 16M | < 8GB | Virtual | Nanite handles geometry |

Rules:
- Always validate total scene budget, not just per-model.
- LOD0 uses the per-model budget; subsequent LODs reduce by 50-75% each level.
- Texture resolution scales with importance: hero=2048-4096, standard=1024, background=512, distant=256.
- Mobile: prefer atlas textures and instance rendering.
- Web: total download size < 10MB for initial load, lazy-load rest.

## Asset Pipeline CI/CD

```yaml
# GitHub Actions workflow for asset pipeline validation
# .github/workflows/asset-pipeline.yml
name: Asset Pipeline
on:
  push:
    paths: ['assets/source/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    container:
      image: linuxserver/blender:4.2.0
    steps:
      - uses: actions/checkout@v4

      - name: Run asset pipeline
        run: |
          for model in assets/source/*.glb; do
            blender --background --python pipeline/validate.py -- "$model"
          done

      - name: Check QC reports
        run: |
          python pipeline/check_reports.py assets/output/reports/
          # Fails if any model doesn't pass game-readiness threshold

      - name: Upload optimized assets
        uses: actions/upload-artifact@v4
        with:
          name: optimized-assets
          path: assets/output/
```

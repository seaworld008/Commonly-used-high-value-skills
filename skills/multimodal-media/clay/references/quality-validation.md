# Quality Validation Reference

Topology checks, geometric metrics, perceptual quality scoring, CLIP-based validation, game-readiness scoring, and pass/fail thresholds for AI-generated 3D models.

## Geometric Metrics

### Hausdorff Distance

Measures the maximum deviation between two surfaces. Used to compare AI output against reference or between LOD levels.

```python
import trimesh
import numpy as np

def hausdorff_distance(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh,
                        sample_count: int = 10000) -> float:
    """Compute one-sided Hausdorff distance from mesh_a to mesh_b."""
    points_a = mesh_a.sample(sample_count)
    _, distances, _ = mesh_b.nearest.on_surface(points_a)
    return float(np.max(distances))

def symmetric_hausdorff(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh,
                         sample_count: int = 10000) -> float:
    """Symmetric Hausdorff distance (max of both directions)."""
    d_ab = hausdorff_distance(mesh_a, mesh_b, sample_count)
    d_ba = hausdorff_distance(mesh_b, mesh_a, sample_count)
    return max(d_ab, d_ba)
```

### Chamfer Distance

Average bidirectional nearest-neighbor distance. More robust than Hausdorff for overall shape similarity.

```python
def chamfer_distance(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh,
                      sample_count: int = 10000) -> float:
    """Compute Chamfer distance between two meshes."""
    points_a = mesh_a.sample(sample_count)
    points_b = mesh_b.sample(sample_count)

    _, dist_a_to_b, _ = mesh_b.nearest.on_surface(points_a)
    _, dist_b_to_a, _ = mesh_a.nearest.on_surface(points_b)

    return float(np.mean(dist_a_to_b**2) + np.mean(dist_b_to_a**2))
```

### Normal Consistency

Measures alignment of surface normals between meshes.

```python
def normal_consistency(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh,
                        sample_count: int = 10000) -> float:
    """Normal consistency score (0-1, higher is better)."""
    points_a = mesh_a.sample(sample_count)
    _, _, face_indices_a = mesh_a.nearest.on_surface(points_a)
    _, _, face_indices_b = mesh_b.nearest.on_surface(points_a)

    normals_a = mesh_a.face_normals[face_indices_a]
    normals_b = mesh_b.face_normals[face_indices_b]

    dot_products = np.sum(normals_a * normals_b, axis=1)
    return float(np.mean(np.clip(dot_products, 0, 1)))
```

### F1 Score (Surface Reconstruction)

Precision/recall metric for surface reconstruction quality at a given distance threshold.

```python
def f1_score(mesh_pred: trimesh.Trimesh, mesh_gt: trimesh.Trimesh,
              threshold: float = 0.01, sample_count: int = 10000) -> dict:
    """F1 score for surface reconstruction quality."""
    points_pred = mesh_pred.sample(sample_count)
    points_gt = mesh_gt.sample(sample_count)

    _, dist_pred_to_gt, _ = mesh_gt.nearest.on_surface(points_pred)
    _, dist_gt_to_pred, _ = mesh_pred.nearest.on_surface(points_gt)

    precision = float(np.mean(dist_pred_to_gt < threshold))
    recall = float(np.mean(dist_gt_to_pred < threshold))

    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    return {"precision": precision, "recall": recall, "f1": f1}
```

### Volume and Surface Area Comparison

```python
def geometry_comparison(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh) -> dict:
    """Compare geometric properties between two meshes."""
    vol_a = mesh_a.volume if mesh_a.is_watertight else None
    vol_b = mesh_b.volume if mesh_b.is_watertight else None

    return {
        "area_a": float(mesh_a.area),
        "area_b": float(mesh_b.area),
        "area_ratio": float(mesh_a.area / mesh_b.area) if mesh_b.area > 0 else None,
        "volume_a": float(vol_a) if vol_a else None,
        "volume_b": float(vol_b) if vol_b else None,
        "volume_ratio": float(vol_a / vol_b) if vol_a and vol_b else None,
        "extents_a": mesh_a.extents.tolist(),
        "extents_b": mesh_b.extents.tolist(),
    }
```

## Topology Checks

### Comprehensive Topology Validation

```python
import trimesh
import numpy as np

def check_topology(mesh: trimesh.Trimesh) -> dict:
    """Comprehensive topology check for game readiness."""
    results = {
        "is_watertight": mesh.is_watertight,
        "is_winding_consistent": mesh.is_winding_consistent,
        "euler_number": mesh.euler_number,
        "face_count": len(mesh.faces),
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "connected_components": len(mesh.split(only_watertight=False)),
    }

    # Non-manifold edges (edges shared by more than 2 faces)
    edge_face_count = {}
    for i, face in enumerate(mesh.faces):
        edges = [
            tuple(sorted([face[0], face[1]])),
            tuple(sorted([face[1], face[2]])),
            tuple(sorted([face[2], face[0]])),
        ]
        for edge in edges:
            edge_face_count.setdefault(edge, []).append(i)

    non_manifold_edges = [e for e, faces in edge_face_count.items() if len(faces) > 2]
    boundary_edges = [e for e, faces in edge_face_count.items() if len(faces) == 1]

    results["non_manifold_edges"] = len(non_manifold_edges)
    results["boundary_edges"] = len(boundary_edges)

    # Degenerate triangles (zero or near-zero area)
    areas = mesh.area_faces
    degenerate = int(np.sum(areas < 1e-10))
    results["degenerate_faces"] = degenerate

    # Thin triangles (high aspect ratio)
    # Faces with very small angles cause shading artifacts
    thin_threshold = 0.01  # radians (~0.6 degrees)
    thin_faces = 0
    for face in mesh.faces:
        verts = mesh.vertices[face]
        edges = [verts[1] - verts[0], verts[2] - verts[1], verts[0] - verts[2]]
        for j in range(3):
            e1 = edges[j]
            e2 = -edges[(j + 2) % 3]
            cos_angle = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-10)
            angle = np.arccos(np.clip(cos_angle, -1, 1))
            if angle < thin_threshold:
                thin_faces += 1
                break
    results["thin_faces"] = thin_faces

    # Isolated vertices (not connected to any face)
    used_verts = set(mesh.faces.flatten())
    results["isolated_vertices"] = len(mesh.vertices) - len(used_verts)

    # Floating geometry detection
    components = mesh.split(only_watertight=False)
    if len(components) > 1:
        main_volume = max(c.convex_hull.volume for c in components)
        floating = [c for c in components
                    if c.convex_hull.volume < main_volume * 0.01]
        results["floating_fragments"] = len(floating)
    else:
        results["floating_fragments"] = 0

    return results
```

### Full Model Validation

```python
import trimesh
import numpy as np
import json
from pathlib import Path

def validate_model(filepath: str, poly_budget: int = 50000,
                    quality_tier: str = "game-ready") -> dict:
    """Full validation of a 3D model file for game readiness."""
    mesh = trimesh.load(filepath, force='mesh')

    topo = check_topology(mesh)

    # Bounding box
    extents = mesh.extents.tolist()
    center = mesh.centroid.tolist()

    # Face type analysis
    tri_count = len(mesh.faces)  # trimesh always triangulates

    report = {
        "file": filepath,
        "topology": topo,
        "geometry": {
            "extents": extents,
            "center": center,
            "surface_area": float(mesh.area),
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "bounding_sphere_radius": float(np.max(np.linalg.norm(
                mesh.vertices - mesh.centroid, axis=1))),
        },
        "budget": {
            "poly_budget": poly_budget,
            "actual_tris": tri_count,
            "actual_verts": len(mesh.vertices),
            "within_budget": tri_count <= poly_budget,
            "utilization": tri_count / poly_budget,
        },
        "issues": [],
        "warnings": [],
    }

    # Critical issues (fail)
    if topo["non_manifold_edges"] > 0:
        report["issues"].append(f"Non-manifold edges: {topo['non_manifold_edges']}")
    if topo["degenerate_faces"] > 0:
        report["issues"].append(f"Degenerate faces: {topo['degenerate_faces']}")
    if not topo["is_winding_consistent"]:
        report["issues"].append("Inconsistent face winding")
    if tri_count > poly_budget:
        report["issues"].append(f"Over poly budget: {tri_count} > {poly_budget}")

    # Warnings (non-blocking but should be addressed)
    if not topo["is_watertight"]:
        report["warnings"].append("Mesh is not watertight")
    if topo["floating_fragments"] > 0:
        report["warnings"].append(f"Floating geometry fragments: {topo['floating_fragments']}")
    if topo["thin_faces"] > tri_count * 0.01:
        report["warnings"].append(f"Thin faces: {topo['thin_faces']} ({topo['thin_faces']/tri_count:.1%})")
    if topo["isolated_vertices"] > 0:
        report["warnings"].append(f"Isolated vertices: {topo['isolated_vertices']}")
    if topo["connected_components"] > 1:
        report["warnings"].append(f"Multiple components: {topo['connected_components']}")

    # Tier-aware pass/fail
    if quality_tier == "draft":
        report["pass"] = True  # Drafts always pass basic check
    elif quality_tier == "game-ready":
        report["pass"] = len(report["issues"]) == 0
    else:  # production
        report["pass"] = len(report["issues"]) == 0 and len(report["warnings"]) == 0

    return report
```

## UV Analysis

```python
def analyze_uv(mesh: trimesh.Trimesh) -> dict:
    """Analyze UV quality metrics."""
    if not hasattr(mesh.visual, 'uv') or mesh.visual.uv is None:
        return {"has_uv": False, "issues": ["No UV coordinates found"]}

    uv = mesh.visual.uv

    # Basic checks
    out_of_range = int(np.sum((uv < 0) | (uv > 1)))

    # Overlapping UV detection
    overlapping_islands = _detect_uv_overlaps(uv, mesh.faces)

    # Texel density variance
    face_areas_3d = mesh.area_faces
    uv_areas = []
    for face in mesh.faces:
        uvs = uv[face]
        area = abs(
            (uvs[1][0] - uvs[0][0]) * (uvs[2][1] - uvs[0][1]) -
            (uvs[2][0] - uvs[0][0]) * (uvs[1][1] - uvs[0][1])
        ) / 2.0
        uv_areas.append(area)

    uv_areas = np.array(uv_areas)
    valid = (face_areas_3d > 1e-10) & (uv_areas > 1e-10)

    if np.sum(valid) > 0:
        texel_densities = uv_areas[valid] / face_areas_3d[valid]
        density_variance = float(np.std(texel_densities) / (np.mean(texel_densities) + 1e-10))
        density_min = float(np.min(texel_densities))
        density_max = float(np.max(texel_densities))
        density_mean = float(np.mean(texel_densities))
    else:
        density_variance = float('inf')
        density_min = density_max = density_mean = 0.0

    total_uv_area = float(np.sum(uv_areas))

    issues = []
    if total_uv_area < 0.50:
        issues.append(f"Very low UV coverage ({total_uv_area:.1%})")
    elif total_uv_area < 0.80:
        issues.append(f"Low UV coverage ({total_uv_area:.1%}) - target >80%")
    if density_variance > 0.5:
        issues.append(f"High texel density variance ({density_variance:.2f}) - target <0.3")
    elif density_variance > 0.3:
        issues.append(f"Moderate texel density variance ({density_variance:.2f})")
    if out_of_range > 0:
        issues.append(f"UV coords out of 0-1 range: {out_of_range}")
    if overlapping_islands > 0:
        issues.append(f"Overlapping UV islands detected: {overlapping_islands}")

    return {
        "has_uv": True,
        "uv_coverage": min(total_uv_area, 1.0),
        "out_of_range_coords": out_of_range,
        "texel_density_variance": density_variance,
        "texel_density_min": density_min,
        "texel_density_max": density_max,
        "texel_density_mean": density_mean,
        "overlapping_islands": overlapping_islands,
        "issues": issues,
    }


def _detect_uv_overlaps(uv: np.ndarray, faces: np.ndarray,
                          grid_resolution: int = 256) -> int:
    """Detect overlapping UV islands using rasterization."""
    grid = np.zeros((grid_resolution, grid_resolution), dtype=np.int32)
    overlap_count = 0

    for face in faces:
        uvs = uv[face]
        # Bounding box in UV space
        min_u, min_v = np.min(uvs, axis=0)
        max_u, max_v = np.max(uvs, axis=0)

        i_min = max(0, int(min_u * grid_resolution))
        i_max = min(grid_resolution - 1, int(max_u * grid_resolution))
        j_min = max(0, int(min_v * grid_resolution))
        j_max = min(grid_resolution - 1, int(max_v * grid_resolution))

        for i in range(i_min, i_max + 1):
            for j in range(j_min, j_max + 1):
                if grid[i, j] > 0:
                    overlap_count += 1
                grid[i, j] += 1

    return overlap_count
```

## CLIP-Based Quality Scoring

Use CLIP to evaluate if the generated 3D model matches the original prompt semantically.

```python
def clip_quality_score(rendered_images: list, prompt: str,
                        model_name: str = "ViT-B/32") -> dict:
    """Evaluate visual quality of rendered 3D model views against prompt.

    Args:
        rendered_images: List of paths to rendered views (8+ recommended).
        prompt: Original generation prompt.
        model_name: CLIP model to use.

    Returns:
        Dict with per-view and aggregate CLIP scores.
    """
    try:
        import clip
        import torch
        from PIL import Image
    except ImportError:
        return {"error": "Install: pip install openai-clip torch pillow",
                "score": None}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load(model_name, device=device)

    text_tokens = clip.tokenize([prompt]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

    scores = []
    for img_path in rendered_images:
        image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = model.encode_image(image)
            image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).item()
        scores.append({"view": img_path, "score": similarity})

    avg_score = sum(s["score"] for s in scores) / len(scores) if scores else 0

    return {
        "prompt": prompt,
        "model": model_name,
        "per_view_scores": scores,
        "average_score": avg_score,
        "min_score": min(s["score"] for s in scores) if scores else 0,
        "max_score": max(s["score"] for s in scores) if scores else 0,
        "pass": avg_score > 0.25,  # Threshold based on CLIP score distribution
        "quality_label": _clip_quality_label(avg_score),
    }


def _clip_quality_label(score: float) -> str:
    if score > 0.32:
        return "excellent"
    if score > 0.28:
        return "good"
    if score > 0.24:
        return "acceptable"
    if score > 0.20:
        return "poor"
    return "very_poor"
```

### Multi-View Render for CLIP Validation

```python
def render_for_clip(mesh_path: str, output_dir: str, num_views: int = 8,
                     resolution: int = 512) -> list:
    """Render turntable views for CLIP-based quality evaluation.

    Generates a Blender script that renders the model from multiple angles.
    """
    script = f'''
import bpy
import math
from pathlib import Path

bpy.ops.wm.read_homefile(use_empty=True)

# Import model
ext = "{mesh_path}".rsplit(".", 1)[-1].lower()
if ext in ("glb", "gltf"):
    bpy.ops.import_scene.gltf(filepath="{mesh_path}")
elif ext == "fbx":
    bpy.ops.import_scene.fbx(filepath="{mesh_path}")
elif ext == "obj":
    bpy.ops.wm.obj_import(filepath="{mesh_path}")

# Find mesh objects
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("No mesh objects found")

# Calculate bounding center
import mathutils
centers = [o.matrix_world @ mathutils.Vector(o.bound_box[0]) for o in meshes]
center = sum(centers, mathutils.Vector()) / len(centers)
max_dim = max(max(o.dimensions) for o in meshes)
distance = max_dim * 2.5

# Setup render
scene = bpy.context.scene
scene.render.resolution_x = {resolution}
scene.render.resolution_y = {resolution}
scene.render.film_transparent = True
scene.render.engine = "BLENDER_EEVEE_NEXT"

# Camera
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam

# Light
bpy.ops.object.light_add(type="SUN", location=(5, 5, 10))
bpy.context.object.data.energy = 3.0

# Render views
out = Path("{output_dir}")
out.mkdir(parents=True, exist_ok=True)
views = []

for i in range({num_views}):
    angle = (2 * math.pi * i) / {num_views}
    cam.location = (
        center.x + distance * math.cos(angle),
        center.y + distance * math.sin(angle),
        center.z + distance * 0.4,
    )
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    filepath = str(out / f"clip_view_{{i:02d}}.png")
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    views.append(filepath)

# Save view list
import json
(out / "clip_views.json").write_text(json.dumps(views))
'''
    return script
```

## PBR Material Validation

```python
def validate_pbr_textures(albedo_path: str = None, normal_path: str = None,
                           roughness_path: str = None, metallic_path: str = None,
                           orm_path: str = None) -> dict:
    """Validate PBR texture maps for common issues."""
    from PIL import Image
    import numpy as np

    issues = []
    warnings = []
    report = {}

    def check_power_of_two(shape):
        return all(s & (s - 1) == 0 and s > 0 for s in shape[:2])

    def check_square(shape):
        return shape[0] == shape[1]

    if albedo_path:
        img = np.array(Image.open(albedo_path))
        report["albedo"] = {
            "resolution": list(img.shape[:2]),
            "is_power_of_two": check_power_of_two(img.shape),
            "is_square": check_square(img.shape),
            "has_alpha": img.shape[2] == 4 if len(img.shape) > 2 else False,
            "avg_luminance": float(np.mean(img[:, :, :3]) / 255),
        }
        if not report["albedo"]["is_power_of_two"]:
            warnings.append("Albedo: non-power-of-two resolution (GPU inefficient)")
        # Check for overly dark or bright albedo
        avg_lum = report["albedo"]["avg_luminance"]
        if avg_lum < 0.04:
            warnings.append(f"Albedo: very dark (avg luminance {avg_lum:.2f})")
        if avg_lum > 0.92:
            warnings.append(f"Albedo: very bright (avg luminance {avg_lum:.2f})")

    if normal_path:
        img = np.array(Image.open(normal_path).convert('RGB')).astype(float) / 255.0
        avg_blue = float(np.mean(img[:, :, 2]))
        avg_red = float(np.mean(img[:, :, 0]))
        avg_green = float(np.mean(img[:, :, 1]))
        report["normal"] = {
            "avg_rgb": [avg_red, avg_green, avg_blue],
            "is_power_of_two": check_power_of_two(img.shape),
        }
        if avg_blue < 0.4:
            issues.append(f"Normal map: low blue channel ({avg_blue:.2f}), may be inverted or damaged")
        if abs(avg_red - 0.5) > 0.15 or abs(avg_green - 0.5) > 0.15:
            warnings.append(f"Normal map: unusual red/green average (R={avg_red:.2f} G={avg_green:.2f}), expected ~0.5")

    if roughness_path:
        img = np.array(Image.open(roughness_path).convert('L')).astype(float) / 255.0
        report["roughness"] = {
            "min": float(np.min(img)),
            "max": float(np.max(img)),
            "mean": float(np.mean(img)),
            "std": float(np.std(img)),
        }
        if np.min(img) == 0 and np.max(img) == 1:
            warnings.append("Roughness: full 0-1 range may cause extreme visual artifacts")
        if np.std(img) < 0.01:
            warnings.append("Roughness: nearly uniform - may look unrealistic")

    if metallic_path:
        img = np.array(Image.open(metallic_path).convert('L')).astype(float) / 255.0
        report["metallic"] = {
            "min": float(np.min(img)),
            "max": float(np.max(img)),
            "mean": float(np.mean(img)),
        }
        # Metallic should be mostly 0 or 1 (binary), not gradients
        mid_range = np.sum((img > 0.1) & (img < 0.9)) / img.size
        if mid_range > 0.2:
            warnings.append(f"Metallic: {mid_range:.0%} of pixels in 0.1-0.9 range (should be mostly 0 or 1)")

    if orm_path:
        img = np.array(Image.open(orm_path))
        if len(img.shape) == 3 and img.shape[2] >= 3:
            report["orm"] = {
                "ao_mean": float(np.mean(img[:, :, 0]) / 255),
                "roughness_mean": float(np.mean(img[:, :, 1]) / 255),
                "metallic_mean": float(np.mean(img[:, :, 2]) / 255),
            }
        else:
            issues.append("ORM texture must be RGB (3 channels)")

    report["issues"] = issues
    report["warnings"] = warnings
    report["pass"] = len(issues) == 0
    return report
```

## Game-Readiness Scoring

### Pass/Fail Thresholds by Quality Tier

| Check | Draft | Game-ready | Production |
|-------|-------|------------|------------|
| Manifold | Warn | Required | Required |
| Watertight | Skip | Warn | Required |
| Within poly budget | Skip | Required | Required |
| No degenerate faces | Warn | Required | Required |
| No thin faces (>1%) | Skip | Warn | Required |
| No floating geometry | Skip | Warn | Required |
| UV coverage > 80% | Skip | Required | Required |
| Texel density variance < 0.3 | Skip | Warn | Required |
| No UV overlaps | Skip | Required | Required |
| No n-gons | Skip | Required | Required |
| LOD chain present | Skip | Required | Required |
| PBR textures valid | Skip | Warn | Required |
| Consistent winding | Warn | Required | Required |
| CLIP score > 0.25 | Skip | Skip | Warn |
| Single component | Skip | Warn | Required |

### Scoring Function

```python
def game_readiness_score(validation_report: dict, uv_report: dict = None,
                          pbr_report: dict = None, clip_report: dict = None,
                          quality_tier: str = "game-ready") -> dict:
    """Compute comprehensive game-readiness score."""
    topo = validation_report["topology"]

    checks = {
        "manifold": topo["non_manifold_edges"] == 0,
        "watertight": topo["is_watertight"],
        "within_budget": validation_report["budget"]["within_budget"],
        "no_degenerate": topo["degenerate_faces"] == 0,
        "no_thin_faces": topo.get("thin_faces", 0) < topo["face_count"] * 0.01,
        "no_floating": topo.get("floating_fragments", 0) == 0,
        "consistent_winding": topo["is_winding_consistent"],
        "single_component": topo.get("connected_components", 1) == 1,
    }

    # UV checks
    if uv_report and uv_report.get("has_uv"):
        checks["uv_coverage"] = uv_report.get("uv_coverage", 0) >= 0.80
        checks["texel_density"] = uv_report.get("texel_density_variance", 1.0) < 0.3
        checks["no_uv_overlaps"] = uv_report.get("overlapping_islands", 0) == 0

    # PBR checks
    if pbr_report:
        checks["pbr_valid"] = pbr_report.get("pass", False)

    # CLIP checks
    if clip_report:
        checks["clip_quality"] = clip_report.get("average_score", 0) > 0.25

    weights = {
        "draft": {
            "manifold": 0.15, "watertight": 0, "within_budget": 0,
            "no_degenerate": 0.15, "no_thin_faces": 0, "no_floating": 0,
            "consistent_winding": 0.1, "single_component": 0,
            "uv_coverage": 0, "texel_density": 0, "no_uv_overlaps": 0,
            "pbr_valid": 0, "clip_quality": 0,
        },
        "game-ready": {
            "manifold": 0.15, "watertight": 0.05, "within_budget": 0.15,
            "no_degenerate": 0.10, "no_thin_faces": 0.05, "no_floating": 0.05,
            "consistent_winding": 0.10, "single_component": 0.05,
            "uv_coverage": 0.10, "texel_density": 0.05, "no_uv_overlaps": 0.05,
            "pbr_valid": 0.05, "clip_quality": 0.05,
        },
        "production": {
            "manifold": 0.12, "watertight": 0.08, "within_budget": 0.12,
            "no_degenerate": 0.08, "no_thin_faces": 0.06, "no_floating": 0.06,
            "consistent_winding": 0.08, "single_component": 0.06,
            "uv_coverage": 0.08, "texel_density": 0.06, "no_uv_overlaps": 0.06,
            "pbr_valid": 0.06, "clip_quality": 0.08,
        },
    }

    tier_weights = weights.get(quality_tier, weights["game-ready"])
    score = sum(
        tier_weights.get(k, 0) * (1.0 if checks.get(k, False) else 0.0)
        for k in tier_weights
    )

    # Normalize to account for available checks
    max_possible = sum(tier_weights.get(k, 0) for k in checks)
    if max_possible > 0:
        score = score / max_possible

    return {
        "quality_tier": quality_tier,
        "score": round(score, 3),
        "max_score": 1.0,
        "pass": score >= 0.80,
        "grade": _score_to_grade(score),
        "checks": checks,
        "weights": tier_weights,
        "failed_checks": [k for k, v in checks.items() if not v and tier_weights.get(k, 0) > 0],
    }


def _score_to_grade(score: float) -> str:
    if score >= 0.95:
        return "A+"
    if score >= 0.90:
        return "A"
    if score >= 0.85:
        return "B+"
    if score >= 0.80:
        return "B"
    if score >= 0.70:
        return "C"
    if score >= 0.60:
        return "D"
    return "F"
```

## Automated Regression Testing

```python
def regression_test(new_model: str, reference_model: str,
                     thresholds: dict = None) -> dict:
    """Compare new model against reference for regression detection.

    Run this when regenerating assets to ensure quality hasn't degraded.
    """
    if thresholds is None:
        thresholds = {
            "hausdorff_max": 0.05,
            "chamfer_max": 0.001,
            "normal_consistency_min": 0.85,
            "f1_min": 0.90,
            "poly_count_variance": 0.20,  # Allow 20% variance
        }

    mesh_new = trimesh.load(new_model, force='mesh')
    mesh_ref = trimesh.load(reference_model, force='mesh')

    h_dist = symmetric_hausdorff(mesh_new, mesh_ref)
    c_dist = chamfer_distance(mesh_new, mesh_ref)
    n_cons = normal_consistency(mesh_new, mesh_ref)
    f1 = f1_score(mesh_new, mesh_ref)

    poly_new = len(mesh_new.faces)
    poly_ref = len(mesh_ref.faces)
    poly_variance = abs(poly_new - poly_ref) / poly_ref if poly_ref > 0 else 0

    results = {
        "hausdorff": {"value": h_dist, "threshold": thresholds["hausdorff_max"],
                      "pass": h_dist <= thresholds["hausdorff_max"]},
        "chamfer": {"value": c_dist, "threshold": thresholds["chamfer_max"],
                    "pass": c_dist <= thresholds["chamfer_max"]},
        "normal_consistency": {"value": n_cons, "threshold": thresholds["normal_consistency_min"],
                               "pass": n_cons >= thresholds["normal_consistency_min"]},
        "f1_score": {"value": f1["f1"], "threshold": thresholds["f1_min"],
                     "pass": f1["f1"] >= thresholds["f1_min"]},
        "poly_count": {"new": poly_new, "reference": poly_ref,
                       "variance": poly_variance,
                       "threshold": thresholds["poly_count_variance"],
                       "pass": poly_variance <= thresholds["poly_count_variance"]},
    }

    all_pass = all(r["pass"] for r in results.values())
    return {"pass": all_pass, "metrics": results}
```

## Complete QC Pipeline

```python
def full_qc_pipeline(model_path: str, prompt: str = "",
                      poly_budget: int = 10000,
                      quality_tier: str = "game-ready",
                      reference_model: str = None) -> dict:
    """Run complete QC pipeline on a model.

    Steps:
    1. Topology validation
    2. UV analysis
    3. PBR texture validation (if textures present)
    4. CLIP scoring (if prompt provided and views can be rendered)
    5. Regression test (if reference model provided)
    6. Game-readiness scoring
    """
    mesh = trimesh.load(model_path, force='mesh')

    # 1. Topology
    topo_report = validate_model(model_path, poly_budget, quality_tier)

    # 2. UV
    uv_report = analyze_uv(mesh)

    # 3. PBR (check for associated texture files)
    pbr_report = None
    model_dir = Path(model_path).parent
    base_name = Path(model_path).stem
    albedo = model_dir / f"{base_name}_albedo.png"
    normal = model_dir / f"{base_name}_normal.png"
    if albedo.exists() or normal.exists():
        pbr_report = validate_pbr_textures(
            albedo_path=str(albedo) if albedo.exists() else None,
            normal_path=str(normal) if normal.exists() else None,
        )

    # 4. CLIP scoring (requires rendering - return script if needed)
    clip_report = None

    # 5. Regression
    regression_report = None
    if reference_model:
        regression_report = regression_test(model_path, reference_model)

    # 6. Game-readiness
    score = game_readiness_score(
        topo_report, uv_report, pbr_report, clip_report, quality_tier
    )

    return {
        "model": model_path,
        "quality_tier": quality_tier,
        "topology": topo_report,
        "uv": uv_report,
        "pbr": pbr_report,
        "clip": clip_report,
        "regression": regression_report,
        "game_readiness": score,
        "overall_pass": score["pass"],
    }
```

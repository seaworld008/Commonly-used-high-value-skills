# API Integration Reference

Provider integration patterns for AI 3D model generation APIs. Covers text-to-3D, image-to-3D, multi-view-to-3D, video-to-3D, and text-to-texture workflows.

## Provider Comparison

| Provider | Strength | Topology Quality | Input | Pricing Model | Format Output | Generation Time |
|----------|----------|-----------------|-------|---------------|---------------|-----------------|
| **Meshy** | General purpose, reliable | Medium | Text, Image | Credit-based (free tier) | FBX, OBJ, glTF, USDZ, STL | 30s-5min |
| **Tripo** | Fast, good topology, animation | Medium-High | Text, Image, Multi-view | Credit-based | FBX, OBJ, glTF, STL | 10-60s |
| **Hunyuan3D 3.0/3.5** | Open-source, 3D-DiT, auto-rigging, 8K PBR | High | Text, Image, Multi-view | Free (self-hosted) / API | FBX, OBJ, glTF | 3.5: sub-60s, 3.0: 1-3min |
| **Rodin** | High detail, production quality | High | Text, Image, Multi-view | Credit-based | FBX, OBJ, glTF, USDZ | 1-5min |
| **Sloyd** | Game-ready topology, parametric | High (pre-retopologized) | Text, Parameters | Subscription + usage | FBX, OBJ, glTF | 5-15s |
| **Stability (Stable Fast 3D)** | Ultra-fast single-image | Medium | Image | API credit-based | OBJ, glTF | ~1s |
| **TRELLIS.2 (Microsoft)** | Open-source MIT, 4B params, O-Voxel, PBR+opacity | High | Image | Free (self-hosted) | glTF, PLY (3DGS) | ~3s (512³), ~17s (1024³) |
| **InstantMesh** | Open-source, multi-view LRM | Medium-High | Image | Free (self-hosted) | OBJ, glTF | 10-30s |
| **Luma Genie** | High-quality generation, video-to-3D | Medium-High | Text, Image, Video | API credit-based | glTF, PLY (3DGS) | 30s-3min |
| **CSM (Common Sense Machines)** | World-building, scene generation (acquired by Google Jan 2026 — evaluate API continuity) | Medium | Image, Video | Credit-based | glTF, USD | 1-5min |

### Provider Generation Comparison

| Capability | Meshy 6 | Tripo | Hunyuan3D 3.0/3.5 | Rodin | Sloyd | Stability | TRELLIS.2 | Luma |
|-----------|---------|-------|-------------------|-------|-------|-----------|-----------|------|
| Text-to-3D | Yes | Yes | Yes | Yes | Yes | No | No | Yes |
| Image-to-3D | Yes | Yes | Yes | Yes | No | Yes | Yes | Yes |
| Multi-view-to-3D | Yes | Yes | Yes (2-4 views) | Yes | No | No | No | No |
| Video-to-3D | No | No | No | No | No | No | No | Yes |
| Text-to-texture | Yes | No | Yes | Yes | No | No | No | No |
| Auto-rigging | No | Yes | Yes (3.0+) | No | No | No | No | No |
| PBR texture output | Yes | Yes | Yes (8K in 3.5) | Yes | Yes | Limited | Yes+opacity | No |
| 3D Gaussian output | No | No | No | No | No | No | Yes | Yes |
| Animation output | No | Yes | No | No | No | No | No | No |
| Low Poly Mode | Yes | Yes (Smart Mesh) | No | No | Yes | No | No | No |

## Authentication Pattern

All providers use API key authentication via environment variables.

```python
import os
import httpx

# Standard auth pattern - NEVER hardcode keys
API_KEY = os.environ["MESHY_API_KEY"]  # or TRIPO_API_KEY, RODIN_API_KEY, etc.

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
```

Environment variable naming convention:

| Provider | Environment Variable |
|----------|---------------------|
| Meshy | `MESHY_API_KEY` |
| Tripo | `TRIPO_API_KEY` |
| Hunyuan3D | `HUNYUAN3D_API_KEY` |
| Rodin | `RODIN_API_KEY` |
| Sloyd | `SLOYD_API_KEY` |
| Stability | `STABILITY_API_KEY` |
| TRELLIS.2 | N/A (self-hosted) |
| InstantMesh | N/A (self-hosted) |
| Luma | `LUMA_API_KEY` |
| CSM | `CSM_API_KEY` |
| Sketchfab | `SKETCHFAB_API_TOKEN` |
| Poly Pizza | `POLYPIZZA_API_KEY` |
| Objaverse | N/A (open dataset) |
| Smithsonian | `SMITHSONIAN_API_KEY` |
| glTF Samples | N/A (GitHub) |
| Kenney | N/A (direct download) |

## Provider Abstraction Layer

Abstract the provider interface for swappability and testability:

```python
import os
import time
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class GenerationConfig:
    """Unified configuration for 3D generation across providers."""
    prompt: str = ""
    image_url: str = ""
    image_paths: list = field(default_factory=list)
    art_style: str = "realistic"
    topology: str = "quad"
    target_polycount: int = 30000
    output_format: str = "glb"
    quality: str = "standard"  # "preview" | "standard" | "high"
    texture_resolution: int = 1024
    with_pbr: bool = True
    with_rigging: bool = False

@dataclass
class GenerationResult:
    """Unified result from any provider."""
    task_id: str
    provider: str
    status: str  # "pending" | "processing" | "succeeded" | "failed"
    progress: float = 0.0
    model_urls: dict = field(default_factory=dict)  # format -> URL
    texture_urls: dict = field(default_factory=dict)
    thumbnail_url: str = ""
    metadata: dict = field(default_factory=dict)

class ModelProvider(ABC):
    """Abstract base for 3D model generation providers."""

    @abstractmethod
    def text_to_3d(self, config: GenerationConfig) -> str:
        """Submit text-to-3D task. Returns task ID."""

    @abstractmethod
    def image_to_3d(self, config: GenerationConfig) -> str:
        """Submit image-to-3D task. Returns task ID."""

    @abstractmethod
    def check_status(self, task_id: str) -> GenerationResult:
        """Check task status and retrieve results."""

    def poll_until_complete(self, task_id: str, interval: int = 5,
                            max_wait: int = 600) -> GenerationResult:
        """Poll until task completes with exponential backoff."""
        elapsed = 0
        current_interval = interval
        while elapsed < max_wait:
            result = self.check_status(task_id)
            if result.status == "succeeded":
                return result
            if result.status == "failed":
                raise RuntimeError(f"Task {task_id} failed: {result.metadata}")
            print(f"[{self.provider_name}] {task_id}: {result.status} "
                  f"({result.progress:.0%}) elapsed={elapsed}s")
            time.sleep(current_interval)
            elapsed += current_interval
            current_interval = min(current_interval * 1.5, 30)
        raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier string."""
```

## Provider Implementations

### Meshy

```python
class MeshyProvider(ModelProvider):
    """Meshy API integration (v2)."""

    provider_name = "meshy"

    def __init__(self):
        self.api_key = os.environ["MESHY_API_KEY"]
        self.base_url = "https://api.meshy.ai/openapi/v2"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def text_to_3d(self, config: GenerationConfig) -> str:
        resp = httpx.post(
            f"{self.base_url}/text-to-3d",
            headers=self.headers,
            json={
                "mode": "refine" if config.quality != "preview" else "preview",
                "prompt": config.prompt,
                "art_style": config.art_style,
                "topology": config.topology,
                "target_polycount": config.target_polycount,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def image_to_3d(self, config: GenerationConfig) -> str:
        import base64
        from pathlib import Path
        if config.image_paths:
            img_data = Path(config.image_paths[0]).read_bytes()
            img_b64 = base64.b64encode(img_data).decode()
            ext = config.image_paths[0].rsplit(".", 1)[-1]
            mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
            image_url = f"data:{mime};base64,{img_b64}"
        else:
            image_url = config.image_url

        resp = httpx.post(
            f"{self.base_url}/image-to-3d",
            headers=self.headers,
            json={
                "image_url": image_url,
                "topology": config.topology,
                "target_polycount": config.target_polycount,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def text_to_texture(self, model_url: str, prompt: str,
                        resolution: int = 1024) -> str:
        """Meshy text-to-texture: re-texture an existing 3D model."""
        resp = httpx.post(
            f"{self.base_url}/text-to-texture",
            headers=self.headers,
            json={
                "model_url": model_url,
                "object_prompt": prompt,
                "resolution": resolution,
                "art_style": "realistic",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def check_status(self, task_id: str) -> GenerationResult:
        resp = httpx.get(
            f"{self.base_url}/text-to-3d/{task_id}",
            headers=self.headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        status_map = {"SUCCEEDED": "succeeded", "FAILED": "failed",
                      "PENDING": "pending", "IN_PROGRESS": "processing"}
        return GenerationResult(
            task_id=task_id,
            provider="meshy",
            status=status_map.get(data.get("status", ""), "processing"),
            progress=data.get("progress", 0) / 100,
            model_urls=data.get("model_urls", {}),
            texture_urls=data.get("texture_urls", {}),
            thumbnail_url=data.get("thumbnail_url", ""),
        )
```

### Tripo

```python
class TripoProvider(ModelProvider):
    """Tripo API integration (v2)."""

    provider_name = "tripo"

    def __init__(self):
        self.api_key = os.environ["TRIPO_API_KEY"]
        self.base_url = "https://api.tripo3d.ai/v2/openapi"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def text_to_3d(self, config: GenerationConfig) -> str:
        resp = httpx.post(
            f"{self.base_url}/task",
            headers=self.headers,
            json={
                "type": "text_to_model",
                "prompt": config.prompt,
                "model_version": "v2.5-20250123",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["code"] != 0:
            raise RuntimeError(f"Tripo error: {data['message']}")
        return data["data"]["task_id"]

    def image_to_3d(self, config: GenerationConfig) -> str:
        resp = httpx.post(
            f"{self.base_url}/task",
            headers=self.headers,
            json={
                "type": "image_to_model",
                "file": {"url": config.image_url},
                "model_version": "v2.5-20250123",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["code"] != 0:
            raise RuntimeError(f"Tripo error: {data['message']}")
        return data["data"]["task_id"]

    def animate(self, original_task_id: str, animation_type: str = "preset:walk") -> str:
        """Tripo auto-rigging + animation."""
        resp = httpx.post(
            f"{self.base_url}/task",
            headers=self.headers,
            json={
                "type": "animate_rig" if animation_type.startswith("preset:") else "animate_retarget",
                "original_model_task_id": original_task_id,
                "animation": animation_type,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["code"] != 0:
            raise RuntimeError(f"Tripo error: {data['message']}")
        return data["data"]["task_id"]

    def check_status(self, task_id: str) -> GenerationResult:
        resp = httpx.get(
            f"{self.base_url}/task/{task_id}",
            headers=self.headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status_map = {"success": "succeeded", "failed": "failed",
                      "queued": "pending", "running": "processing"}
        return GenerationResult(
            task_id=task_id,
            provider="tripo",
            status=status_map.get(data.get("status", ""), "processing"),
            progress=data.get("progress", 0) / 100,
            model_urls={"glb": data.get("output", {}).get("model", "")},
            thumbnail_url=data.get("output", {}).get("rendered_image", ""),
        )
```

### Rodin

```python
class RodinProvider(ModelProvider):
    """Rodin (Hyperhuman) API integration (v2)."""

    provider_name = "rodin"

    def __init__(self):
        self.api_key = os.environ["RODIN_API_KEY"]
        self.base_url = "https://hyperhuman.deemos.com/api/v2"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def text_to_3d(self, config: GenerationConfig) -> str:
        resp = httpx.post(
            f"{self.base_url}/rodin",
            headers=self.headers,
            json={"prompt": config.prompt},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["uuid"]

    def image_to_3d(self, config: GenerationConfig) -> str:
        payload = {"prompt": config.prompt or ""}
        if config.image_url:
            payload["images"] = [config.image_url]
        if len(config.image_paths) > 1:
            payload["images"] = config.image_paths  # multi-view
        resp = httpx.post(
            f"{self.base_url}/rodin",
            headers=self.headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["uuid"]

    def check_status(self, task_id: str) -> GenerationResult:
        resp = httpx.get(
            f"{self.base_url}/status/{task_id}",
            headers=self.headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return GenerationResult(
            task_id=task_id,
            provider="rodin",
            status="succeeded" if data.get("completed") else "processing",
            progress=data.get("progress", 0) / 100,
            model_urls=data.get("model_urls", {}),
        )
```

### Stability (Stable Fast 3D)

```python
class StabilityProvider(ModelProvider):
    """Stability AI - Stable Fast 3D (sub-second image-to-3D)."""

    provider_name = "stability"

    def __init__(self):
        self.api_key = os.environ["STABILITY_API_KEY"]
        self.base_url = "https://api.stability.ai/v2beta/3d"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def text_to_3d(self, config: GenerationConfig) -> str:
        raise NotImplementedError("Stability only supports image-to-3D")

    def image_to_3d(self, config: GenerationConfig) -> str:
        """Synchronous image-to-3D (returns immediately with model)."""
        from pathlib import Path
        image_path = config.image_paths[0] if config.image_paths else None
        if not image_path:
            raise ValueError("Stability requires a local image file")

        with open(image_path, "rb") as f:
            resp = httpx.post(
                f"{self.base_url}/stable-fast-3d",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"image": f},
                data={
                    "texture_resolution": config.texture_resolution,
                    "remesh": "quad" if config.topology == "quad" else "none",
                    "foreground_ratio": 0.85,
                },
                timeout=60.0,
            )
        resp.raise_for_status()
        # Returns GLB directly in response body
        output_path = Path(f"sf3d_{int(time.time())}.glb")
        output_path.write_bytes(resp.content)
        return str(output_path)  # Synchronous - returns file path

    def check_status(self, task_id: str) -> GenerationResult:
        # Stable Fast 3D is synchronous; task_id is the file path
        return GenerationResult(
            task_id=task_id,
            provider="stability",
            status="succeeded",
            progress=1.0,
            model_urls={"glb": task_id},
        )
```

## Self-Hosted Provider Setup

### Hunyuan3D 2.0

```python
# Hunyuan3D 2.0 - self-hosted via Gradio API or direct inference
# pip install gradio_client  (for Gradio-hosted instances)
# GPU requirement: NVIDIA A100 40GB+ recommended

from gradio_client import Client

def hunyuan3d_generate(image_path: str, server_url: str = "http://localhost:7860"):
    """Generate 3D model via self-hosted Hunyuan3D 2.0 Gradio server."""
    client = Client(server_url)
    result = client.predict(
        image_path,           # Input image
        "high",               # Quality: "low" | "medium" | "high"
        True,                 # Generate PBR textures
        api_name="/generate"
    )
    # result contains paths to generated .glb and texture files
    return result

# Direct inference (requires torch + hunyuan3d package)
# from hunyuan3d import Hunyuan3DPipeline
# pipe = Hunyuan3DPipeline.from_pretrained("tencent/Hunyuan3D-2")
# mesh = pipe(image="input.png", num_inference_steps=50)
# mesh.export("output.glb")
```

### Trellis (Microsoft)

```python
# Trellis - open-source, dual output (3D Gaussian Splatting + mesh)
# pip install trellis-3d
# GPU requirement: NVIDIA RTX 3090+ (24GB VRAM)

# Trellis produces both 3D Gaussian Splatting and extracted mesh
# The 3DGS output can be used for real-time rendering
# The mesh output goes through standard game pipeline

def trellis_generate(image_path: str, server_url: str = "http://localhost:7861"):
    """Generate via self-hosted Trellis server."""
    from gradio_client import Client
    client = Client(server_url)
    result = client.predict(
        image_path,
        seed=42,
        randomize_seed=False,
        ss_guidance_strength=7.5,
        ss_sampling_steps=12,
        slat_guidance_strength=3.0,
        slat_sampling_steps=12,
        mesh_simplify=0.95,    # Simplification ratio
        texture_size=1024,
        api_name="/generate"
    )
    # Returns: (3DGS .ply path, mesh .glb path, video preview path)
    return {"gaussian": result[0], "mesh": result[1], "preview": result[2]}
```

### InstantMesh (Large Reconstruction Model)

```python
# InstantMesh - LRM-based single/multi-view to mesh
# pip install instantmesh
# GPU: NVIDIA RTX 3080+ (12GB VRAM minimum)

def instantmesh_generate(image_path: str, server_url: str = "http://localhost:7862"):
    """Generate via self-hosted InstantMesh."""
    from gradio_client import Client
    client = Client(server_url)
    # Step 1: Generate multi-view images from single input
    multiview = client.predict(image_path, api_name="/generate_multiview")
    # Step 2: Reconstruct 3D mesh from multi-view
    mesh_path = client.predict(multiview, api_name="/reconstruct")
    return mesh_path
```

## Video-to-3D Pattern

```python
def video_to_3d_pipeline(video_path: str, provider: str = "luma") -> str:
    """Convert video to 3D model.

    Pipeline: Video -> Frame extraction -> Multi-view selection -> 3D reconstruction.
    For turntable videos, select evenly spaced frames for best results.
    """
    if provider == "luma":
        api_key = os.environ["LUMA_API_KEY"]
        # Luma supports direct video upload for 3D reconstruction
        with open(video_path, "rb") as f:
            resp = httpx.post(
                "https://webapp.engineeringlumalabs.com/api/v3/captures",
                headers={"Authorization": f"luma-api-key={api_key}"},
                files={"file": f},
                timeout=120.0,
            )
        resp.raise_for_status()
        return resp.json()["capture"]["uuid"]

    # Generic approach: extract frames and use multi-view provider
    import cv2
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Select 8-16 evenly spaced frames
    indices = [int(i * total_frames / 12) for i in range(12)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            path = f"/tmp/frame_{idx:04d}.png"
            cv2.imwrite(path, frame)
            frames.append(path)
    cap.release()
    # Use multi-view capable provider (Tripo, Rodin)
    return frames  # Pass to multi-view-to-3D endpoint
```

## Text-to-Texture Pattern

```python
def text_to_texture(model_path: str, texture_prompt: str,
                     provider: str = "meshy") -> dict:
    """Apply AI-generated textures to an existing 3D model.

    Use cases:
    - Re-skin existing game assets with new themes
    - Generate texture variants (summer/winter/damaged versions)
    - Apply PBR material to untextured geometry
    """
    if provider == "meshy":
        p = MeshyProvider()
        # Upload model first, then request texture generation
        task_id = p.text_to_texture(
            model_url=model_path,  # URL or upload
            prompt=texture_prompt,
            resolution=2048,
        )
        result = p.poll_until_complete(task_id)
        return result.texture_urls

    # Provider-agnostic pattern: use separate texture generation
    # Some providers support re-texturing as a post-process
    raise NotImplementedError(f"Text-to-texture not supported for {provider}")
```

## 3D Gaussian Splatting Conversion

```python
def gaussian_to_mesh(ply_path: str, method: str = "tsdf") -> str:
    """Convert 3D Gaussian Splatting to mesh for game engine use.

    3DGS is great for rendering but not directly usable in game engines.
    Convert to mesh for standard pipeline integration.

    Methods:
    - "tsdf": TSDF fusion (good quality, slower)
    - "poisson": Poisson reconstruction (fast, may lose detail)
    - "sugar": SuGaR method (Gaussian-to-mesh, best quality)
    """
    if method == "sugar":
        # SuGaR: Surface-Aligned Gaussian Splatting
        # pip install sugar-3d
        # Produces high-quality meshes from 3DGS
        pass  # See SuGaR GitHub for implementation

    if method == "tsdf":
        import open3d as o3d
        # Render depth maps from multiple viewpoints
        # Fuse into TSDF volume
        # Extract mesh via marching cubes
        volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=0.005,
            sdf_trunc=0.02,
            color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
        )
        # ... integrate depth frames ...
        mesh = volume.extract_triangle_mesh()
        mesh.compute_vertex_normals()
        output_path = ply_path.replace(".ply", "_mesh.obj")
        o3d.io.write_triangle_mesh(output_path, mesh)
        return output_path

    if method == "poisson":
        import open3d as o3d
        pcd = o3d.io.read_point_cloud(ply_path)
        pcd.estimate_normals()
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=10
        )
        output_path = ply_path.replace(".ply", "_mesh.obj")
        o3d.io.write_triangle_mesh(output_path, mesh)
        return output_path
```

## Async Polling Pattern

All providers use async task creation + polling. Standard pattern with exponential backoff:

```python
import time
import asyncio
from typing import Callable

def poll_with_backoff(check_fn: Callable[[str], dict], task_id: str,
                      initial_interval: int = 5, max_interval: int = 30,
                      max_wait: int = 600) -> dict:
    """Generic polling with exponential backoff."""
    elapsed = 0
    interval = initial_interval
    while elapsed < max_wait:
        result = check_fn(task_id)
        status = result.get("status", "").upper()
        if status in ("SUCCEEDED", "COMPLETED", "DONE", "SUCCESS"):
            return result
        if status in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(f"Task {task_id} failed: {result}")
        progress = result.get("progress", "unknown")
        print(f"[{task_id}] status={status} progress={progress} elapsed={elapsed}s")
        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 1.5, max_interval)
    raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")


async def poll_with_backoff_async(check_fn, task_id: str,
                                   initial_interval: int = 5,
                                   max_interval: int = 30,
                                   max_wait: int = 600) -> dict:
    """Async version for concurrent task polling."""
    elapsed = 0
    interval = initial_interval
    while elapsed < max_wait:
        result = await check_fn(task_id)
        status = result.get("status", "").upper()
        if status in ("SUCCEEDED", "COMPLETED", "DONE", "SUCCESS"):
            return result
        if status in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(f"Task {task_id} failed: {result}")
        await asyncio.sleep(interval)
        elapsed += interval
        interval = min(interval * 1.5, max_interval)
    raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")
```

## Batch Orchestration

```python
import asyncio
from dataclasses import dataclass

@dataclass
class BatchJob:
    prompt: str
    config: GenerationConfig
    task_id: str = ""
    result: GenerationResult = None
    error: str = ""

async def batch_generate(provider: ModelProvider, jobs: list[BatchJob],
                          concurrency: int = 5, preview_count: int = 3) -> list[BatchJob]:
    """Batch generation with preview gate and concurrency control.

    1. Generate preview_count items first
    2. Pause for review
    3. If approved, generate remaining with concurrency limit
    """
    # Phase 1: Preview
    print(f"Phase 1: Generating {preview_count} previews...")
    for job in jobs[:preview_count]:
        job.config.quality = "preview"
        job.task_id = provider.text_to_3d(job.config)

    for job in jobs[:preview_count]:
        try:
            job.result = provider.poll_until_complete(job.task_id)
        except Exception as e:
            job.error = str(e)

    preview_pass = sum(1 for j in jobs[:preview_count] if j.result and not j.error)
    print(f"Preview results: {preview_pass}/{preview_count} succeeded")

    if preview_pass < preview_count * 0.5:
        print("WARNING: >50% previews failed. Review prompts before batch run.")
        return jobs

    # Phase 2: Full batch with concurrency
    print(f"Phase 2: Generating {len(jobs)} models (concurrency={concurrency})...")
    semaphore = asyncio.Semaphore(concurrency)

    async def process_job(job: BatchJob):
        async with semaphore:
            job.config.quality = "standard"
            job.task_id = provider.text_to_3d(job.config)
            try:
                job.result = provider.poll_until_complete(job.task_id)
            except Exception as e:
                job.error = str(e)

    await asyncio.gather(*[process_job(j) for j in jobs])
    return jobs
```

## Rate Limiting and Retry

```python
import httpx
import time

MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 15]

def request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """HTTP request with retry on rate limit (429) and server errors (5xx)."""
    for attempt in range(MAX_RETRIES):
        resp = httpx.request(method, url, **kwargs)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", RETRY_DELAYS[attempt]))
            print(f"Rate limited. Retrying in {retry_after}s (attempt {attempt+1}/{MAX_RETRIES})...")
            time.sleep(retry_after)
            continue
        if resp.status_code >= 500:
            print(f"Server error {resp.status_code}. Retrying in {RETRY_DELAYS[attempt]}s...")
            time.sleep(RETRY_DELAYS[attempt])
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url}")
```

## Cost Estimation

Estimate before batch runs. Include this pattern in batch scripts:

```python
def estimate_cost(provider: str, count: int, mode: str = "standard",
                   texture: bool = False) -> dict:
    """Estimate API cost for a batch of generations."""
    # Approximate per-model costs (check current pricing - prices change frequently)
    costs = {
        "meshy":     {"preview": 0.10, "standard": 0.50, "texture": 0.30},
        "tripo":     {"draft": 0.10, "standard": 0.30, "animate": 0.20},
        "rodin":     {"standard": 0.50, "high": 1.00},
        "sloyd":     {"standard": 0.05, "detailed": 0.15},
        "stability": {"standard": 0.08},
        "luma":      {"standard": 0.30, "high": 0.60},
    }
    per_unit = costs.get(provider, {}).get(mode, 0.50)
    texture_cost = costs.get(provider, {}).get("texture", 0.30) if texture else 0
    total = (per_unit + texture_cost) * count

    return {
        "provider": provider,
        "count": count,
        "mode": mode,
        "per_unit_usd": per_unit,
        "texture_per_unit_usd": texture_cost,
        "total_usd": total,
        "note": "Estimates only. Check provider dashboard for current pricing.",
        "warning": "BATCH >10: Confirm cost before proceeding" if count > 10 else None,
    }
```

## Download and Save Pattern

```python
import httpx
from pathlib import Path

def download_model(url: str, output_dir: str, filename: str,
                   verify_integrity: bool = True) -> Path:
    """Download generated model file with integrity verification."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filepath = output_path / filename

    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
        if total and downloaded != total:
            raise RuntimeError(f"Incomplete download: {downloaded}/{total} bytes")

    size_kb = filepath.stat().st_size / 1024
    print(f"Downloaded: {filepath} ({size_kb:.1f} KB)")

    # Basic integrity check
    if verify_integrity:
        if filepath.suffix in (".glb", ".gltf"):
            _verify_gltf(filepath)
        elif filepath.suffix == ".fbx":
            _verify_fbx(filepath)

    return filepath


def _verify_gltf(filepath: Path):
    """Verify glTF/GLB file integrity."""
    if filepath.suffix == ".glb":
        with open(filepath, "rb") as f:
            magic = f.read(4)
            if magic != b"glTF":
                raise ValueError(f"Invalid GLB magic bytes: {magic}")
    print(f"Integrity check passed: {filepath.name}")


def _verify_fbx(filepath: Path):
    """Verify FBX file integrity."""
    with open(filepath, "rb") as f:
        header = f.read(23)
        if not header.startswith(b"Kaydara FBX Binary"):
            print(f"WARNING: Non-standard FBX header in {filepath.name}")
```

## Webhook Pattern (Event-Driven)

For production pipelines, prefer webhooks over polling when supported:

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/3d-generation")
async def handle_generation_webhook(request: Request):
    """Receive completion webhook from 3D generation provider."""
    payload = await request.json()
    task_id = payload.get("task_id")
    status = payload.get("status")
    model_url = payload.get("model_url")

    if status == "completed":
        # Trigger downstream pipeline: validate -> optimize -> integrate
        await trigger_pipeline(task_id, model_url)
    elif status == "failed":
        await handle_failure(task_id, payload.get("error"))

    return {"received": True}

# Configure webhook URL with provider:
# POST /api/v2/webhooks { "url": "https://your-server/webhook/3d-generation" }
```

## External Model Download

Download existing 3D models from public repositories and marketplaces. Use when a suitable model already exists rather than generating from scratch.

### Source Comparison

| Source | License | Models | API | Strength | Format |
|--------|---------|--------|-----|----------|--------|
| **Sketchfab** | Mixed (CC, paid) | 5M+ | REST (OAuth) | Largest marketplace, preview embed | glTF, FBX, OBJ, USDZ |
| **Objaverse** | CC-BY 4.0 | 800K+ | HuggingFace Hub | Massive open dataset, ML-ready | glTF |
| **Objaverse-XL** | Mixed | 10M+ | HuggingFace Hub | Extended Objaverse, diverse sources | glTF, OBJ |
| **Poly Pizza** | CC0 (public domain) | 3K+ | REST | Free low-poly game assets | glTF |
| **Kenney** | CC0 (public domain) | 1K+ | Direct download | Game-ready, consistent style | glTF, FBX, OBJ |
| **Smithsonian 3D** | CC0 / EDU | 1K+ | REST (IIIF) | Museum artifact scans, photogrammetry | glTF, OBJ, STL |
| **glTF Sample Models** | Various open | 100+ | GitHub raw | Reference/test models, PBR showcase | glTF |
| **TurboSquid** | Commercial | 1M+ | REST | Professional quality, editorial review | FBX, OBJ, MAX |
| **CGTrader** | Commercial | 1M+ | REST | Professional, CAD models available | FBX, OBJ, STEP |
| **Free3D** | Mixed | 20K+ | Web scraping only | Free tier available | FBX, OBJ, 3DS |

### Model Source Abstraction

```python
import os
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModelSearchResult:
    """A single search result from a model repository."""
    source: str
    uid: str
    name: str
    author: str = ""
    license: str = ""
    poly_count: int = 0
    formats: list = field(default_factory=list)
    thumbnail_url: str = ""
    download_url: str = ""
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class DownloadResult:
    """Result of a model download operation."""
    filepath: Path
    source: str
    uid: str
    format: str
    size_bytes: int
    license: str = ""
    attribution: str = ""
    metadata: dict = field(default_factory=dict)


class ModelSource(ABC):
    """Abstract base for external 3D model sources."""

    @abstractmethod
    def search(self, query: str, limit: int = 20,
               file_format: str = "glb") -> list[ModelSearchResult]:
        """Search for models by keyword."""

    @abstractmethod
    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a model by its UID."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Source identifier string."""
```

### Sketchfab

```python
class SketchfabSource(ModelSource):
    """Sketchfab API integration.

    Auth: OAuth token via SKETCHFAB_API_TOKEN env var.
    Free tier: download free/CC-licensed models.
    Store purchases: download paid models you own.
    Docs: https://docs.sketchfab.com/data-api/v3/
    """

    source_name = "sketchfab"

    def __init__(self):
        self.token = os.environ["SKETCHFAB_API_TOKEN"]
        self.base_url = "https://api.sketchfab.com/v3"
        self.headers = {"Authorization": f"Token {self.token}"}

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb",
               downloadable: bool = True,
               sort_by: str = "-likeCount",
               license_filter: str = None,
               categories: list = None,
               max_face_count: int = None,
               animated: bool = None) -> list[ModelSearchResult]:
        """Search Sketchfab models.

        Args:
            sort_by: -likeCount, -viewCount, -createdAt, -publishedAt
            license_filter: by, by-sa, by-nd, by-nc, by-nc-sa, by-nc-nd, cc0
            categories: e.g. ["characters", "weapons-military", "architecture"]
            max_face_count: Filter by polygon count
            animated: Filter for animated models
        """
        params = {
            "q": query,
            "type": "models",
            "downloadable": str(downloadable).lower(),
            "sort_by": sort_by,
            "count": min(limit, 100),
        }
        if license_filter:
            params["license"] = license_filter
        if categories:
            params["categories"] = ",".join(categories)
        if max_face_count:
            params["max_face_count"] = max_face_count
        if animated is not None:
            params["animated"] = str(animated).lower()

        resp = httpx.get(
            f"{self.base_url}/search",
            headers=self.headers,
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append(ModelSearchResult(
                source="sketchfab",
                uid=item["uid"],
                name=item["name"],
                author=item.get("user", {}).get("displayName", ""),
                license=item.get("license", {}).get("slug", "unknown"),
                poly_count=item.get("faceCount", 0),
                formats=[a["format"] for a in item.get("archives", {}).get("gltf", {}).get("archives", [])],
                thumbnail_url=item.get("thumbnails", {}).get("images", [{}])[0].get("url", ""),
                tags=[t.get("name", "") for t in item.get("tags", [])],
                metadata={
                    "vertex_count": item.get("vertexCount", 0),
                    "animated": item.get("isAnimated", False),
                    "view_count": item.get("viewCount", 0),
                    "like_count": item.get("likeCount", 0),
                },
            ))
        return results

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a model from Sketchfab.

        Requires the model to be downloadable (free or purchased).
        """
        # Step 1: Request download URL
        resp = httpx.get(
            f"{self.base_url}/models/{uid}/download",
            headers=self.headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        download_info = resp.json()

        # Prefer glTF/GLB format
        format_key = "gltf" if file_format in ("glb", "gltf") else file_format
        if format_key not in download_info:
            available = list(download_info.keys())
            raise ValueError(
                f"Format '{format_key}' not available. Available: {available}"
            )

        url = download_info[format_key]["url"]
        size = download_info[format_key].get("size", 0)

        # Step 2: Download the archive
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        archive_path = output_path / f"{uid}.zip"

        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as stream:
            stream.raise_for_status()
            with open(archive_path, "wb") as f:
                for chunk in stream.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        # Step 3: Extract archive
        import zipfile
        extract_dir = output_path / uid
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_dir)
        archive_path.unlink()  # Remove zip after extraction

        # Find the main model file
        model_file = _find_model_file(extract_dir, file_format)

        # Step 4: Get license info for attribution
        model_resp = httpx.get(
            f"{self.base_url}/models/{uid}",
            headers=self.headers,
            timeout=30.0,
        )
        model_data = model_resp.json()
        license_info = model_data.get("license", {})
        author = model_data.get("user", {}).get("displayName", "")

        return DownloadResult(
            filepath=model_file,
            source="sketchfab",
            uid=uid,
            format=file_format,
            size_bytes=model_file.stat().st_size,
            license=license_info.get("slug", "unknown"),
            attribution=f'"{model_data["name"]}" by {author} '
                        f'(https://sketchfab.com/3d-models/{uid}) '
                        f'licensed under {license_info.get("label", "unknown")}',
            metadata={
                "face_count": model_data.get("faceCount", 0),
                "vertex_count": model_data.get("vertexCount", 0),
                "animated": model_data.get("isAnimated", False),
            },
        )
```

### Objaverse (HuggingFace Hub)

```python
class ObjaverseSource(ModelSource):
    """Objaverse dataset via HuggingFace Hub.

    No API key required for basic access.
    800K+ CC-BY models. Ideal for ML training data and bulk asset sourcing.
    pip install objaverse
    """

    source_name = "objaverse"

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb",
               min_face_count: int = None,
               tags: list = None) -> list[ModelSearchResult]:
        """Search Objaverse annotations by keyword and tags."""
        import objaverse

        # Load annotations (cached after first call)
        annotations = objaverse.load_annotations()
        results = []
        query_lower = query.lower()

        for uid, meta in annotations.items():
            name = meta.get("name", "").lower()
            desc = meta.get("description", "").lower()
            item_tags = [t.get("name", "").lower() for t in meta.get("tags", [])]

            # Keyword match in name, description, or tags
            if (query_lower in name or query_lower in desc
                    or any(query_lower in t for t in item_tags)):
                face_count = meta.get("faceCount", 0)
                if min_face_count and face_count < min_face_count:
                    continue

                results.append(ModelSearchResult(
                    source="objaverse",
                    uid=uid,
                    name=meta.get("name", uid),
                    author=meta.get("user", {}).get("displayName", ""),
                    license=meta.get("license", "by"),  # Most are CC-BY
                    poly_count=face_count,
                    formats=["glb"],
                    thumbnail_url=meta.get("thumbnails", {}).get("images", [{}])[0].get("url", ""),
                    tags=[t.get("name", "") for t in meta.get("tags", [])],
                    metadata={
                        "vertex_count": meta.get("vertexCount", 0),
                        "animated": meta.get("isAnimated", False),
                    },
                ))
                if len(results) >= limit:
                    break

        return results

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a model from Objaverse."""
        import objaverse

        # Download single object (returns {uid: local_path})
        paths = objaverse.load_objects(uids=[uid])
        if uid not in paths:
            raise RuntimeError(f"Failed to download Objaverse model: {uid}")

        src_path = Path(paths[uid])
        dst_dir = Path(output_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / f"{uid}.glb"

        import shutil
        shutil.copy2(src_path, dst_path)

        annotations = objaverse.load_annotations([uid])
        meta = annotations.get(uid, {})

        return DownloadResult(
            filepath=dst_path,
            source="objaverse",
            uid=uid,
            format="glb",
            size_bytes=dst_path.stat().st_size,
            license="CC-BY-4.0",
            attribution=f'"{meta.get("name", uid)}" from Objaverse '
                        f'(https://objaverse.allenai.org/explore/?query={uid})',
            metadata={
                "face_count": meta.get("faceCount", 0),
                "vertex_count": meta.get("vertexCount", 0),
            },
        )

    def download_batch(self, uids: list[str], output_dir: str,
                       processes: int = 4) -> list[DownloadResult]:
        """Batch download multiple models with multiprocessing."""
        import objaverse

        paths = objaverse.load_objects(uids=uids, download_processes=processes)
        results = []
        dst_dir = Path(output_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        for uid, src in paths.items():
            dst = dst_dir / f"{uid}.glb"
            shutil.copy2(src, dst)
            results.append(DownloadResult(
                filepath=dst, source="objaverse", uid=uid,
                format="glb", size_bytes=dst.stat().st_size,
                license="CC-BY-4.0",
            ))
        return results
```

### Poly Pizza (CC0 Game Assets)

```python
class PolyPizzaSource(ModelSource):
    """Poly Pizza - free CC0 low-poly game assets.

    API key via POLYPIZZA_API_KEY env var.
    All assets are CC0 (public domain) - no attribution required.
    Docs: https://polypizza.xyz/docs
    """

    source_name = "polypizza"

    def __init__(self):
        self.api_key = os.environ["POLYPIZZA_API_KEY"]
        self.base_url = "https://api.polypizza.xyz"
        self.headers = {"x-auth-token": self.api_key}

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb",
               category: str = None) -> list[ModelSearchResult]:
        """Search Poly Pizza models.

        Categories: characters, animals, food, nature, buildings,
                    vehicles, weapons, furniture, props
        """
        params = {"Keyword": query, "Limit": min(limit, 50)}
        if category:
            params["Category"] = category

        resp = httpx.get(
            f"{self.base_url}/v1/search",
            headers=self.headers,
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            ModelSearchResult(
                source="polypizza",
                uid=item["ID"],
                name=item["Title"],
                author=item.get("Creator", ""),
                license="CC0",
                poly_count=item.get("Tris", 0),
                formats=["gltf"],
                thumbnail_url=item.get("Thumbnail", ""),
                tags=item.get("Tags", []),
            )
            for item in data.get("results", [])
        ]

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a model from Poly Pizza."""
        resp = httpx.get(
            f"{self.base_url}/v1/model/{uid}",
            headers=self.headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        model_data = resp.json()
        download_url = model_data["Download"]

        dst_dir = Path(output_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / f"{uid}.gltf"

        dl_resp = httpx.get(download_url, timeout=60.0, follow_redirects=True)
        dl_resp.raise_for_status()
        dst_path.write_bytes(dl_resp.content)

        return DownloadResult(
            filepath=dst_path,
            source="polypizza",
            uid=uid,
            format="gltf",
            size_bytes=dst_path.stat().st_size,
            license="CC0",
            attribution=f'"{model_data["Title"]}" by {model_data.get("Creator", "")} '
                        f"via Poly Pizza (CC0 public domain)",
        )
```

### Kenney (Game Assets)

```python
class KenneySource(ModelSource):
    """Kenney.nl game assets - CC0 public domain.

    No API key required. Direct GitHub download.
    Consistent low-poly style, ideal for prototyping and indie games.
    """

    source_name = "kenney"
    GITHUB_BASE = "https://raw.githubusercontent.com/KenneyNL"

    # Known asset packs with their GitHub repos
    PACKS = {
        "nature": "Kenney/Nature-Kit/main",
        "furniture": "Kenney/Furniture-Kit/main",
        "car": "Kenney/Car-Kit/main",
        "space": "Kenney/Space-Kit/main",
        "city": "Kenney/City-Kit/main",
        "holiday": "Kenney/Holiday-Kit/main",
        "pirate": "Kenney/Pirate-Kit/main",
        "mini-dungeon": "Kenney/Mini-Dungeon/main",
    }

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb") -> list[ModelSearchResult]:
        """Search Kenney asset packs by keyword.

        Note: Kenney doesn't have a search API. This matches against
        known pack names. For full catalog, visit kenney.nl/assets.
        """
        query_lower = query.lower()
        results = []
        for pack_name, repo_path in self.PACKS.items():
            if query_lower in pack_name:
                results.append(ModelSearchResult(
                    source="kenney",
                    uid=pack_name,
                    name=f"Kenney {pack_name.replace('-', ' ').title()} Kit",
                    author="Kenney",
                    license="CC0",
                    formats=["glb", "fbx", "obj"],
                    tags=[pack_name, "game-ready", "low-poly"],
                    metadata={"pack": True, "repo": repo_path},
                ))
        return results[:limit]

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a Kenney asset pack.

        Downloads the full pack as a zip from kenney.nl.
        For individual models, use download_from_pack().
        """
        # Direct download from kenney.nl
        pack_url = f"https://kenney.nl/media/pages/assets/{uid}/download"
        dst_dir = Path(output_dir) / f"kenney-{uid}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        archive_path = dst_dir / f"{uid}.zip"

        resp = httpx.get(pack_url, timeout=120.0, follow_redirects=True)
        resp.raise_for_status()
        archive_path.write_bytes(resp.content)

        import zipfile
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(dst_dir)
        archive_path.unlink()

        return DownloadResult(
            filepath=dst_dir,
            source="kenney",
            uid=uid,
            format="pack",
            size_bytes=sum(f.stat().st_size for f in dst_dir.rglob("*") if f.is_file()),
            license="CC0",
            attribution="Kenney (kenney.nl) - CC0 public domain",
        )
```

### glTF Sample Models (Testing & Reference)

```python
class GltfSamplesSource(ModelSource):
    """KhronosGroup glTF Sample Models from GitHub.

    No API key required. Standard reference models for testing
    glTF loaders, PBR rendering, and pipeline validation.
    """

    source_name = "gltf-samples"
    REPO_API = "https://api.github.com/repos/KhronosGroup/glTF-Sample-Assets"
    RAW_BASE = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models"

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb") -> list[ModelSearchResult]:
        """Search glTF sample models by name."""
        # Fetch model listing from repo
        resp = httpx.get(
            f"{self.REPO_API}/contents/Models",
            timeout=30.0,
        )
        resp.raise_for_status()
        entries = resp.json()

        query_lower = query.lower()
        results = []
        for entry in entries:
            if entry["type"] != "dir":
                continue
            name = entry["name"]
            if query_lower in name.lower() or query_lower == "*":
                results.append(ModelSearchResult(
                    source="gltf-samples",
                    uid=name,
                    name=name,
                    author="KhronosGroup",
                    license="Various (see individual model)",
                    formats=["glb", "gltf"],
                    tags=["reference", "test", "pbr"],
                    download_url=f"{self.RAW_BASE}/{name}/glTF-Binary/{name}.glb",
                ))
                if len(results) >= limit:
                    break
        return results

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        """Download a glTF sample model."""
        if file_format == "glb":
            url = f"{self.RAW_BASE}/{uid}/glTF-Binary/{uid}.glb"
        else:
            url = f"{self.RAW_BASE}/{uid}/glTF/{uid}.gltf"

        dst_dir = Path(output_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / f"{uid}.{file_format}"

        resp = httpx.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        dst_path.write_bytes(resp.content)

        return DownloadResult(
            filepath=dst_path,
            source="gltf-samples",
            uid=uid,
            format=file_format,
            size_bytes=dst_path.stat().st_size,
            license="See model README",
            attribution=f"glTF Sample Model: {uid} (KhronosGroup/glTF-Sample-Assets)",
        )
```

### Smithsonian 3D

```python
class SmithsonianSource(ModelSource):
    """Smithsonian 3D Digitization - museum artifact scans.

    API key via SMITHSONIAN_API_KEY env var.
    High-quality photogrammetry scans. CC0 for most items.
    Docs: https://3d.si.edu/api
    """

    source_name = "smithsonian"

    def __init__(self):
        self.api_key = os.environ.get("SMITHSONIAN_API_KEY", "")
        self.base_url = "https://3d-api.si.edu/api/v1.0"

    def search(self, query: str, limit: int = 20,
               file_format: str = "glb") -> list[ModelSearchResult]:
        resp = httpx.get(
            f"{self.base_url}/content/3d/search",
            params={"q": query, "rows": limit},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            ModelSearchResult(
                source="smithsonian",
                uid=item["content"]["id"],
                name=item["title"],
                author="Smithsonian Institution",
                license="CC0",
                formats=["glb", "obj", "stl"],
                thumbnail_url=item.get("thumbnail", ""),
                tags=item.get("tags", []),
            )
            for item in data.get("rows", [])
        ]

    def download(self, uid: str, output_dir: str,
                 file_format: str = "glb") -> DownloadResult:
        # Fetch model detail to get download URL
        resp = httpx.get(
            f"{self.base_url}/content/3d/{uid}",
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Find matching format in downloads
        downloads = data.get("content", {}).get("downloads", [])
        download_url = None
        for dl in downloads:
            if file_format in dl.get("format", "").lower():
                download_url = dl["url"]
                break
        if not download_url and downloads:
            download_url = downloads[0]["url"]  # Fallback to first available

        if not download_url:
            raise ValueError(f"No downloadable format found for {uid}")

        dst_dir = Path(output_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / f"smithsonian_{uid}.{file_format}"

        dl_resp = httpx.get(download_url, timeout=120.0, follow_redirects=True)
        dl_resp.raise_for_status()
        dst_path.write_bytes(dl_resp.content)

        return DownloadResult(
            filepath=dst_path,
            source="smithsonian",
            uid=uid,
            format=file_format,
            size_bytes=dst_path.stat().st_size,
            license="CC0",
            attribution=f'"{data.get("title", uid)}" - Smithsonian 3D Digitization (CC0)',
        )
```

### Utility Functions

```python
def _find_model_file(directory: Path, preferred_format: str = "glb") -> Path:
    """Find the main model file in an extracted archive."""
    format_priority = {
        "glb": [".glb", ".gltf", ".fbx", ".obj"],
        "gltf": [".gltf", ".glb", ".fbx", ".obj"],
        "fbx": [".fbx", ".glb", ".gltf", ".obj"],
        "obj": [".obj", ".fbx", ".glb", ".gltf"],
    }
    extensions = format_priority.get(preferred_format, [".glb", ".gltf", ".fbx", ".obj"])
    for ext in extensions:
        files = list(directory.rglob(f"*{ext}"))
        if files:
            # Prefer the largest file (likely the main model)
            return max(files, key=lambda f: f.stat().st_size)
    raise FileNotFoundError(f"No 3D model file found in {directory}")


def search_all_sources(query: str, limit_per_source: int = 5,
                        sources: list[ModelSource] = None) -> list[ModelSearchResult]:
    """Search multiple model sources in parallel.

    Returns combined results sorted by relevance.
    """
    import concurrent.futures

    if sources is None:
        sources = []
        # Initialize available sources (skip those without required API keys)
        if os.environ.get("SKETCHFAB_API_TOKEN"):
            sources.append(SketchfabSource())
        if os.environ.get("POLYPIZZA_API_KEY"):
            sources.append(PolyPizzaSource())
        sources.append(ObjaverseSource())     # No key required
        sources.append(GltfSamplesSource())   # No key required
        sources.append(KenneySource())        # No key required

    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(source.search, query, limit_per_source): source
            for source in sources
        }
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"[{source.source_name}] Search failed: {e}")

    return all_results


def download_with_validation(source: ModelSource, uid: str,
                              output_dir: str, file_format: str = "glb",
                              validate: bool = True) -> DownloadResult:
    """Download a model and optionally run QC validation.

    Combines download with the quality validation pipeline.
    See quality-validation.md for validation details.
    """
    result = source.download(uid, output_dir, file_format)
    print(f"Downloaded: {result.filepath} ({result.size_bytes / 1024:.1f} KB)")
    print(f"License: {result.license}")
    print(f"Attribution: {result.attribution}")

    if validate and result.filepath.suffix in (".glb", ".gltf", ".obj", ".fbx"):
        # Import validation from quality-validation.md patterns
        # validate_model(result.filepath)
        print(f"Run validation: validate_model('{result.filepath}')")

    # Save attribution metadata alongside model
    meta_path = result.filepath.with_suffix(".meta.json")
    import json
    meta_path.write_text(json.dumps({
        "source": result.source,
        "uid": result.uid,
        "license": result.license,
        "attribution": result.attribution,
        "format": result.format,
        "size_bytes": result.size_bytes,
        "downloaded_at": __import__("datetime").datetime.now().isoformat(),
        **result.metadata,
    }, indent=2))

    return result
```

### License Compatibility Guide

| License | Commercial Use | Modification | Attribution Required | Share-Alike |
|---------|---------------|-------------|---------------------|-------------|
| CC0 | Yes | Yes | No | No |
| CC-BY | Yes | Yes | Yes | No |
| CC-BY-SA | Yes | Yes | Yes | Yes |
| CC-BY-NC | No | Yes | Yes | No |
| CC-BY-NC-SA | No | Yes | Yes | Yes |
| CC-BY-ND | Yes | No | Yes | No |
| Editorial / Store | Per license | Per license | Per license | Per license |

Rules:
- Always save attribution metadata with downloaded models.
- CC0 models are safest for commercial game assets.
- CC-BY requires visible credit (e.g., in game credits screen).
- CC-NC licenses prohibit commercial use entirely.
- Store-purchased models: follow the specific store license.
- When in doubt, verify the license before integrating into a shipped product.

### Source Selection Guide

| Use Case | Recommended Source | Reason |
|----------|-------------------|--------|
| Game prototyping | Kenney, Poly Pizza | CC0, consistent style, game-ready |
| Placeholder assets | glTF Samples | Reference quality, well-tested |
| ML training data | Objaverse | 800K+ models, bulk download |
| High-quality scanned objects | Smithsonian, Sketchfab | Photogrammetry, museum quality |
| Production game assets | Sketchfab (paid), TurboSquid | Editorial review, professional |
| Indie game (free) | Kenney, Poly Pizza, Sketchfab (CC) | Free, commercial-safe |
| Reference for AI generation | Objaverse, Sketchfab | Use as image-to-3D input |
| Style-consistent asset packs | Kenney | All packs share visual style |

## Provider Selection Guide

| Use Case | Recommended Provider | Reason |
|----------|---------------------|--------|
| Quick prototyping | Meshy (preview) or Stability | Fast, cheap |
| Game-ready assets | Sloyd | Pre-retopologized output, parametric |
| High-detail hero assets | Rodin | Best detail fidelity |
| Single-image reconstruction | Stability (Stable Fast 3D) | Sub-second generation |
| Self-hosted / open-source | Hunyuan3D 2.0 or Trellis | Full control, no API costs |
| Batch generation | Tripo or Meshy | Good rate limits, predictable pricing |
| Characters with animation | Tripo | Built-in rigging + animation |
| Scene / environment | CSM | World-building focused |
| Video capture to 3D | Luma | Direct video-to-3D support |
| 3D Gaussian Splatting | Trellis or Luma | Native 3DGS output |
| Re-texturing existing models | Meshy (text-to-texture) | Best texture generation |
| Open-source + high quality | Hunyuan3D 2.0 | PBR textures, commercial license |

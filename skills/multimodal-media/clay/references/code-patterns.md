# Code Patterns Reference

Templates and conventions for 3D modeling code across Blender Python, Three.js (WebGL/WebGPU), Babylon.js, React Three Fiber, OpenSCAD, SDF, USD, and Gaussian Splatting viewers.

## Blender Python (bpy) - Blender 4.x

### Scene Setup

```python
import bpy
import math

def clear_scene():
    """Remove all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Clear orphan data blocks
    for block_type in (bpy.data.meshes, bpy.data.materials, bpy.data.textures,
                       bpy.data.images, bpy.data.node_groups):
        for block in block_type:
            if block.users == 0:
                block_type.remove(block)

def setup_scene(camera_distance: float = 5.0, engine: str = "CYCLES"):
    """Set up a clean scene with camera and light."""
    clear_scene()

    # Camera
    bpy.ops.object.camera_add(location=(camera_distance, -camera_distance, camera_distance))
    cam = bpy.context.object
    cam.rotation_euler = (math.radians(55), 0, math.radians(45))
    bpy.context.scene.camera = cam

    # Sun light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    light = bpy.context.object
    light.data.energy = 3.0

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = engine  # 'CYCLES' or 'BLENDER_EEVEE_NEXT' (Blender 4.x)
    if engine == 'CYCLES':
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.film_transparent = True  # For thumbnail renders

    # Color management
    scene.view_settings.view_transform = 'AgX'  # Blender 4.x default
```

### Mesh Creation

```python
import bpy
import bmesh

def create_mesh_from_data(name: str, vertices: list, faces: list) -> bpy.types.Object:
    """Create a mesh object from vertex and face data."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new(v) for v in vertices]
    bm.verts.ensure_lookup_table()
    for face_indices in faces:
        bm.faces.new([verts[i] for i in face_indices])
    bm.to_mesh(mesh)
    bm.free()

    mesh.update()
    mesh.validate()
    return obj

def import_model(filepath: str) -> bpy.types.Object:
    """Import 3D model (auto-detect format)."""
    ext = filepath.rsplit(".", 1)[-1].lower()
    importers = {
        "fbx": lambda: bpy.ops.import_scene.fbx(filepath=filepath),
        "glb": lambda: bpy.ops.import_scene.gltf(filepath=filepath),
        "gltf": lambda: bpy.ops.import_scene.gltf(filepath=filepath),
        "obj": lambda: bpy.ops.wm.obj_import(filepath=filepath),
        "stl": lambda: bpy.ops.wm.stl_import(filepath=filepath),
        "usd": lambda: bpy.ops.wm.usd_import(filepath=filepath),
        "usdc": lambda: bpy.ops.wm.usd_import(filepath=filepath),
        "usdz": lambda: bpy.ops.wm.usd_import(filepath=filepath),
        "ply": lambda: bpy.ops.wm.ply_import(filepath=filepath),
    }
    if ext not in importers:
        raise ValueError(f"Unsupported format: {ext}")
    before = set(bpy.data.objects.keys())
    importers[ext]()
    after = set(bpy.data.objects.keys())
    new_objs = after - before
    if new_objs:
        return bpy.data.objects[next(iter(new_objs))]
    return bpy.context.active_object
```

### Geometry Nodes (Blender 4.x)

```python
def create_scatter_geometry_nodes(target_obj: bpy.types.Object,
                                   instance_obj: bpy.types.Object,
                                   density: float = 10.0,
                                   scale_range: tuple = (0.8, 1.2)):
    """Create Geometry Nodes modifier for scattering instances on a surface.

    Useful for environment population: scatter rocks, grass, props on terrain.
    """
    mod = target_obj.modifiers.new("GeometryNodes", 'NODES')

    # Create node group
    group = bpy.data.node_groups.new("ScatterInstances", 'GeometryNodeTree')
    mod.node_group = group

    # Input/output interface (Blender 4.x API)
    group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = group.nodes
    links = group.links

    input_node = nodes.new('NodeGroupInput')
    output_node = nodes.new('NodeGroupOutput')

    # Distribute Points on Faces
    distribute = nodes.new('GeometryNodeDistributePointsOnFaces')
    distribute.distribute_method = 'POISSON'
    distribute.inputs['Density'].default_value = density

    # Instance on Points
    instance = nodes.new('GeometryNodeInstanceOnPoints')

    # Object Info (the instance)
    obj_info = nodes.new('GeometryNodeObjectInfo')
    obj_info.inputs['Object'].default_value = instance_obj
    obj_info.transform_space = 'RELATIVE'

    # Random Scale
    random_val = nodes.new('FunctionNodeRandomValue')
    random_val.data_type = 'FLOAT_VECTOR'
    random_val.inputs[0].default_value = [scale_range[0]] * 3
    random_val.inputs[1].default_value = [scale_range[1]] * 3

    # Link nodes
    links.new(input_node.outputs[0], distribute.inputs['Mesh'])
    links.new(distribute.outputs['Points'], instance.inputs['Points'])
    links.new(obj_info.outputs['Geometry'], instance.inputs['Instance'])
    links.new(random_val.outputs[1], instance.inputs['Scale'])
    links.new(distribute.outputs['Rotation'], instance.inputs['Rotation'])

    # Join original geometry with instances
    join = nodes.new('GeometryNodeJoinGeometry')
    links.new(input_node.outputs[0], join.inputs['Geometry'])
    links.new(instance.outputs['Instances'], join.inputs['Geometry'])
    links.new(join.outputs[0], output_node.inputs[0])
```

### Modifier Stack

```python
def add_subdivision(obj: bpy.types.Object, levels: int = 2, render_levels: int = 3):
    """Add subdivision surface modifier."""
    mod = obj.modifiers.new("Subdivision", 'SUBSURF')
    mod.levels = levels
    mod.render_levels = render_levels

def add_decimate(obj: bpy.types.Object, ratio: float = 0.5,
                  method: str = 'COLLAPSE') -> bpy.types.Modifier:
    """Add decimate modifier for poly reduction.

    Methods: 'COLLAPSE' (best quality), 'UNSUBDIV', 'PLANAR'.
    """
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = method
    if method == 'COLLAPSE':
        mod.ratio = ratio
    elif method == 'PLANAR':
        mod.angle_limit = 0.087  # ~5 degrees
    return mod

def add_weighted_normal(obj: bpy.types.Object):
    """Add Weighted Normal modifier for better shading on hard-surface models."""
    mod = obj.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL')
    mod.mode = 'FACE_AREA_AND_ANGLE'
    mod.keep_sharp = True

def apply_all_modifiers(obj: bpy.types.Object):
    """Apply all modifiers on an object."""
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
```

### PBR Material with Texture Maps

```python
def create_pbr_material(name: str, base_color: tuple = (0.8, 0.8, 0.8, 1.0),
                         metallic: float = 0.0, roughness: float = 0.5,
                         albedo_path: str = None, normal_path: str = None,
                         roughness_path: str = None, metallic_path: str = None,
                         ao_path: str = None) -> bpy.types.Material:
    """Create a PBR material with Principled BSDF and optional texture maps."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    # Base values
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness

    y_offset = 0
    def add_texture(image_path, target_input, color_space="sRGB"):
        nonlocal y_offset
        if not image_path:
            return
        img = bpy.data.images.load(image_path)
        img.colorspace_settings.name = color_space
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-400, y_offset)
        y_offset -= 300
        links.new(tex.outputs["Color"], bsdf.inputs[target_input])

    add_texture(albedo_path, "Base Color", "sRGB")
    add_texture(normal_path, "Normal", "Non-Color")
    add_texture(roughness_path, "Roughness", "Non-Color")
    add_texture(metallic_path, "Metallic", "Non-Color")

    # Normal map node
    if normal_path:
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.location = (-200, -300)
        # Reconnect through normal map node
        for link in list(links):
            if link.to_socket == bsdf.inputs.get("Normal"):
                tex_node = link.from_node
                links.remove(link)
                links.new(tex_node.outputs["Color"], normal_map.inputs["Color"])
                links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
                break

    return mat

def assign_material(obj: bpy.types.Object, material: bpy.types.Material):
    """Assign a material to an object."""
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)
```

### Multi-View Render for QC

```python
def render_turntable(obj_name: str, output_dir: str, num_views: int = 8,
                      resolution: int = 512):
    """Render turntable views for visual QC of generated models."""
    from pathlib import Path
    import math

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    obj = bpy.data.objects[obj_name]
    # Auto-frame camera
    bbox_center = sum((obj.matrix_world @ v.co for v in obj.data.vertices),
                       type(obj.data.vertices[0].co)()) / len(obj.data.vertices)

    cam = bpy.context.scene.camera
    distance = max(obj.dimensions) * 2.0

    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.image_settings.file_format = 'PNG'

    for i in range(num_views):
        angle = (2 * math.pi * i) / num_views
        cam.location = (
            bbox_center.x + distance * math.cos(angle),
            bbox_center.y + distance * math.sin(angle),
            bbox_center.z + distance * 0.5,
        )
        direction = bbox_center - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        scene.render.filepath = str(out / f"view_{i:02d}.png")
        bpy.ops.render.render(write_still=True)

    print(f"Rendered {num_views} views to {out}")
```

### Batch Export

```python
import bpy
from pathlib import Path

def batch_export_fbx(output_dir: str, apply_modifiers: bool = True):
    """Export each selected object as a separate FBX file."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    selected = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    for obj in selected:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        filepath = str(path / f"{obj.name}.fbx")
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            apply_unit_scale=True,
            use_mesh_modifiers=apply_modifiers,
            mesh_smooth_type='FACE',
            path_mode='COPY',
            embed_textures=True,
        )
        print(f"Exported: {filepath}")

def export_gltf(obj_name: str, output_path: str, draco: bool = True,
                webp_textures: bool = True, ktx2: bool = False):
    """Export as glTF with compression options."""
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object '{obj_name}' not found")
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        use_selection=True,
        export_format='GLB',
        export_draco_mesh_compression_enable=draco,
        export_draco_mesh_compression_level=6,
        export_image_format='WEBP' if webp_textures else 'AUTO',
        export_apply=True,
    )
    # Post-process: apply KTX2 + Basis Universal if requested
    if ktx2:
        print(f"NOTE: Run gltf-transform ktx2 {output_path} for KTX2 compression")

def export_usd(obj_name: str, output_path: str):
    """Export as USD/USDC for DCC interchange."""
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object '{obj_name}' not found")
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.usd_export(
        filepath=output_path,
        selected_objects_only=True,
        export_materials=True,
        generate_preview_surface=True,
    )
```

## Three.js (WebGL + WebGPU)

### WebGL Scene Setup

```javascript
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

function createScene(container) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf0f0f0);

  // Camera
  const camera = new THREE.PerspectiveCamera(
    45, container.clientWidth / container.clientHeight, 0.1, 1000
  );
  camera.position.set(5, 3, 5);

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));  // Cap at 2x
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  // Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;

  // Environment lighting (IBL)
  const pmremGenerator = new THREE.PMREMGenerator(renderer);
  scene.environment = pmremGenerator.fromScene(
    new THREE.Scene().add(new THREE.AmbientLight(0xffffff, 1))
  ).texture;

  // Directional light with shadows
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
  dirLight.position.set(5, 10, 7);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.setScalar(2048);
  dirLight.shadow.camera.near = 0.5;
  dirLight.shadow.camera.far = 50;
  scene.add(dirLight);

  // Ground plane
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 20),
    new THREE.MeshStandardMaterial({ color: 0xcccccc })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // Resize handler
  const onResize = () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  };
  window.addEventListener('resize', onResize);

  return { scene, camera, renderer, controls };
}
```

### WebGPU Scene Setup (Three.js r160+)

```javascript
import * as THREE from 'three/webgpu';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

async function createWebGPUScene(container) {
  // WebGPU renderer (async initialization)
  const renderer = new THREE.WebGPURenderer({ antialias: true });
  await renderer.init();
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf0f0f0);

  const camera = new THREE.PerspectiveCamera(
    45, container.clientWidth / container.clientHeight, 0.1, 1000
  );
  camera.position.set(5, 3, 5);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // WebGPU supports TSL (Three.js Shading Language) for custom materials
  // and node-based material system
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
  dirLight.position.set(5, 10, 7);
  dirLight.castShadow = true;
  scene.add(dirLight);

  return { scene, camera, renderer, controls };
}
```

### GLTFLoader with Full Compression Support

```javascript
function createOptimizedLoader(renderer) {
  const dracoLoader = new DRACOLoader();
  dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/');

  const ktx2Loader = new KTX2Loader();
  ktx2Loader.setTranscoderPath('https://www.gstatic.com/basis-universal/versioned/2024-05-01/');
  ktx2Loader.detectSupport(renderer);

  const loader = new GLTFLoader();
  loader.setDRACOLoader(dracoLoader);
  loader.setKTX2Loader(ktx2Loader);
  loader.setMeshoptDecoder(MeshoptDecoder);

  return loader;
}

async function loadModel(scene, url, options = {}) {
  const {
    position = [0, 0, 0],
    scale = 1.0,
    castShadow = true,
    receiveShadow = true,
    onProgress,
  } = options;

  const loader = createOptimizedLoader(scene.renderer);

  const gltf = await new Promise((resolve, reject) => {
    loader.load(url, resolve, onProgress, reject);
  });

  const model = gltf.scene;
  model.position.set(...position);
  model.scale.setScalar(scale);
  model.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = castShadow;
      child.receiveShadow = receiveShadow;
      // Enable frustum culling
      child.frustumCulled = true;
    }
  });
  scene.add(model);

  // Return animations if present
  const mixer = gltf.animations.length > 0
    ? new THREE.AnimationMixer(model)
    : null;
  if (mixer) {
    gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
  }

  return { model, mixer, animations: gltf.animations };
}
```

### LOD System (Three.js)

```javascript
function createLODGroup(lodMeshes, distances) {
  /**
   * Create LOD group from array of meshes and switch distances.
   * @param {THREE.Mesh[]} lodMeshes - Array of meshes [lod0, lod1, lod2, ...]
   * @param {number[]} distances - Switch distances [0, 10, 25, 50]
   */
  const lod = new THREE.LOD();
  lodMeshes.forEach((mesh, i) => {
    lod.addLevel(mesh, distances[i] || 0);
  });
  lod.autoUpdate = true;
  return lod;
}

// Usage with AI-generated LOD chain
async function loadLODChain(scene, basePath, lodLevels = 4) {
  const loader = createOptimizedLoader(scene.renderer);
  const distances = [0, 15, 40, 80];
  const meshes = [];

  for (let i = 0; i < lodLevels; i++) {
    const gltf = await new Promise((resolve, reject) => {
      loader.load(`${basePath}_lod${i}.glb`, resolve, undefined, reject);
    });
    meshes.push(gltf.scene);
  }

  const lod = createLODGroup(meshes, distances);
  scene.add(lod);
  return lod;
}
```

### Instanced Rendering for Batch Assets

```javascript
function createInstancedMesh(geometry, material, positions, options = {}) {
  /**
   * Efficient rendering of many identical objects (trees, rocks, props).
   * GPU instancing: 1 draw call for thousands of objects.
   */
  const { rotations, scales } = options;
  const count = positions.length;
  const mesh = new THREE.InstancedMesh(geometry, material, count);

  const dummy = new THREE.Object3D();
  positions.forEach((pos, i) => {
    dummy.position.set(pos[0], pos[1], pos[2]);
    if (rotations?.[i]) {
      dummy.rotation.set(rotations[i][0], rotations[i][1], rotations[i][2]);
    }
    if (scales?.[i]) {
      dummy.scale.setScalar(scales[i]);
    } else {
      dummy.scale.setScalar(1);
    }
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  });

  mesh.instanceMatrix.needsUpdate = true;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}
```

### PBR Material

```javascript
function createPBRMaterial(options = {}) {
  const {
    color = 0x888888,
    metalness = 0.0,
    roughness = 0.5,
    map = null,
    normalMap = null,
    roughnessMap = null,
    metalnessMap = null,
    aoMap = null,
    emissiveMap = null,
    emissive = 0x000000,
    emissiveIntensity = 0,
  } = options;

  return new THREE.MeshStandardMaterial({
    color,
    metalness,
    roughness,
    map,
    normalMap,
    roughnessMap,
    metalnessMap,
    aoMap,
    emissiveMap,
    emissive,
    emissiveIntensity,
    envMapIntensity: 1.0,
  });
}
```

## React Three Fiber

```jsx
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls, Environment, useGLTF, Detailed } from '@react-three/drei';
import { Suspense, useRef } from 'react';

function Model({ url, position = [0, 0, 0], scale = 1 }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} position={position} scale={scale} />;
}

function LODModel({ basePath, distances = [0, 15, 40] }) {
  /** LOD component using @react-three/drei Detailed */
  const lod0 = useGLTF(`${basePath}_lod0.glb`);
  const lod1 = useGLTF(`${basePath}_lod1.glb`);
  const lod2 = useGLTF(`${basePath}_lod2.glb`);

  return (
    <Detailed distances={distances}>
      <primitive object={lod0.scene.clone()} />
      <primitive object={lod1.scene.clone()} />
      <primitive object={lod2.scene.clone()} />
    </Detailed>
  );
}

function Scene() {
  return (
    <Canvas shadows camera={{ position: [5, 3, 5], fov: 45 }}>
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 10, 7]} intensity={1.5} castShadow />
      <Environment preset="city" />
      <Suspense fallback={null}>
        <Model url="/models/asset.glb" />
      </Suspense>
      <OrbitControls enableDamping />
    </Canvas>
  );
}
```

## Babylon.js

### Engine Setup

```javascript
const canvas = document.getElementById('renderCanvas');
const engine = new BABYLON.Engine(canvas, true, {
  preserveDrawingBuffer: true,
  stencil: true,
});

const createScene = () => {
  const scene = new BABYLON.Scene(engine);
  scene.clearColor = new BABYLON.Color4(0.9, 0.9, 0.9, 1);

  // Camera
  const camera = new BABYLON.ArcRotateCamera(
    'camera', Math.PI / 4, Math.PI / 3, 10,
    BABYLON.Vector3.Zero(), scene
  );
  camera.attachControl(canvas, true);
  camera.lowerRadiusLimit = 2;
  camera.upperRadiusLimit = 50;

  // Environment lighting
  const hdrTexture = BABYLON.CubeTexture.CreateFromPrefilteredData(
    '/textures/environment.env', scene
  );
  scene.environmentTexture = hdrTexture;

  // Directional light with shadows
  const dirLight = new BABYLON.DirectionalLight(
    'dirLight', new BABYLON.Vector3(-1, -2, -1), scene
  );
  dirLight.intensity = 0.8;

  const shadowGen = new BABYLON.ShadowGenerator(2048, dirLight);
  shadowGen.useBlurExponentialShadowMap = true;
  shadowGen.blurKernel = 32;

  return { scene, camera, shadowGen };
};
```

### PBR Material (Babylon.js)

```javascript
function createPBRMaterial(scene, name, options = {}) {
  const {
    albedoColor = new BABYLON.Color3(0.5, 0.5, 0.5),
    metallic = 0.0,
    roughness = 0.5,
    albedoTexture = null,
    bumpTexture = null,
    metallicTexture = null,
  } = options;

  const mat = new BABYLON.PBRMaterial(name, scene);
  mat.albedoColor = albedoColor;
  mat.metallic = metallic;
  mat.roughness = roughness;

  if (albedoTexture) mat.albedoTexture = new BABYLON.Texture(albedoTexture, scene);
  if (bumpTexture) mat.bumpTexture = new BABYLON.Texture(bumpTexture, scene);
  if (metallicTexture) mat.metallicTexture = new BABYLON.Texture(metallicTexture, scene);

  mat.usePhysicalLightAttenuation = true;
  return mat;
}
```

### glTF Loading with LOD (Babylon.js)

```javascript
async function loadWithLOD(scene, basePath, shadowGen) {
  const distances = [0, 20, 50, 100];
  const meshes = [];

  for (let i = 0; i < 4; i++) {
    const result = await BABYLON.SceneLoader.ImportMeshAsync(
      '', basePath, `asset_lod${i}.glb`, scene
    );
    const root = result.meshes[0];
    root.setEnabled(i === 0);  // Only LOD0 visible initially
    result.meshes.forEach(m => {
      if (m.material) shadowGen.addShadowCaster(m);
    });
    meshes.push({ root, distance: distances[i] });
  }

  // LOD switching in render loop
  scene.onBeforeRenderObservable.add(() => {
    const camPos = scene.activeCamera.position;
    meshes.forEach((lod, i) => {
      const dist = BABYLON.Vector3.Distance(camPos, lod.root.position);
      const nextDist = meshes[i + 1]?.distance ?? Infinity;
      lod.root.setEnabled(dist >= lod.distance && dist < nextDist);
    });
  });
}
```

## OpenSCAD

OpenSCAD is the most LLM-compatible 3D modeling language due to its declarative, text-based nature.

### Parametric Primitives

```openscad
// Parametric box with rounded edges
module rounded_box(size, radius=2) {
    minkowski() {
        cube([size[0]-2*radius, size[1]-2*radius, size[2]-2*radius], center=true);
        sphere(r=radius, $fn=20);
    }
}

// Parametric cylinder with chamfer
module chamfered_cylinder(h, r, chamfer=1) {
    union() {
        cylinder(h=h-chamfer, r=r, $fn=32);
        translate([0, 0, h-chamfer])
            cylinder(h=chamfer, r1=r, r2=r-chamfer, $fn=32);
    }
}

// Thread (helical) for mechanical parts
module thread(h, r, pitch=2, tooth_depth=0.5) {
    linear_extrude(height=h, twist=360*h/pitch, $fn=32)
        translate([r-tooth_depth, 0])
            circle(r=tooth_depth, $fn=6);
}
```

### Boolean Operations

```openscad
// CSG operations for complex shapes
module game_prop_crate(size=20, wall=2) {
    difference() {
        cube(size, center=true);
        cube(size - 2*wall, center=true);
        for (angle = [45, -45]) {
            rotate([0, 0, angle])
                cube([size*1.5, wall/2, size+1], center=true);
        }
    }
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x*(size/2 - wall), y*(size/2 - wall), 0])
            cube([wall*2, wall*2, size], center=true);
    }
}

game_prop_crate(size=30, wall=3);
```

### Modular Game Asset Library

```openscad
// Reusable module library for game props
module barrel(h=40, r=15, stave_count=12) {
    difference() {
        // Main body with slight bulge
        scale([1, 1, 1])
            resize([r*2, r*2, h])
                sphere(r=r, $fn=stave_count);
        // Hollow interior
        translate([0, 0, 2])
            resize([r*1.6, r*1.6, h])
                sphere(r=r, $fn=stave_count);
    }
    // Metal bands
    for (z = [h*0.2, h*0.5, h*0.8]) {
        translate([0, 0, z - h/2])
            difference() {
                cylinder(h=2, r=r+0.5, $fn=32);
                cylinder(h=2, r=r-0.5, $fn=32);
            }
    }
}

// Export command: openscad -o barrel.stl -D '$fn=48' barrel.scad
```

### STL Export with Quality Settings

```openscad
// Design for STL export
// Low poly:  openscad -o output.stl -D '$fn=16' model.scad
// Mid poly:  openscad -o output.stl -D '$fn=48' model.scad
// High poly: openscad -o output.stl -D '$fn=96' model.scad

$fn = 48;  // Default resolution

module final_model() {
    rounded_box([40, 20, 10], radius=2);
}

final_model();
```

## SDF (Signed Distance Functions)

### SDF Primitives

```python
import numpy as np

def sdf_sphere(p: np.ndarray, center: np.ndarray, radius: float) -> np.ndarray:
    return np.linalg.norm(p - center, axis=-1) - radius

def sdf_box(p: np.ndarray, center: np.ndarray, half_extents: np.ndarray) -> np.ndarray:
    q = np.abs(p - center) - half_extents
    return (np.linalg.norm(np.maximum(q, 0), axis=-1)
            + np.minimum(np.max(q, axis=-1), 0))

def sdf_capsule(p: np.ndarray, a: np.ndarray, b: np.ndarray, radius: float) -> np.ndarray:
    """Capsule SDF (line segment with radius)."""
    pa = p - a
    ba = b - a
    h = np.clip(np.sum(pa * ba, axis=-1) / np.sum(ba * ba), 0, 1)
    return np.linalg.norm(pa - ba * h[..., None], axis=-1) - radius

def sdf_torus(p: np.ndarray, center: np.ndarray,
              major_r: float, minor_r: float) -> np.ndarray:
    """Torus SDF."""
    q = p - center
    q_xz = np.sqrt(q[..., 0]**2 + q[..., 2]**2) - major_r
    return np.sqrt(q_xz**2 + q[..., 1]**2) - minor_r
```

### CSG Operations

```python
def sdf_union(d1, d2):
    return np.minimum(d1, d2)

def sdf_intersection(d1, d2):
    return np.maximum(d1, d2)

def sdf_difference(d1, d2):
    return np.maximum(d1, -d2)

def sdf_smooth_union(d1, d2, k=0.1):
    """Smooth union for organic blending."""
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0, 1)
    return d2 * (1 - h) + d1 * h - k * h * (1 - h)

def sdf_smooth_subtraction(d1, d2, k=0.1):
    """Smooth subtraction."""
    h = np.clip(0.5 - 0.5 * (d2 + d1) / k, 0, 1)
    return d1 * (1 - h) + (-d2) * h + k * h * (1 - h)

def sdf_round(sdf_val, radius):
    """Round edges of any SDF."""
    return sdf_val - radius

def sdf_onion(sdf_val, thickness):
    """Hollow shell from any SDF."""
    return np.abs(sdf_val) - thickness
```

### Marching Cubes Extraction

```python
from skimage.measure import marching_cubes

def extract_mesh_from_sdf(sdf_fn, bounds, resolution=128):
    """Extract triangle mesh from SDF using marching cubes."""
    x = np.linspace(bounds[0][0], bounds[1][0], resolution)
    y = np.linspace(bounds[0][1], bounds[1][1], resolution)
    z = np.linspace(bounds[0][2], bounds[1][2], resolution)
    grid = np.stack(np.meshgrid(x, y, z, indexing='ij'), axis=-1)

    values = sdf_fn(grid)

    verts, faces, normals, _ = marching_cubes(
        values, level=0.0,
        spacing=(x[1]-x[0], y[1]-y[0], z[1]-z[0])
    )
    verts += np.array(bounds[0])
    return verts, faces, normals
```

## USD (Universal Scene Description)

```python
# pip install usd-core
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

def create_usd_scene(output_path: str):
    """Create a USD scene with mesh and PBR material."""
    stage = Usd.Stage.CreateNew(output_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    # Create mesh
    mesh = UsdGeom.Mesh.Define(stage, "/World/Mesh")
    mesh.CreatePointsAttr([(0,0,0), (1,0,0), (1,1,0), (0,1,0)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateNormalsAttr([(0,0,1)] * 4)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)

    # PBR material (MaterialX compatible)
    material = UsdShade.Material.Define(stage, "/World/Materials/PBR")
    shader = UsdShade.Shader.Define(stage, "/World/Materials/PBR/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.8, 0.6, 0.4))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    mesh.GetPrim().ApplyAPI(UsdShade.MaterialBindingAPI)
    UsdShade.MaterialBindingAPI(mesh).Bind(material)

    stage.Save()
    print(f"USD scene saved: {output_path}")
```

## 3D Gaussian Splatting Viewer

```javascript
// Three.js-based 3DGS viewer using @mkkellogg/gaussian-splats-3d
// npm install @mkkellogg/gaussian-splats-3d

import * as GaussianSplats3D from '@mkkellogg/gaussian-splats-3d';

async function createSplatViewer(container, splatUrl) {
  const viewer = new GaussianSplats3D.Viewer({
    cameraUp: [0, 1, 0],
    initialCameraPosition: [2, 2, 2],
    initialCameraLookAt: [0, 0, 0],
    rootElement: container,
    sharedMemoryForWorkers: false,
  });

  await viewer.addSplatScene(splatUrl, {
    splatAlphaRemovalThreshold: 5,  // Remove low-opacity splats
    showLoadingUI: true,
    progressiveLoad: true,
  });

  viewer.start();
  return viewer;
}
```

## Common Conventions

### Asset Naming

```
{project}_{category}_{name}_{variant}_{lod}.{ext}

Examples:
  rpg_prop_crate_wood_lod0.glb
  rpg_prop_crate_wood_lod1.glb
  rpg_char_knight_base_lod0.glb
  rpg_env_tree_oak_lod2.glb
  rpg_prop_crate_wood_albedo_2k.png
  rpg_prop_crate_wood_normal_2k.png
```

### Directory Structure

```
assets/
  models/
    characters/
    props/
    environment/
    vehicles/
  textures/
    characters/
    props/
    shared/           # Atlases, tileable textures
  materials/
  animations/
  splats/             # 3D Gaussian Splatting files
metadata/
  {asset_name}.json
pipeline/
  scripts/            # Blender/processing scripts
  configs/            # Pipeline configuration
```

### Metadata JSON

```json
{
  "name": "rpg_prop_crate_wood",
  "version": "1.2.0",
  "provider": "meshy",
  "provider_model": "meshy-4",
  "task_id": "task_abc123",
  "created": "2026-01-15T10:30:00Z",
  "prompt": "Medieval wooden crate with iron reinforcements",
  "quality_tier": "game-ready",
  "target_engine": "unity",
  "pipeline_version": "2.0",
  "lod_levels": [
    {"level": 0, "tris": 2400, "file": "crate_wood_lod0.glb"},
    {"level": 1, "tris": 800, "file": "crate_wood_lod1.glb"},
    {"level": 2, "tris": 200, "file": "crate_wood_lod2.glb"}
  ],
  "textures": {
    "albedo": {"file": "crate_wood_albedo.ktx2", "resolution": 1024},
    "normal": {"file": "crate_wood_normal.ktx2", "resolution": 1024},
    "orm": {"file": "crate_wood_orm.ktx2", "resolution": 1024, "note": "R=AO, G=Roughness, B=Metallic"}
  },
  "compression": {
    "mesh": "draco",
    "texture": "ktx2_basis_uastc"
  },
  "validation": {
    "manifold": true,
    "watertight": true,
    "max_tris": 2400,
    "uv_coverage": 0.85,
    "texel_density_variance": 0.12,
    "clip_score": 0.87,
    "game_readiness_score": 0.95
  }
}
```

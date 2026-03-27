# AI-Powered 3D Room Design System
## Proper Implementation Plan — Full Computer Vision Stack

> **What changed from the previous plan:** The old plan relied on Claude Vision to
> guess room geometry. This plan uses a real computer vision pipeline — COLMAP for
> 3D reconstruction, Depth Anything for dense depth, GroundingDINO + SAM for object
> detection and segmentation, and Open3D for geometry cleanup. Claude is repositioned
> as the semantic brain and design agent only, not as a spatial measurement tool.
> The result is a system that can actually measure rooms, not just guess at them.

---

## Table of Contents

1.  [Honest Stack Comparison — Old vs New](#1-honest-stack-comparison--old-vs-new)
2.  [What This System Actually Does](#2-what-this-system-actually-does)
3.  [Full Architecture](#3-full-architecture)
4.  [The SceneScript — Central Data Contract](#4-the-scenescript--central-data-contract)
5.  [Complete Tech Stack](#5-complete-tech-stack)
6.  [Infrastructure Requirements](#6-infrastructure-requirements)
7.  [Environment Setup](#7-environment-setup)
8.  [Project Folder Structure](#8-project-folder-structure)
9.  [Pipeline — Step by Step](#9-pipeline--step-by-step)
    - Step 1: Video Upload
    - Step 2: Frame Extraction
    - Step 3: COLMAP — Camera Poses + Sparse 3D Reconstruction
    - Step 4: Depth Anything — Dense Depth Maps
    - Step 5: GroundingDINO + SAM — Object Detection and Segmentation
    - Step 6: Open3D — Point Cloud Fusion and Geometry Cleanup
    - Step 7: SceneScript Generation — Fusing All Data
    - Step 8: Claude — Semantic Labelling and Design Agent
    - Step 9: Three.js — Interactive 3D Render
    - Step 10: Hover-to-Shop — Product Discovery
10. [Complete API Contract](#10-complete-api-contract)
11. [Memory and State Management](#11-memory-and-state-management)
12. [Object Selection and Replacement Flow](#12-object-selection-and-replacement-flow)
13. [Known Issues and Exact Solutions](#13-known-issues-and-exact-solutions)
14. [Build Phases — Realistic Timeline](#14-build-phases--realistic-timeline)
15. [Day-by-Day Build Order (Hackathon Mode)](#15-day-by-day-build-order-hackathon-mode)
16. [What to Skip and When to Add It](#16-what-to-skip-and-when-to-add-it)
17. [Demo Fallback SceneScript](#17-demo-fallback-scenescript)
18. [Post-Hackathon Roadmap](#18-post-hackathon-roadmap)
19. [Final Summary](#19-final-summary)

---

## 1. Honest Stack Comparison — Old vs New

| Concern | Old Plan (Claude Vision) | New Plan (Proper CV Stack) |
|---|---|---|
| Room dimensions | User guesses, Claude guesses | COLMAP measures from camera poses |
| Object positions | Claude estimates fractions | Point cloud → plane fitting → real coords |
| Object sizes | Lookup table of standard sizes | SAM segmentation mask → real bounding box |
| Depth | None | Depth Anything dense per-pixel depth |
| Object detection | Claude Vision (~75-85% accuracy) | GroundingDINO (open-vocab, ~90%+ accuracy) |
| Object segmentation | None | SAM (pixel-perfect masks) |
| Geometry cleanup | None | Open3D plane fitting, outlier removal |
| Semantic understanding | Claude Vision | Claude text API (labels + design agent) |
| Scale accuracy | Approximate | Metric — COLMAP recovers real-world scale |
| GPU required | No | Yes — Depth Anything + SAM need GPU |

**The honest truth about the new stack:**
The new stack produces genuinely accurate room geometry. The trade-off is it requires
a GPU backend (Google Colab, RunPod, or a machine with an Nvidia GPU) and takes
30–120 seconds per room scan instead of 5–10 seconds. For a hackathon, you run the
heavy pipeline on Colab. For production, you deploy it on a GPU server.

**For the hackathon specifically:**
Run COLMAP + Depth Anything + SAM on Google Colab. Expose the Colab notebook as an
ngrok tunnel. The Next.js frontend calls your FastAPI backend which proxies to Colab
for the heavy compute. After the hackathon, move it to a proper GPU instance.

---

## 2. What This System Actually Does

**One sentence:** A tool that reconstructs a real room from a phone video with
genuine metric accuracy, lets users redesign it using natural language, and lets them
buy real furniture directly from the 3D scene.

**The pipeline in plain English:**
1. User films their room for 30 seconds
2. COLMAP figures out where the camera was at every frame and builds a sparse 3D map
3. Depth Anything fills in dense depth for every pixel in every frame
4. GroundingDINO detects every piece of furniture with open-vocabulary text prompts
5. SAM segments the exact pixel boundaries of each detected object
6. Open3D fuses all depth maps into one clean point cloud and fits floor/wall planes
7. All data is fused into a SceneScript with real metric positions and sizes
8. Claude labels objects semantically and powers the design agent chat
9. Three.js renders the room interactively in the browser
10. Hovering over any object reveals a real product to buy

---

## 3. Full Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER'S BROWSER                              │
│  ┌──────────────┐  ┌─────────────────────────┐  ┌───────────────┐  │
│  │  Video       │  │   Three.js 3D Scene     │  │  Chat Panel   │  │
│  │  Upload UI   │  │   + Raycasting          │  │  + Shop Panel │  │
│  └──────┬───────┘  └──────────┬──────────────┘  └───────┬───────┘  │
└─────────┼────────────────────┼──────────────────────────┼──────────┘
          │                    │ SceneScript               │
          ▼                    ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (CPU)                          │
│  /api/upload   /api/scene   /api/agent   /api/shop   /api/undo      │
│                         Session Store                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ heavy compute jobs
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GPU WORKER (Colab / RunPod)                      │
│                                                                     │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │   COLMAP    │  │  Depth Anything  │  │  GroundingDINO      │   │
│  │  (SfM/MVS)  │  │  (dense depth)   │  │  + SAM              │   │
│  └──────┬──────┘  └────────┬─────────┘  └──────────┬──────────┘   │
│         │                  │                        │              │
│         └──────────────────┼────────────────────────┘              │
│                            ▼                                        │
│                    ┌──────────────┐                                 │
│                    │   Open3D     │                                 │
│                    │  fusion +    │                                 │
│                    │  geometry    │                                 │
│                    └──────┬───────┘                                 │
└───────────────────────────┼─────────────────────────────────────────┘
                            │ structured geometry data
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CLAUDE API (semantic layer)                      │
│   Vision disabled — text only                                       │
│   Input: geometry data + object masks + labels                      │
│   Output: semantic labels, design actions, natural language         │
└─────────────────────────────────────────────────────────────────────┘
```

**Key principle:** Claude never sees raw images or tries to measure anything.
Claude only receives structured geometry data and object labels, and returns
semantic understanding and design actions. All measurement is done by real CV tools.

---

## 4. The SceneScript — Central Data Contract

The SceneScript is the JSON document that all components read from and write to.
It is produced by the geometry fusion pipeline and consumed by Three.js and Claude.

### 4.1 Full Schema

```json
{
  "version": 1,
  "session_id": "uuid-here",
  "source": "colmap_pipeline",
  "room": {
    "width": 4.52,
    "depth": 5.18,
    "height": 2.76,
    "floor_plane": { "normal": [0, 1, 0], "offset": 0.0 },
    "wall_planes": [
      { "id": "wall_north", "normal": [0, 0, 1],  "offset": 0.0  },
      { "id": "wall_south", "normal": [0, 0, -1], "offset": 5.18 },
      { "id": "wall_east",  "normal": [-1, 0, 0], "offset": 4.52 },
      { "id": "wall_west",  "normal": [1, 0, 0],  "offset": 0.0  }
    ]
  },
  "walls": [
    { "id": "wall_north", "x1": 0,    "z1": 0,    "x2": 4.52, "z2": 0    },
    { "id": "wall_south", "x1": 0,    "z1": 5.18, "x2": 4.52, "z2": 5.18 },
    { "id": "wall_east",  "x1": 4.52, "z1": 0,    "x2": 4.52, "z2": 5.18 },
    { "id": "wall_west",  "x1": 0,    "z1": 0,    "x2": 0,    "z2": 5.18 }
  ],
  "windows": [
    {
      "id": "win_001",
      "wall": "wall_north",
      "x": 1.4,
      "width": 1.2,
      "height": 1.1,
      "sill_height": 0.9,
      "detected_by": "grounding_dino"
    }
  ],
  "doors": [
    {
      "id": "door_001",
      "wall": "wall_west",
      "x": 0.5,
      "width": 0.9,
      "height": 2.1,
      "detected_by": "grounding_dino"
    }
  ],
  "objects": [
    {
      "id": "obj_001",
      "type": "sofa",
      "label_source": "grounding_dino",
      "label_confirmed": true,
      "position": { "x": 1.18, "y": 0.0, "z": 0.52 },
      "size": { "w": 2.21, "h": 0.84, "d": 0.91 },
      "rotation_y": 0.0,
      "color": "grey",
      "style": null,
      "point_cloud_cluster_id": 3,
      "sam_mask_id": "mask_007",
      "detection_confidence": 0.91,
      "product_url": null,
      "product_name": null
    }
  ],
  "point_cloud": {
    "path": "/tmp/session_id/pointcloud.ply",
    "num_points": 184203,
    "has_color": true
  },
  "metadata": {
    "room_type": "living_room",
    "style": null,
    "pipeline_version": "colmap_v1",
    "processing_time_seconds": 87,
    "colmap_num_cameras": 42,
    "colmap_num_points": 12400,
    "created_at": "2025-01-01T00:00:00Z",
    "last_edited": "2025-01-01T00:00:00Z"
  }
}
```

### 4.2 Coordinate System

```
         North wall (z = 0)
         ____________________
        |                    |
West    |    Y (up)          |   East
wall    |    |               |   wall
(x=0)   |    |_____ X        |   (x=W)
        |   /                |
        |  Z (into room)     |
        |____________________|
         South wall (z = D)

Origin:   front-left floor corner after COLMAP alignment
X:        room width direction (right)
Z:        room depth direction (away from entry)
Y:        up (floor at Y=0 after plane fitting)

All object positions = centre of object bounding box base on floor (Y=0)
```

---

## 5. Complete Tech Stack

### Frontend

| Technology          | Version | Purpose                                          |
|---------------------|---------|--------------------------------------------------|
| Next.js             | 14+     | Web framework, routing, API proxy                |
| React               | 18+     | Component architecture                           |
| Three.js            | r160+   | 3D scene rendering                               |
| @react-three/fiber  | latest  | React renderer for Three.js                      |
| @react-three/drei   | latest  | OrbitControls, GLTF loader, OutlineEffect, Html  |
| Zustand             | latest  | Global state: SceneScript, selection, chat       |
| Tailwind CSS        | 3+      | UI styling                                       |

### Backend (CPU — your laptop or any server)

| Technology          | Version | Purpose                                          |
|---------------------|---------|--------------------------------------------------|
| FastAPI             | 0.110+  | API server, session management, proxy            |
| Python              | 3.11+   | Backend language                                 |
| httpx               | 0.27+   | Async calls to GPU worker and Claude API         |
| pydantic            | v2+     | Request/response validation                      |
| python-multipart    | latest  | Video upload handling                            |
| jsonschema          | 4.22+   | SceneScript validation                           |
| python-dotenv       | latest  | Environment variables                            |
| anthropic           | 0.25+   | Claude API client                                |
| uvicorn             | latest  | ASGI server                                      |

### GPU Worker (Google Colab or RunPod — separate from backend)

| Technology          | Version | Purpose                                          |
|---------------------|---------|--------------------------------------------------|
| Python              | 3.11+   | Worker language                                  |
| opencv-python       | 4.9+    | Frame extraction, image preprocessing            |
| numpy               | 1.26+   | Array operations                                 |
| COLMAP              | latest  | Structure from Motion, sparse reconstruction     |
| pycolmap            | 0.6+    | Python bindings for COLMAP                       |
| Depth-Anything-V2   | latest  | Dense per-pixel monocular depth estimation       |
| torch               | 2.2+    | PyTorch for depth + detection models             |
| torchvision         | latest  | Vision utilities                                 |
| transformers        | 4.40+   | GroundingDINO model loading (HuggingFace)        |
| groundingdino       | latest  | Open-vocabulary object detection                 |
| segment-anything    | latest  | SAM — pixel-level object segmentation            |
| open3d              | 0.18+   | Point cloud fusion, plane fitting, geometry      |
| flask               | latest  | Simple HTTP server for GPU worker API            |
| pyngrok             | latest  | Expose Colab to internet for hackathon           |

### AI

| Technology          | Purpose                                          |
|---------------------|--------------------------------------------------|
| Claude claude-sonnet-4-20250514 (text only) | Semantic labelling of detected objects, design agent, action generation |
| GroundingDINO       | Primary object detection (runs on GPU)           |
| Depth Anything V2   | Dense depth estimation (runs on GPU)             |
| SAM (ViT-H)         | Pixel-level segmentation (runs on GPU)           |

### Product Discovery

| Technology          | Purpose                                          |
|---------------------|--------------------------------------------------|
| SerpAPI             | Google Shopping results (preferred)              |
| Google Custom Search| Free tier fallback (100 queries/day)             |
| BeautifulSoup       | Direct retailer scrape as final fallback         |

---

## 6. Infrastructure Requirements

### For the hackathon (3 days)

```
Your laptop (CPU backend):
  - Any machine with Python 3.11+, Node 18+
  - Runs: FastAPI backend, Next.js frontend
  - Does NOT run the heavy CV models

Google Colab (GPU worker):
  - Free tier with T4 GPU is sufficient for Depth Anything + SAM
  - Colab Pro ($10/month) recommended — T4/A100, no timeouts
  - Runs: COLMAP, Depth Anything, GroundingDINO, SAM, Open3D
  - Exposed via pyngrok tunnel to your FastAPI backend
  - Processing time per room: ~60-120 seconds on T4 GPU
```

### For production (post-hackathon)

```
GPU server options:
  RunPod:   $0.20/hr for RTX 4090 — excellent price/performance
  Lambda:   $0.50/hr for A10 — good for continuous inference
  AWS g4dn: $0.53/hr for T4 — easy if already on AWS

Minimum GPU spec:
  - 16GB VRAM (SAM ViT-H needs ~10GB)
  - 16GB RAM
  - COLMAP can use CPU but is 10x slower without GPU
```

### Model sizes (download once, keep on GPU worker)

| Model              | Size    | Where to get it                          |
|--------------------|---------|------------------------------------------|
| Depth Anything V2  | ~1.3 GB | HuggingFace: depth-anything/Depth-Anything-V2-Large |
| GroundingDINO      | ~700 MB | HuggingFace: IDEA-Research/grounding-dino |
| SAM ViT-H          | ~2.4 GB | Meta: sam_vit_h_4b8939.pth               |
| COLMAP             | ~200 MB | colmap.github.io / apt install colmap    |

**Total disk on GPU worker: ~5 GB for models + COLMAP**

---

## 7. Environment Setup

### Backend `.env`

```bash
# Claude
ANTHROPIC_API_KEY=sk-ant-...

# GPU Worker
GPU_WORKER_URL=https://abc123.ngrok.io   # Colab ngrok tunnel URL
GPU_WORKER_SECRET=your-shared-secret     # Basic auth between backend and worker

# Product Search
SERPAPI_KEY=...
GOOGLE_CSE_KEY=...
GOOGLE_CSE_CX=...

# App Config
SESSION_TTL_SECONDS=7200
MAX_HISTORY_VERSIONS=20
MAX_VIDEO_SIZE_MB=200
ALLOWED_VIDEO_TYPES=mp4,mov,avi,webm
FRAME_EXTRACT_INTERVAL_SECONDS=1        # 1 frame/sec for COLMAP (needs overlap)
MIN_FRAMES_COLMAP=30                    # COLMAP needs 30+ frames for good result
MAX_FRAMES_COLMAP=80                    # Cap to avoid Colab timeout

# Environment
ENV=development
CORS_ORIGINS=http://localhost:3000
```

### Backend `requirements.txt`

```
fastapi==0.110.0
uvicorn==0.29.0
python-multipart==0.0.9
httpx==0.27.0
anthropic==0.25.0
jsonschema==4.22.0
pydantic==2.7.0
python-dotenv==1.0.1
beautifulsoup4==4.12.3
aiofiles==23.2.1
```

### GPU Worker setup (run once in Colab)

```python
# Cell 1: Install everything
!pip install pycolmap open3d transformers groundingdino-py
!pip install git+https://github.com/facebookresearch/segment-anything.git
!pip install git+https://github.com/LiheYoung/Depth-Anything.git
!pip install flask pyngrok

# Cell 2: Download models
import os
os.makedirs('/content/models', exist_ok=True)

# SAM
!wget -q https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth \
     -O /content/models/sam_vit_h.pth

# Depth Anything V2 (HuggingFace automatic download on first use)
# GroundingDINO (HuggingFace automatic download on first use)

# Cell 3: Install COLMAP
!apt-get install -y colmap

# Cell 4: Start the Flask worker server + ngrok tunnel
# (see Section 9, Step 3 for the full Flask server code)
```

---

## 8. Project Folder Structure

```
room-design-ai/
│
├── frontend/
│   ├── .env.local
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                      # Upload + onboarding
│   │   ├── scan/page.tsx                 # Processing progress
│   │   ├── correct/page.tsx              # Correction UI
│   │   └── design/page.tsx               # Main 3D + chat + shop
│   │
│   ├── components/
│   │   ├── upload/
│   │   │   ├── VideoUploader.tsx
│   │   │   └── FilmingInstructions.tsx
│   │   ├── scan/
│   │   │   └── ScanProgress.tsx          # Stage-by-stage: COLMAP → Depth → SAM → Open3D
│   │   ├── correction/
│   │   │   ├── CorrectionPanel.tsx
│   │   │   └── ObjectRow.tsx
│   │   ├── scene/
│   │   │   ├── SceneViewer.tsx           # Canvas wrapper
│   │   │   ├── RoomGeometry.tsx          # Floor + walls from SceneScript
│   │   │   ├── ObjectMesh.tsx            # GLTF + box fallback
│   │   │   ├── PointCloudOverlay.tsx     # Optional: render raw point cloud
│   │   │   ├── SelectionOutline.tsx
│   │   │   └── HoverTooltip.tsx
│   │   ├── action/
│   │   │   └── ActionPanel.tsx
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx
│   │   │   └── MessageBubble.tsx
│   │   └── shop/
│   │       ├── ProductPanel.tsx
│   │       └── ProductCard.tsx
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── types.ts
│   │   ├── objectSizes.ts                # Fallback sizes if CV size extraction fails
│   │   └── store.ts
│   │
│   └── public/
│       ├── models/                       # GLTF furniture files
│       └── textures/
│
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── main.py
│   ├── routers/
│   │   ├── upload.py                     # POST /api/upload
│   │   ├── scan.py                       # POST /api/scan (proxies to GPU worker)
│   │   ├── scene.py                      # GET/PUT /api/scene
│   │   ├── agent.py                      # POST /api/agent
│   │   ├── undo.py                       # POST /api/scene/undo
│   │   └── shop.py                       # POST /api/shop/search + /place
│   ├── services/
│   │   ├── gpu_proxy.py                  # Proxies heavy jobs to GPU worker
│   │   ├── scene_builder.py              # Fuses GPU worker output → SceneScript
│   │   ├── scene_validator.py            # Constraint checks on SceneScript
│   │   ├── design_agent.py               # Claude design agent
│   │   └── product_search.py             # SerpAPI / CSE / scrape
│   ├── models/
│   │   ├── scene_script.py               # Pydantic SceneScript model
│   │   └── agent_action.py               # Pydantic action models
│   ├── prompts/
│   │   ├── labelling_prompt.py           # Claude: label geometry objects
│   │   └── agent_prompt.py               # Claude: design agent
│   ├── data/
│   │   ├── object_sizes.py               # Fallback size lookup table
│   │   └── demo_scene.py                 # Hardcoded fallback SceneScript
│   └── session/
│       └── store.py                      # In-memory session dict
│
├── gpu_worker/
│   ├── worker.py                         # Flask server that runs on Colab
│   ├── pipeline/
│   │   ├── frame_extractor.py            # OpenCV frame extraction
│   │   ├── colmap_runner.py              # Runs COLMAP, parses output
│   │   ├── depth_estimator.py            # Depth Anything V2 inference
│   │   ├── object_detector.py            # GroundingDINO inference
│   │   ├── segmenter.py                  # SAM inference
│   │   └── geometry_fusion.py            # Open3D fusion + plane fitting
│   └── utils/
│       ├── image_utils.py
│       └── pointcloud_utils.py
│
└── shared/
    └── scene_schema.json                 # JSON schema for SceneScript
```

---

## 9. Pipeline — Step by Step

---

### Step 1 — Video Upload and Onboarding

**What happens:** User sees filming instructions, selects room dimensions as an
anchor (still needed even with COLMAP — helps with scale disambiguation), then
uploads their video.

**Filming requirements for COLMAP (stricter than before):**
```
  Walk SLOWLY — COLMAP needs high frame overlap between views
  Minimum 30% overlap between consecutive frames
  Good lighting — depth models need texture
  Avoid purely white walls with zero texture
  Do NOT use flash — creates specular highlights that confuse depth
  Walk the full perimeter, then across the middle
  30-45 seconds minimum — shorter videos give COLMAP too few frames
  Landscape orientation
```

**Why room dimensions are still asked:**
COLMAP recovers camera poses up to an unknown scale factor. Providing the approximate
room size allows the pipeline to resolve this ambiguity and output real metric
coordinates. Without it, all coordinates are in "COLMAP units" which are
proportionally correct but not in metres.

**Output:** Video at `/tmp/{session_id}/video.mp4`, dimensions stored in session.

---

### Step 2 — Frame Extraction

**What happens:** Extract frames at 1 frame per second (not 2) because COLMAP needs
high overlap. Score for sharpness. Cap at 80 frames to avoid Colab timeouts.

```python
# pipeline/frame_extractor.py

import cv2
import numpy as np

def extract_frames(video_path: str, output_dir: str,
                   interval_sec: float = 1.0,
                   max_frames: int = 80) -> list[str]:

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval_frames = int(fps * interval_sec)

    frames_saved = []
    frame_idx = 0

    while cap.isOpened() and len(frames_saved) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval_frames == 0:
            # Sharpness score
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Only save if sharp enough
            if score > 50.0:
                path = f"{output_dir}/frame_{len(frames_saved):04d}.jpg"
                cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                frames_saved.append({"path": path, "sharpness": score,
                                     "frame_idx": frame_idx})

        frame_idx += 1

    cap.release()
    return frames_saved
```

**Output:** 30–80 JPEG frames, each with a sharpness score.

---

### Step 3 — COLMAP: Camera Poses and Sparse Reconstruction

**What COLMAP does:**
- Feature extraction (SIFT features) from all frames
- Feature matching between frame pairs
- Structure from Motion (SfM): finds where the camera was at each frame and
  builds a sparse 3D point cloud of scene landmarks
- This gives us: camera intrinsics, camera extrinsics (pose per frame), and
  a sparse set of 3D points with known world coordinates

**Why this matters:** Camera poses are required for Depth Anything to produce
consistent depth maps across frames and for Open3D to fuse depths into one
coherent point cloud.

```python
# pipeline/colmap_runner.py

import subprocess
import pycolmap
import numpy as np
from pathlib import Path

def run_colmap(frames_dir: str, output_dir: str,
               room_width: float, room_depth: float) -> dict:

    images_path = Path(frames_dir)
    database_path = Path(output_dir) / "colmap.db"
    sparse_path = Path(output_dir) / "sparse"
    sparse_path.mkdir(parents=True, exist_ok=True)

    # 1. Feature extraction
    subprocess.run([
        "colmap", "feature_extractor",
        "--database_path", str(database_path),
        "--image_path", str(images_path),
        "--ImageReader.camera_model", "SIMPLE_RADIAL",
        "--SiftExtraction.use_gpu", "1"
    ], check=True)

    # 2. Exhaustive matching (sequential for video frames)
    subprocess.run([
        "colmap", "sequential_matcher",
        "--database_path", str(database_path),
        "--SequentialMatching.overlap", "10"   # match each frame to 10 neighbours
    ], check=True)

    # 3. Sparse reconstruction (SfM)
    subprocess.run([
        "colmap", "mapper",
        "--database_path", str(database_path),
        "--image_path", str(images_path),
        "--output_path", str(sparse_path)
    ], check=True)

    # 4. Parse COLMAP output with pycolmap
    reconstruction = pycolmap.Reconstruction(str(sparse_path / "0"))

    # 5. Scale alignment using room dimensions
    # COLMAP gives proportional coordinates — we scale to metres
    points3d = np.array([p.xyz for p in reconstruction.points3D.values()])
    x_range = points3d[:, 0].max() - points3d[:, 0].min()
    z_range = points3d[:, 2].max() - points3d[:, 2].min()

    # Scale factor: average of X and Z alignment to room dimensions
    scale_x = room_width / x_range if x_range > 0 else 1.0
    scale_z = room_depth / z_range if z_range > 0 else 1.0
    scale = (scale_x + scale_z) / 2.0

    # Extract camera poses per image (for depth fusion)
    camera_poses = {}
    for img_id, image in reconstruction.images.items():
        R = image.rotation_matrix()
        t = image.tvec
        camera_poses[image.name] = {
            "R": R.tolist(),
            "t": (t * scale).tolist(),
            "camera_id": image.camera_id
        }

    # Extract camera intrinsics
    camera_intrinsics = {}
    for cam_id, camera in reconstruction.cameras.items():
        camera_intrinsics[cam_id] = {
            "fx": camera.focal_length,
            "fy": camera.focal_length,
            "cx": camera.principal_point_x,
            "cy": camera.principal_point_y,
            "width": camera.width,
            "height": camera.height
        }

    return {
        "camera_poses": camera_poses,
        "camera_intrinsics": camera_intrinsics,
        "scale_factor": scale,
        "num_images_registered": len(reconstruction.images),
        "num_points3d": len(reconstruction.points3D),
        "sparse_path": str(sparse_path)
    }
```

**COLMAP failure handling:**
If fewer than 10 frames register successfully, COLMAP has failed (not enough texture
or overlap). In this case, fall back to the Claude Vision approximate pipeline
(from the old plan) and mark the scene as `"confidence": "approximate"` in metadata.
Always tell the user which mode was used.

**Output:** Camera poses per frame, camera intrinsics, scale factor, sparse point cloud.

---

### Step 4 — Depth Anything V2: Dense Depth Maps

**What it does:** For each selected frame, generates a full-resolution per-pixel
depth map. Combined with camera poses from COLMAP, these depth maps can be
back-projected into 3D space to form a dense point cloud.

```python
# pipeline/depth_estimator.py

import torch
import numpy as np
import cv2
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image

class DepthEstimator:
    def __init__(self, model_name="depth-anything/Depth-Anything-V2-Large-hf"):
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_name)
        self.model = self.model.cuda().eval()

    def estimate(self, image_path: str, camera_intrinsics: dict,
                 scale_factor: float) -> np.ndarray:
        """Returns depth map in metres, same resolution as input image."""

        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process: upsample to original resolution
        depth_raw = outputs.predicted_depth.squeeze().cpu().numpy()
        h, w = np.array(image).shape[:2]
        depth_raw = cv2.resize(depth_raw, (w, h), interpolation=cv2.INTER_LINEAR)

        # Depth Anything outputs inverse depth (disparity-like)
        # Convert to metric depth using scale factor from COLMAP
        # This alignment step calibrates relative depth to absolute metres
        depth_metric = scale_factor / (depth_raw + 1e-6)

        return depth_metric   # shape: (H, W), values in metres
```

**Why Depth Anything V2 and not MiDaS:**
Depth Anything V2 is the current state of the art for monocular depth. It is
substantially more accurate than MiDaS, especially in indoor environments, and
handles untextured surfaces (white walls, carpets) much better. It is available
on HuggingFace and loads in two lines of code.

**Output:** Per-frame depth maps in metres, shape `(H, W)`.

---

### Step 5 — GroundingDINO + SAM: Object Detection and Segmentation

**What it does:**
- GroundingDINO detects objects using a text prompt (no fixed class list)
- SAM produces pixel-perfect segmentation masks for each detected object
- Together they give us: what is in the room, where in the image it is,
  and its exact pixel boundary

```python
# pipeline/object_detector.py

import torch
import numpy as np
from groundingdino.util.inference import load_model, load_image, predict
from segment_anything import sam_model_registry, SamPredictor

# Text prompt: covers all common room furniture
DETECTION_PROMPT = (
    "sofa . armchair . chair . table . coffee table . dining table . "
    "desk . bed . wardrobe . bookshelf . bookcase . tv . television . "
    "tv stand . tv unit . plant . lamp . door . window . cabinet . "
    "dresser . nightstand . rug . curtain . mirror"
)

class ObjectDetectorAndSegmenter:
    def __init__(self, dino_config, dino_weights, sam_weights):
        # Load GroundingDINO
        self.dino = load_model(dino_config, dino_weights)

        # Load SAM
        sam = sam_model_registry["vit_h"](checkpoint=sam_weights)
        sam.cuda()
        self.sam_predictor = SamPredictor(sam)

    def detect_and_segment(self, image_path: str,
                            box_threshold: float = 0.35,
                            text_threshold: float = 0.25) -> list[dict]:
        """
        Returns list of detected objects with:
          - label: detected class name
          - confidence: detection score
          - bbox: [x1, y1, x2, y2] in pixels
          - mask: binary np.ndarray (H, W) from SAM
        """
        image_source, image_tensor = load_image(image_path)
        H, W = image_source.shape[:2]

        # GroundingDINO detection
        boxes, logits, phrases = predict(
            model=self.dino,
            image=image_tensor,
            caption=DETECTION_PROMPT,
            box_threshold=box_threshold,
            text_threshold=text_threshold
        )

        # Convert normalised boxes to pixel coords
        boxes_px = boxes * np.array([W, H, W, H])
        boxes_px[:, :2] -= boxes_px[:, 2:] / 2   # cx,cy,w,h → x1,y1,w,h
        boxes_px[:, 2:] += boxes_px[:, :2]         # → x1,y1,x2,y2

        # SAM segmentation for each detected box
        self.sam_predictor.set_image(image_source)
        results = []

        for i, (box, phrase, conf) in enumerate(zip(boxes_px, phrases, logits)):
            masks, scores, _ = self.sam_predictor.predict(
                box=box,
                multimask_output=True
            )
            best_mask = masks[np.argmax(scores)]

            results.append({
                "label": phrase,
                "confidence": float(conf),
                "bbox": box.tolist(),
                "mask": best_mask,   # shape: (H, W) bool
                "mask_id": f"mask_{i:03d}"
            })

        return results
```

**GroundingDINO vs YOLO:**
YOLO uses a fixed set of class labels and will never detect "tv_unit" or "wardrobe"
unless specifically trained on them. GroundingDINO is open-vocabulary — you give it
any text description and it finds matching objects. This is substantially better for
room interiors which have non-COCO furniture classes. The detection quality is also
higher for this use case.

**Output per frame:** List of detected objects with bounding boxes and pixel masks.

---

### Step 6 — Open3D: Point Cloud Fusion and Geometry

**What it does:**
- Back-projects depth maps using camera poses to get 3D points for each frame
- Fuses all frames' point clouds into one unified dense point cloud
- Fits planes to find the floor and walls
- Uses plane equations to compute room dimensions
- Segments the point cloud by floor/wall planes to isolate floating objects (furniture)
- Computes bounding boxes of object clusters in 3D

```python
# pipeline/geometry_fusion.py

import open3d as o3d
import numpy as np

def depth_to_pointcloud(depth_map, K, R, t, color_image=None):
    """Back-project one depth map to 3D using camera intrinsics + extrinsics."""
    H, W = depth_map.shape
    fx, fy = K["fx"], K["fy"]
    cx, cy = K["cx"], K["cy"]

    u, v = np.meshgrid(np.arange(W), np.arange(H))
    z = depth_map

    # Only use pixels with valid depth (not too close, not too far)
    valid = (z > 0.1) & (z < 10.0)

    x = (u[valid] - cx) * z[valid] / fx
    y = (v[valid] - cy) * z[valid] / fy
    z_vals = z[valid]

    # Camera-space points
    pts_cam = np.stack([x, y_vals, z_vals], axis=1)  # (N, 3)

    # Transform to world space using COLMAP pose
    pts_world = (R @ pts_cam.T).T + t

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts_world)

    if color_image is not None:
        colors = color_image.reshape(-1, 3)[valid] / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors)

    return pcd


def fuse_and_analyse(frame_pcds: list, room_width: float, room_depth: float) -> dict:
    """Fuse all per-frame point clouds and extract room geometry."""

    # 1. Merge all point clouds
    merged = o3d.geometry.PointCloud()
    for pcd in frame_pcds:
        merged += pcd

    # 2. Voxel downsampling (reduce to ~500k points for speed)
    merged = merged.voxel_down_sample(voxel_size=0.02)

    # 3. Statistical outlier removal
    merged, _ = merged.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

    # 4. Fit floor plane using RANSAC
    floor_plane, floor_inliers = merged.segment_plane(
        distance_threshold=0.02,
        ransac_n=3,
        num_iterations=1000
    )
    [a, b, c, d] = floor_plane

    # 5. Remove floor points, fit wall planes
    non_floor = merged.select_by_index(floor_inliers, invert=True)

    # Fit up to 4 wall planes iteratively
    wall_planes = []
    remaining = non_floor
    for _ in range(4):
        if len(remaining.points) < 100:
            break
        plane, inliers = remaining.segment_plane(
            distance_threshold=0.05, ransac_n=3, num_iterations=500
        )
        # Only keep near-vertical planes (walls have near-zero Y component)
        if abs(plane[1]) < 0.3:
            wall_planes.append({"equation": plane, "inliers": inliers})
        remaining = remaining.select_by_index(inliers, invert=True)

    # 6. Remaining points = furniture/objects
    # Cluster them using DBSCAN
    labels = np.array(remaining.cluster_dbscan(eps=0.1, min_points=50))
    num_clusters = labels.max() + 1

    object_clusters = []
    for cluster_id in range(num_clusters):
        cluster_mask = labels == cluster_id
        cluster_pcd = remaining.select_by_index(np.where(cluster_mask)[0])
        bbox = cluster_pcd.get_axis_aligned_bounding_box()

        min_b = np.asarray(bbox.min_bound)
        max_b = np.asarray(bbox.max_bound)

        # Position = centre base on floor (Y = 0)
        centre_x = (min_b[0] + max_b[0]) / 2
        centre_z = (min_b[2] + max_b[2]) / 2

        object_clusters.append({
            "cluster_id": cluster_id,
            "position": {"x": float(centre_x), "y": 0.0, "z": float(centre_z)},
            "size": {
                "w": float(max_b[0] - min_b[0]),
                "h": float(max_b[1] - min_b[1]),
                "d": float(max_b[2] - min_b[2])
            },
            "num_points": int(cluster_mask.sum())
        })

    return {
        "floor_plane": floor_plane.tolist(),
        "wall_planes": [{"equation": wp["equation"].tolist()} for wp in wall_planes],
        "object_clusters": object_clusters,
        "total_points": len(merged.points)
    }
```

**Output:** Floor plane, wall planes, list of object clusters with real 3D positions
and sizes in metres.

---

### Step 7 — SceneScript Generation: Fusing All Data

**What happens:** The CPU backend (FastAPI) receives all outputs from the GPU worker
and fuses them into the final SceneScript.

The fusion logic:
1. Takes each object cluster from Open3D (has position + size in 3D)
2. Matches it to detected objects from GroundingDINO (has label + image bbox)
3. Matching is done by projecting the cluster's 3D centre back into each image
   and checking if it falls within a GroundingDINO bounding box
4. The matched label becomes the object type
5. If no GroundingDINO match, the cluster is kept as `type: "other"`

```python
# services/scene_builder.py

def fuse_to_scene_script(session_id, gpu_output, room_width, room_depth):
    """
    gpu_output contains:
      - colmap_result: camera poses, intrinsics, scale
      - depth_maps: per-frame depth arrays
      - detections: per-frame GroundingDINO + SAM results
      - geometry: Open3D clusters, floor/wall planes
    """

    clusters = gpu_output["geometry"]["object_clusters"]
    detections_by_frame = gpu_output["detections"]
    camera_poses = gpu_output["colmap_result"]["camera_poses"]
    intrinsics = gpu_output["colmap_result"]["camera_intrinsics"]

    objects = []
    for cluster in clusters:
        # Find best matching detection label across all frames
        best_label, best_conf = match_cluster_to_detection(
            cluster, detections_by_frame, camera_poses, intrinsics
        )

        # Normalise label to valid object type
        obj_type = normalise_label(best_label)  # "three seater sofa" → "sofa"

        obj = {
            "id": f"obj_{len(objects)+1:03d}",
            "type": obj_type,
            "label_source": "grounding_dino",
            "label_confirmed": False,   # user must confirm in correction UI
            "position": cluster["position"],
            "size": cluster["size"],
            "rotation_y": 0.0,
            "color": extract_dominant_color(cluster, gpu_output["depth_maps"]),
            "style": None,
            "point_cloud_cluster_id": cluster["cluster_id"],
            "detection_confidence": best_conf,
            "product_url": None,
            "product_name": None
        }
        objects.append(obj)

    # Build wall geometry from wall planes
    walls = build_walls_from_planes(
        gpu_output["geometry"]["wall_planes"], room_width, room_depth
    )

    scene = {
        "version": 1,
        "session_id": session_id,
        "source": "colmap_pipeline",
        "room": {
            "width": room_width,
            "depth": room_depth,
            "height": 2.8   # estimated from wall plane heights
        },
        "walls": walls,
        "windows": extract_openings(detections_by_frame, "window"),
        "doors": extract_openings(detections_by_frame, "door"),
        "objects": objects,
        "metadata": {
            "room_type": infer_room_type(objects),
            "pipeline_version": "colmap_v1",
            "colmap_registered": gpu_output["colmap_result"]["num_images_registered"],
            "confidence": "metric"
        }
    }
    return scene
```

---

### Step 8 — Claude: Semantic Labelling and Design Agent

**Claude's role in the new pipeline is purely semantic and linguistic.**
It never sees raw images. It never estimates positions. It receives structured data
and either returns better labels or returns design actions.

**Labelling prompt (one-time, after fusion):**
```
You are an interior design AI reviewing a room analysis.
The computer vision pipeline has detected these objects with these labels:

{list of detected labels with positions}

Your task:
1. Correct any label that seems wrong (e.g. "three seater" → "sofa")
2. Infer the room type (living_room, bedroom, dining_room, office, etc.)
3. Suggest a style if clearly apparent (minimalist, maximalist, etc.)

Return ONLY valid JSON:
{
  "corrected_labels": { "obj_001": "sofa", "obj_002": "coffee_table" },
  "room_type": "living_room",
  "style": "minimalist"
}
```

**Design agent prompt (on every user instruction — same as before):**
```
You are an interior design AI editing a room.

Current SceneScript:
{scene_script_json}

{selected_object_block if object selected}

User instruction: "{instruction}"

Return a single JSON action object only. No explanation. No markdown.
{...action schemas...}
```

---

### Step 9 — Three.js Interactive 3D Render

The Three.js rendering is identical to the previous plan. The only difference is
that positions and sizes now come from real CV measurements, not guesses.
Refer to the Three.js implementation guide from the previous version — all code
remains valid. The SceneScript format is the same.

**One addition: optional point cloud overlay**

```tsx
// components/scene/PointCloudOverlay.tsx
// Shows the raw Open3D point cloud as a Three.js Points object
// Good for demo: shows "see, this is real geometry"

import { useMemo } from 'react'
import * as THREE from 'three'

export function PointCloudOverlay({ plyPath, visible }) {
  // Load PLY file via Three.js PLYLoader
  // Render as Points with PointsMaterial
  // Toggle with a "Show Point Cloud" button in the UI
}
```

---

### Step 10 — Hover-to-Shop

**Identical to the previous plan.** When the user hovers over a detected furniture
object for 500ms, a tooltip appears. "Find this item" triggers a product search
using the object type and color. Product results appear. User can place a product
in the scene. Refer to Section 13 of the previous plan for the full spec.

The only improvement: since we now know real product dimensions from Open3D, we can
better filter product search results to those within 20% of the actual detected size.

---

## 10. Complete API Contract

### POST /api/upload
Upload video + room dimensions.

**Request:** `multipart/form-data`
```
file: <video>
room_width: 4.5
room_depth: 5.0
```

**Response 200:**
```json
{ "session_id": "uuid", "status": "uploaded", "duration_seconds": 34 }
```

---

### POST /api/scan
Trigger the full CV pipeline (proxied to GPU worker).

**Request:**
```json
{ "session_id": "uuid" }
```

**Response 200** (may take 60-120s — use polling or SSE):
```json
{
  "session_id": "uuid",
  "status": "complete",
  "pipeline_used": "colmap",
  "scene": { ...SceneScript... },
  "warnings": ["colmap_low_coverage: 18/42 frames registered"]
}
```

**Fallback response** (if COLMAP fails):
```json
{
  "session_id": "uuid",
  "status": "complete",
  "pipeline_used": "claude_vision_fallback",
  "scene": { ...SceneScript with confidence: approximate... },
  "warnings": ["colmap_failed: insufficient_overlap — using claude_vision_fallback"]
}
```

---

### GET /api/scan/status/{session_id}
Poll for scan progress.

**Response 200:**
```json
{
  "session_id": "uuid",
  "status": "processing",
  "stage": "depth_estimation",
  "stages_complete": ["frame_extraction", "colmap"],
  "stages_remaining": ["depth_estimation", "detection", "fusion"],
  "elapsed_seconds": 45
}
```

---

### POST /api/agent
Send design instruction.

**Request:**
```json
{
  "session_id": "uuid",
  "instruction": "Replace the sofa with a leather armchair",
  "selected_object_id": "obj_001"
}
```

**Response 200:**
```json
{
  "action": { "action": "replace", "object_id": "obj_001", ... },
  "scene": { ...updated SceneScript... },
  "message": "Replaced the sofa with a brown leather armchair."
}
```

---

### POST /api/scene/undo
**Request:** `{ "session_id": "uuid" }`
**Response 200:** `{ "scene": {...}, "version": 3 }`

---

### PUT /api/scene/correct
Save user corrections from correction UI.

**Request:** `{ "session_id": "uuid", "scene": {...SceneScript...} }`
**Response 200:** `{ "scene": {...validated SceneScript...}, "status": "confirmed" }`

---

### POST /api/shop/search
**Request:** `{ "object_type": "sofa", "color": "grey", "style": null, "max_width_m": 2.2 }`
**Response 200:** `{ "results": [...], "source": "serpapi" }`

---

### POST /api/shop/place
**Request:** `{ "session_id": "uuid", "object_id": "obj_001", "product": {...} }`
**Response 200:** `{ "scene": {...updated SceneScript...} }`

---

## 11. Memory and State Management

**Identical to previous plan — the SceneScript IS the memory.**

Every Claude agent call receives the full current SceneScript. No conversation
history is sent. The SceneScript contains the complete room state. Claude does not
need to remember anything.

```
Agent call N:   SceneScript_vN  +  instruction  →  SceneScript_vN+1
Agent call N+1: SceneScript_vN+1 + instruction  →  SceneScript_vN+2
```

**Version history stack** in backend session store — same implementation as before.
Max 20 versions. Undo pops the stack.

**Zustand frontend store** — same as before. Holds current SceneScript, selected
object ID, hovered object ID, chat history, loading states.

---

## 12. Object Selection and Replacement Flow

**Identical to previous plan.** Three.js raycasting detects hovered and clicked
objects. Selection triggers ActionPanel. User types instruction. Backend calls
Claude with full SceneScript + selected object ID. Claude returns action JSON.
Backend validates + applies. Frontend partial re-renders changed objects only.

The SceneScript structure is unchanged so all this code is the same.

---

## 13. Known Issues and Exact Solutions

| # | Issue | Cause | Solution |
|---|---|---|---|
| 1 | COLMAP fails on textureless walls | White walls have no SIFT features | Add minimum texture check; fall back to Claude Vision pipeline if < 10 frames register |
| 2 | COLMAP scale ambiguity | SfM has no absolute scale | User provides room dimensions; scale aligned using X/Z range |
| 3 | Depth Anything scale drift | Monocular depth is relative | Calibrate to COLMAP scale using matched feature points |
| 4 | GroundingDINO misses small objects | Objects smaller than ~50px in image | Run detection at multiple scales; supplement with user correction UI |
| 5 | SAM mask bleeds into adjacent objects | Objects touching each other | Use GroundingDINO box as hard prompt boundary for SAM |
| 6 | Open3D DBSCAN merges adjacent furniture | Nearby objects cluster together | Tune eps parameter; use wall/floor plane constraints to separate clusters |
| 7 | Object cluster has no matching detection | Object occluded in all frames | Keep as `type: "other"`, user renames in correction UI |
| 8 | Claude Vision fallback triggered | COLMAP failed | System continues with approximate positions; user notified via banner |
| 9 | GPU worker timeout on Colab | Free tier 90-minute limit | Use Colab Pro ($10/mo); cap frames at 80; show scan time estimate |
| 10 | Objects float above floor | Depth scale error | Floor plane fitting anchors all object Y to 0 in Open3D step |
| 11 | Scene drift after many edits | Agent errors accumulate | Versioned SceneScript + rollback on validation failure |
| 12 | Product search returns wrong size | Product dimensions not in listing | Filter by size ± 20% from SceneScript; show dimensions in product card |
| 13 | Colab session dies mid-scan | Network dropout | Scan is idempotent — re-upload triggers fresh scan; show retry button |

---

## 14. Build Phases — Realistic Timeline

This is NOT a 3-day build for the full COLMAP pipeline.
Be honest about what you can ship when.

### Hackathon Phase (3 days) — Hybrid approach

**Day 1 and 2:** Build with the Claude Vision fallback pipeline (old plan).
This is fast, reliable, and ships a working demo. The SceneScript format, correction
UI, agent chat, Three.js render, and hover-to-shop all work identically.

**Day 3:** Integrate the COLMAP GPU worker as an enhancement path.
Run it on Colab. If it succeeds, the scene is metric-accurate.
If it fails, fall back to Claude Vision automatically.
The demo shows both paths. The audience sees the ambition.

The key insight: because the SceneScript format is identical whether it came from
COLMAP or Claude Vision, all the UI and agent code works for both. You build once,
plug in the better pipeline when ready.

### Post-Hackathon Phase 1 (2–4 weeks)

- Full COLMAP pipeline deployed on RunPod GPU server
- Depth Anything + Open3D geometry fully integrated
- GroundingDINO replacing Claude Vision for object detection
- SAM segmentation for precise object boundaries
- Remove Claude Vision fallback (replaced by proper CV)

### Post-Hackathon Phase 2 (1–3 months)

- COLMAP upgraded to COLMAP with dense MVS (better geometry)
- Consider MASt3R or VGGT if open-sourced and stable — potentially COLMAP-free
- Open3D replaced with more sophisticated scene graph construction
- Style-aware product matching

---

## 15. Day-by-Day Build Order (Hackathon Mode)

### Day 1 — Core Pipeline (Claude Vision path)

**Morning:**
- [ ] Project scaffolding: Next.js + FastAPI + folder structure
- [ ] All dependencies installed, `.env` files created
- [ ] Video upload endpoint + drag-drop UI
- [ ] Frame extraction service (OpenCV, sharpness filter)
- [ ] Room dimension onboarding modal

**Afternoon:**
- [ ] Claude Vision prompt (finalise in Claude.ai first)
- [ ] Vision analysis service + JSON parser
- [ ] Fraction-to-metres conversion + standard size lookup
- [ ] Deduplication pass
- [ ] SceneScript Pydantic model + `scene_schema.json`

**Evening:**
- [ ] SceneScript validator (floor anchor + bounds + overlap + version)
- [ ] Session store
- [ ] End-to-end test: video → SceneScript via Claude Vision
- [ ] Fix any prompt failures before sleeping
- [ ] COLMAP GPU worker notebook started in Colab (run installation cells overnight)

---

### Day 2 — 3D Interface + Agent

**Morning:**
- [ ] Three.js canvas setup (camera, lighting, shadows)
- [ ] RoomGeometry component (walls, floor from SceneScript)
- [ ] ObjectMesh component (GLTF + BoxGeometry fallback)
- [ ] Download 8 GLTF models: sofa, chair, table, bed, wardrobe, plant, lamp, bookshelf
- [ ] Demo fallback SceneScript loads and renders correctly

**Afternoon:**
- [ ] Raycasting: hover (500ms dwell) + click selection
- [ ] HoverTooltip + SelectionOutline + ActionPanel
- [ ] Correction UI: list, rename, delete, add, confirm
- [ ] PUT /api/scene/correct endpoint

**Evening:**
- [ ] Design agent prompt (finalise in Claude.ai first)
- [ ] POST /api/agent endpoint
- [ ] All action types working: replace, move, add, remove, restyle, update
- [ ] POST /api/scene/undo
- [ ] Partial re-render working (only changed objects update)

---

### Day 3 — Shop + COLMAP Integration + Polish

**Morning:**
- [ ] Hover-to-shop: "Find this item" → product search → ProductPanel
- [ ] POST /api/shop/search (SerpAPI or scrape fallback)
- [ ] POST /api/shop/place (update SceneScript with product + real dimensions)
- [ ] "Buy Now" link on placed products

**Afternoon:**
- [ ] COLMAP GPU worker Flask server tested in Colab
- [ ] ngrok tunnel from Colab exposed to local FastAPI backend
- [ ] POST /api/scan proxies to GPU worker
- [ ] GET /api/scan/status polling + ScanProgress UI stages
- [ ] Fallback logic: if COLMAP fails → run Claude Vision path
- [ ] Confidence banner in UI: "Metric accuracy" vs "Approximate"

**Evening:**
- [ ] Full end-to-end demo run: video → COLMAP scan → correct → design → shop
- [ ] Verify demo fallback SceneScript works if scan fails during demo
- [ ] Polish: loading states, error messages, all edge cases handled
- [ ] Presentation flow prepared

---

## 16. What to Skip and When to Add It

| Item | Skip Why | Add When |
|---|---|---|
| MiDaS | Depth Anything V2 is strictly better | Never — Depth Anything replaces it |
| YOLO | GroundingDINO is better for open-vocab room objects | Never — DINO replaces it |
| Dense MVS (COLMAP) | Sparse SfM is enough for room layout | Post-hackathon if higher mesh quality needed |
| MASt3R / VGGT | Cutting-edge, unstable APIs, hard to install | Post-hackathon when stable |
| Drag-and-drop objects | Complex Three.js DragControls + sync | Post-hackathon v1 |
| User accounts + DB | No persistence needed for demo | Post-hackathon v1 |
| Photorealistic rendering | GLTF + lighting is sufficient | Future |
| Mobile native app | Web is sufficient for demo | Future |
| Real-time collaboration | Out of scope | Future |
| Direct checkout | Affiliate links are enough | Post-hackathon v1 |
| NeRF / 3D Gaussian Splatting | Photorealistic but not interactive furniture layout | Future, separate product |

---

## 17. Demo Fallback SceneScript

Load this immediately if video scan fails during the presentation.
It represents a standard living room and works with all agent + shop features.

```json
{
  "version": 1,
  "session_id": "demo",
  "source": "demo",
  "room": { "width": 4.5, "depth": 5.5, "height": 2.8 },
  "walls": [
    { "id": "wall_north", "x1": 0,   "z1": 0,   "x2": 4.5, "z2": 0   },
    { "id": "wall_south", "x1": 0,   "z1": 5.5, "x2": 4.5, "z2": 5.5 },
    { "id": "wall_east",  "x1": 4.5, "z1": 0,   "x2": 4.5, "z2": 5.5 },
    { "id": "wall_west",  "x1": 0,   "z1": 0,   "x2": 0,   "z2": 5.5 }
  ],
  "windows": [
    { "id": "win_001", "wall": "wall_north", "x": 1.4, "width": 1.2,
      "height": 1.1, "sill_height": 0.9, "detected_by": "demo" }
  ],
  "doors": [
    { "id": "door_001", "wall": "wall_west", "x": 0.5,
      "width": 0.9, "height": 2.1, "detected_by": "demo" }
  ],
  "objects": [
    { "id": "obj_001", "type": "sofa",
      "position": { "x": 1.2, "y": 0.0, "z": 0.6 },
      "size": { "w": 2.2, "h": 0.85, "d": 0.9 },
      "rotation_y": 0, "color": "grey", "detection_confidence": 1.0,
      "product_url": null, "product_name": null },
    { "id": "obj_002", "type": "coffee_table",
      "position": { "x": 1.5, "y": 0.0, "z": 1.8 },
      "size": { "w": 1.0, "h": 0.45, "d": 0.6 },
      "rotation_y": 0, "color": "brown", "detection_confidence": 1.0,
      "product_url": null, "product_name": null },
    { "id": "obj_003", "type": "tv_unit",
      "position": { "x": 2.0, "y": 0.0, "z": 4.9 },
      "size": { "w": 1.6, "h": 0.5, "d": 0.45 },
      "rotation_y": 0, "color": "black", "detection_confidence": 1.0,
      "product_url": null, "product_name": null },
    { "id": "obj_004", "type": "armchair",
      "position": { "x": 3.5, "y": 0.0, "z": 0.8 },
      "size": { "w": 0.8, "h": 0.85, "d": 0.8 },
      "rotation_y": 270, "color": "beige", "detection_confidence": 1.0,
      "product_url": null, "product_name": null },
    { "id": "obj_005", "type": "plant",
      "position": { "x": 4.1, "y": 0.0, "z": 0.4 },
      "size": { "w": 0.4, "h": 1.0, "d": 0.4 },
      "rotation_y": 0, "color": "green", "detection_confidence": 1.0,
      "product_url": null, "product_name": null },
    { "id": "obj_006", "type": "bookshelf",
      "position": { "x": 4.1, "y": 0.0, "z": 2.5 },
      "size": { "w": 0.8, "h": 1.8, "d": 0.3 },
      "rotation_y": 90, "color": "white", "detection_confidence": 1.0,
      "product_url": null, "product_name": null }
  ],
  "metadata": {
    "room_type": "living_room", "style": null,
    "pipeline_version": "demo", "confidence": "demo",
    "created_at": "2025-01-01T00:00:00Z",
    "last_edited": "2025-01-01T00:00:00Z"
  }
}
```

---

## 18. Post-Hackathon Roadmap

### v1 — 2–4 weeks post-hackathon
- Full COLMAP + Depth Anything + DINO + SAM + Open3D on dedicated GPU server
- Persistent storage: PostgreSQL + Redis
- User accounts (NextAuth.js)
- Save + share room designs (unique URL)
- Drag-and-drop object movement in Three.js
- Direct affiliate links: IKEA, Amazon, Castlery

### v2 — 1–3 months
- MASt3R or VGGT integration if APIs stabilise (potentially replaces COLMAP)
- Dense mesh reconstruction (COLMAP MVS) for watertight room mesh
- 50+ GLTF furniture models with real retailer SKU mapping
- Style presets with one-click full room redesign
- Budget-constrained product search

### v3 — 3–6 months
- AR overlay mode: Three.js scene projected onto live camera
- Mobile web (touch controls for Three.js)
- AI-generated before/after visualisation renders
- Team collaboration: multi-user room editing

---

## 19. Final Summary

**The three-part architecture is unchanged:**
```
UNDERSTANDING  →  REPRESENTATION  →  RENDERING
  (CV Stack)       (SceneScript)      (Three.js)
```

**What changed from the old plan:**

The understanding layer is now real computer vision, not guesswork.

| Old Understanding Layer | New Understanding Layer |
|---|---|
| Claude Vision guesses positions from 2D images | COLMAP measures camera poses from video |
| Standard size lookup table for dimensions | Open3D measures real bounding boxes from point cloud |
| Approximate scale | Metric scale anchored to user-provided room dimensions |
| Claude guesses labels | GroundingDINO detects with open-vocabulary text prompts |
| No segmentation | SAM provides pixel-perfect object masks |
| No depth | Depth Anything V2 provides dense per-pixel metric depth |

**Claude's repositioned role:** Semantic brain and design agent only.
Claude receives structured geometry data and returns labels and actions.
Claude never estimates positions, depths, or sizes. Those jobs belong to CV tools.

**The SceneScript format is stable across both pipelines.** Whether the scene was
produced by COLMAP or by the Claude Vision fallback, the SceneScript looks identical.
All UI, agent, and shop code works on both. This is the key design decision that
makes the hybrid hackathon strategy work.

> **The SceneScript is the memory. COLMAP measures the room. GroundingDINO names
> the objects. Open3D places them. Claude redesigns them. Three.js shows them.
> The hover-to-shop layer makes them buyable. Build the SceneScript first.
> Build the demo fallback second. Build everything else in order.**

---

*AI-Powered 3D Room Design System — Proper CV Stack Implementation Plan — 2025*

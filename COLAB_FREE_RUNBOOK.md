# Colab Free Runbook (Milestone 1 + Milestone 2 Minimal)

Date: 2026-03-27

This runbook is for your current project state where Milestone 1 (frame extraction + COLMAP + alignment) and Milestone 2 minimal extraction are implemented in code, and heavier processing should run on a free GPU environment.

## 1) What is already implemented in this repo

Implemented locally:
- Full project scaffolding (frontend + backend + gpu_worker + shared)
- SceneScript schema + backend scene validation
- Precomputed scene loading flow (`/api/load_precomputed`)
- Milestone 1 offline pipeline code:
  - `gpu_worker/pipeline/frame_extractor.py`
  - `gpu_worker/pipeline/colmap_runner.py`
  - `gpu_worker/pipeline/colmap_aligner.py`
  - `gpu_worker/pipeline/offline_m1_pipeline.py`
- Milestone 2 minimal offline pipeline code:
  - `gpu_worker/pipeline/depth_estimator.py`
  - `gpu_worker/pipeline/object_detector.py`
  - `gpu_worker/pipeline/object_instances.py`
  - `gpu_worker/pipeline/object_fusion.py`
  - `gpu_worker/pipeline/geometry_fusion.py`
  - `gpu_worker/pipeline/opening_extractor.py`
  - `gpu_worker/pipeline/offline_m2_pipeline.py`

Not implemented yet:
- Full heavy-model stack (Depth Anything + GroundingDINO + SAM)
- Live backend proxy to Colab worker endpoints

## 2) Why Colab Free is the right next step

Your local machine should avoid heavy CV workloads. Colab Free provides temporary GPU sessions and enough resources for Milestone 1 experiments.

Trade-offs on Colab Free:
- Session can disconnect.
- Runtime storage is ephemeral.
- GPU availability can vary.

Mitigation:
- Save artifacts to Google Drive at end of each run.
- Keep runs short (30-80 frames).

## 3) What you need to do now (exact steps)

### Step A: Create a Colab notebook
1. Open Colab.
2. Runtime -> Change runtime type -> GPU.
3. Add these cells.

### Step B: Install dependencies
```python
import sys
print(sys.version)

!pip install -q --upgrade pip

# IMPORTANT: Do NOT downgrade numpy on Colab (it breaks many preinstalled packages).
# Install only what this pipeline needs and keep Colab's default numpy.
!pip install -q "open3d==0.19.0"

# Colab Python 3.12 uses pycolmap 3.x/4.x wheels, not 0.x
!pip install -q "pycolmap==3.12.6"

# If cv2 import fails, install opencv headless compatible with Colab runtime:
# !pip install -q "opencv-python-headless>=4.13,<4.14"

# Verify imports
import numpy as np
import cv2
import open3d as o3d
import pycolmap
print("ok", np.__version__, cv2.__version__, o3d.__version__, pycolmap.__version__)
```

If install still fails, run this fallback once:
```python
!pip install -q --upgrade pip setuptools wheel
!pip install -q "open3d==0.19.0"
!pip install -q "pycolmap==3.12.6"
```

If `pycolmap==3.12.6` is unavailable in your runtime, run:
```python
!pip install -q "pycolmap>=3.10,<4.1"
```

If you still see dependency conflict warnings about `jax`, `cupy`, `pytensor`, etc.
but the final import check prints `ok ...`, you can continue.
Those warnings are about unrelated preinstalled Colab packages and do not block this pipeline.

### Step C: Pull your project code into Colab
Option 1 (recommended): upload project zip from your machine and unzip.

```python
from google.colab import files
uploaded = files.upload()  # upload repo zip
```

```python
!unzip -q mansara.zip -d /content/
!ls /content/mansara/gpu_worker/pipeline
```

Option 2: git clone if your repo is hosted.

### Step D: Upload room video to Colab
```python
from google.colab import files
video = files.upload()  # upload one room video mp4

# Capture exact uploaded filename and build absolute path
video_filename = next(iter(video.keys()))
video_path = f"/content/{video_filename}"
print("Uploaded video:", video_filename)
print("Resolved path:", video_path)
```

### Step E: Run Milestone 1 pipeline
```python
import os
import sys

repo = "/content/mansara"
os.chdir(repo)
sys.path.append(os.path.join(repo, "gpu_worker", "pipeline"))

from offline_m1_pipeline import run_m1_pipeline

# Safety check before running pipeline
from pathlib import Path
print("Video exists:", Path(video_path).exists(), video_path)

summary = run_m1_pipeline(
  video_path=video_path,
    output_dir="/content/m1_outputs/session_001",
    room_width=4.5,
    room_depth=5.2,
    interval_sec=1.0,
    max_frames=80,
    min_sharpness=50.0,
    use_gpu=True,
)

summary
```

If you uploaded the video in a different cell and lost variable state, run:
```python
!ls -lah /content | head -n 50
```
Then set manually, for example:
```python
video_path = "/content/Room_video.mp4"
```

If you get `NameError: name 'video_path' is not defined`, run this first:
```python
from pathlib import Path

# Try to auto-detect a likely uploaded video file in /content
video_candidates = []
for ext in ("*.mp4", "*.mov", "*.avi", "*.webm", "*.mkv"):
  video_candidates.extend(Path("/content").glob(ext))

if not video_candidates:
  raise FileNotFoundError("No video found in /content. Upload the video again first.")

# Use the most recently modified video
video_candidates = sorted(video_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
video_path = str(video_candidates[0])
print("Auto-selected video_path:", video_path)
```

### Step E.1: If you get `AttributeError: ... SiftExtractionOptions ... use_gpu`
This happens when Colab has a newer `pycolmap` API and your local uploaded file is older.

Do this exactly:
1. Re-zip your latest local `mansara` project and re-upload it.
2. In Colab, clear old code and unzip again:
```python
!rm -rf /content/mansara
!unzip -q mansara.zip -d /content/
```
3. Reload modules before running the pipeline:
```python
import os
import sys
import importlib

repo = "/content/mansara"
os.chdir(repo)
sys.path.append(os.path.join(repo, "gpu_worker", "pipeline"))

import colmap_runner
import offline_m1_pipeline
importlib.reload(colmap_runner)
importlib.reload(offline_m1_pipeline)

from offline_m1_pipeline import run_m1_pipeline
```

Then run Step E again.

Fast option (no full re-zip/re-upload):
1. Upload only `gpu_worker/pipeline/colmap_runner.py` from your laptop.
2. Replace file in Colab and reload modules:
```python
from google.colab import files
import shutil

uploaded = files.upload()  # choose only colmap_runner.py
shutil.copy("colmap_runner.py", "/content/mansara/gpu_worker/pipeline/colmap_runner.py")
print("Updated colmap_runner.py")

import os, sys, importlib
repo = "/content/mansara"
os.chdir(repo)
sys.path.append(os.path.join(repo, "gpu_worker", "pipeline"))

import colmap_runner, offline_m1_pipeline
importlib.reload(colmap_runner)
importlib.reload(offline_m1_pipeline)

from offline_m1_pipeline import run_m1_pipeline
print("Reloaded modules")
```

If you get CUDA/SIFT error like `Cannot use Sift GPU without CUDA support`, run Step E with:
```python
use_gpu=False
```

### Step F: Inspect quality gate
```python
import json
p = "/content/m1_outputs/session_001/m1_summary.json"
print(json.dumps(json.load(open(p)), indent=2))
```

Check these fields:
- `alignment.pipeline_tier`
- `colmap.registration_ratio`
- `colmap.num_sparse_points`

### Step G: Download outputs to local machine
```python
from google.colab import files
!cd /content/m1_outputs && zip -qr m1_outputs.zip .
files.download('/content/m1_outputs/m1_outputs.zip')
```

### Step H: Run Milestone 2 minimal pipeline
```python
import os
import sys

repo = "/content/mansara"
os.chdir(repo)
sys.path.append(os.path.join(repo, "gpu_worker", "pipeline"))

from offline_m2_pipeline import run_m2_pipeline

m2_result = run_m2_pipeline(
  m1_output_dir="/content/m1_outputs/session_001",
  summary_path="/content/m1_outputs/session_001/m1_summary.json",
  aligned_payload_path="/content/m1_outputs/session_001/m1_aligned_payload.json",
  output_path="/content/m1_outputs/session_001/m2_result.json",
)

print("objects", len(m2_result.get("objects", [])))
print("windows", len(m2_result.get("windows", [])))
print("doors", len(m2_result.get("doors", [])))
print("diagnostics", m2_result.get("diagnostics", {}))
```

### Step I: Download M2 result
```python
from google.colab import files
files.download('/content/m1_outputs/session_001/m2_result.json')
```

## 4) How to use Colab outputs in your app now

1. Extract `m1_outputs.zip` locally.
2. Keep `m1_summary.json` and `m1_aligned_payload.json`.
3. Import directly using:
  - `POST /api/load_m1`
  - body: `session_id`, `summary_path`, `aligned_payload_path`
4. Frontend home page now has "Load M1 Output" fields to call this endpoint.
5. For M2 import, use:
  - `POST /api/load_m2`
  - body: `session_id`, `summary_path`, `aligned_payload_path`, `m2_result_path`
6. Frontend home page now has "Load M2 Output" and an `M2 result path` field.

## 5) Recommended free workflow

- Use Colab for M1 processing only.
- Download artifacts immediately after each run.
- Keep local frontend/backend running for UI and agent experiments.
- Repeat scans until `pipeline_tier` reaches `metric` or `partial` with acceptable registration ratio.

## 6) What will be built next in code

Immediate next engineering tasks:
1. Add optional Colab worker HTTP mode (ngrok) for semi-live processing.
2. Upgrade M2 from minimal CV heuristics to heavy-model detections/segmentation.

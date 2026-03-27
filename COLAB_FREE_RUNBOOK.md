# Colab Free Runbook From Scratch (M1 + M2 Minimal)

Date: 2026-03-28

This runbook is a clean, start-to-finish process for running Milestone 1 and Milestone 2 minimal in Google Colab, then importing outputs into the local app.

## 0) What You Will Do

1. Open Colab and enable GPU.
2. Install dependencies.
3. Upload project zip and unzip correctly.
4. Upload a room video (manual step).
5. Run M1 pipeline.
6. Run M2 pipeline.
7. Download output JSON files.
8. Import files in local frontend using Load M2 Output.

## 1) Video File You Should Upload

Use these recommended settings for best results.

- File type: mp4 (recommended)
- Video codec: H.264 (AVC)
- Duration: 20 to 45 seconds
- Resolution: 720p or 1080p
- Orientation: landscape
- Motion: slow walk, no fast panning
- Lighting: bright and stable
- Overlap: high overlap between consecutive views

Accepted formats in pipeline: mp4, mov, avi, webm, mkv.

If your file is very large, transcode in Colab before running M1.

## 2) Manual Work You Must Do

These steps are manual and cannot be automated by the pipeline.

- Manual step A: In Colab, Runtime -> Change runtime type -> GPU.
- Manual step B: Upload mansara.zip from your machine.
- Manual step C: Upload your room video from your machine.
- Manual step D: After processing, download generated JSON files.
- Manual step E: In local web app, paste local file paths and click Load M2 Output.

## 3) Colab Steps (Copy-Paste Cells)

### Step 1: Verify runtime and install dependencies

```python
import sys
print(sys.version)

!pip install -q --upgrade pip
!pip install -q "open3d==0.19.0"
!pip install -q "pycolmap==3.12.6"

import numpy as np
import cv2
import open3d as o3d
import pycolmap
print("ok", np.__version__, cv2.__version__, o3d.__version__, pycolmap.__version__)
```

If pycolmap exact version is not available:

```python
!pip install -q "pycolmap>=3.10,<4.1"
```

### Step 2: Upload project zip and extract cleanly

```python
from google.colab import files
uploaded = files.upload()  # choose mansara.zip
```

```python
# Overwrite without interactive prompts
!rm -rf /content/mansara /content/mansara-main
!unzip -oq mansara.zip -d /content/
!find /content -maxdepth 6 -type d -path "*/gpu_worker/pipeline"
```

### Step 3: Set repo path and import pipeline modules

```python
import os
import sys
from pathlib import Path

repo = "/content/mansara"
os.chdir(repo)
sys.path.append(str(Path(repo) / "gpu_worker" / "pipeline"))

from offline_m1_pipeline import run_m1_pipeline
from offline_m2_pipeline import run_m2_pipeline

print("Imports ok")
```

### Step 4: Upload video and create video_path

```python
from google.colab import files
from pathlib import Path

video_upload = files.upload()  # upload your room video
video_filename = next(iter(video_upload.keys()))
video_path = f"/content/{video_filename}"
print("video_path:", video_path, "exists:", Path(video_path).exists())
```

### Step 5: Optional transcode to lighter file (recommended)

```python
# Keeps quality useful for SfM but reduces heavy decode/IO
!ffmpeg -y -i "$video_path" -vf "scale='min(1280,iw)':-2,fps=12" -c:v libx264 -preset veryfast -crf 26 -an /content/video_m1.mp4

video_path = "/content/video_m1.mp4"
!ls -lh "$video_path"
```

### Step 6: Run M1 pipeline

```python
import time

# Important: clean old output folder so previous frames do not accumulate
!rm -rf /content/m1_outputs/session_001

t0 = time.time()
summary = run_m1_pipeline(
    video_path=video_path,
    output_dir="/content/m1_outputs/session_001",
    room_width=4.5,
    room_depth=5.2,
    interval_sec=0.6,
    max_frames=45,
    min_sharpness=6.0,
    use_gpu=True,
)
print("M1 done in sec:", round(time.time() - t0, 1))
summary
```

### Step 7: Run M2 pipeline

```python
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

### Step 8: Download output files

```python
from google.colab import files

files.download("/content/m1_outputs/session_001/m1_summary.json")
files.download("/content/m1_outputs/session_001/m1_aligned_payload.json")
files.download("/content/m1_outputs/session_001/m2_result.json")
```

Optional single zip:

```python
!cd /content/m1_outputs && zip -qr m1_outputs_session_001.zip session_001
from google.colab import files
files.download("/content/m1_outputs/m1_outputs_session_001.zip")
```

## 4) Import Into Local App

In local frontend home page:

1. Fill M1 summary path with local m1_summary.json path.
2. Fill M1 aligned payload path with local m1_aligned_payload.json path.
3. Fill M2 result path with local m2_result.json path.
4. Click Load M2 Output.

Backend endpoint used: POST /api/load_m2.

## 5) Rerun With A New Video

You do not need to restart everything every run.

For each new run:

1. Upload new video.
2. Use a new output folder, for example /content/m1_outputs/session_002.
3. Use a new Session ID in app to avoid mixing history.

Example change for new run:

- output_dir: /content/m1_outputs/session_002
- m2 output: /content/m1_outputs/session_002/m2_result.json

## 6) When To Restart Or Delete

No restart needed:

- New video, same notebook session.
- New M1 and M2 run with new output folder.

Restart Colab runtime only if:

- Imports break repeatedly.
- Kernel is unstable or out of memory.
- You changed core dependency versions and state got inconsistent.

Delete folders only when needed:

- Delete a specific run folder before reusing same session name.
- Keep old runs if you want history.

## 7) Common Problems And Fixes

### Problem: No video found in /content

Cause:

- Video not uploaded, or runtime restarted and files were wiped.

Fix:

- Upload video again using files.upload.
- Rebuild video_path.

### Problem: NameError video_path is not defined

Cause:

- Cell order issue after restart.

Fix:

- Re-run Step 4 to define video_path.

### Problem: ModuleNotFoundError offline_m1_pipeline

Cause:

- repo path not appended to sys.path.

Fix:

- Re-run Step 3 exactly.

### Problem: unzip asks replace y n A N r

Cause:

- Existing files and unzip without overwrite flag.

Fix:

- Use unzip -oq and remove old folder first.

### Problem: Too few usable frames extracted

Cause:

- Blurry or dark video, strict sharpness threshold.

Fix:

- Capture slower video with better lighting.
- Lower min_sharpness to 3.0 to 6.0.
- Lower interval_sec to 0.35 to sample more frames.

### Problem: M1 takes too long

Cause:

- Too many frames, heavy video, or old frames accumulated from previous run.

Fix:

- Clean output folder before run.
- Use transcode step.
- Use interval_sec 0.6 to 0.8 and max_frames 30 to 45.

### Problem: GPU looks idle in nvidia-smi

Cause:

- Parts of pipeline are CPU-heavy (mapping and optimization).

Fix:

- This can be normal. Focus on completion and output quality.

## 8) Current Scope

Implemented:

- M1 offline pipeline
- M2 minimal offline pipeline
- Backend /api/load_m1 and /api/load_m2 import flow
- Frontend M1 and M2 loaders

Not implemented yet:

- Full heavy model stack (Depth Anything + GroundingDINO + SAM)
- Live backend proxy to remote worker

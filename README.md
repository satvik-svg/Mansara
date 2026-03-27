# Room Design AI - Local Run Guide

This guide explains how to run backend and frontend locally, then import Milestone 1 and Milestone 2 (Colab) outputs.

## 1. Prerequisites

- Windows PowerShell
- Node.js and npm installed
- Python 3.11 virtual environment available at `.venv311`

## 2. Start Backend (FastAPI)

Open a PowerShell terminal in project root:

```powershell
cd C:\Users\sriva\mansara
cd C:\Users\sriva\mansara
Push-Location backend
..\.venv311\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend URL:
- http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/health

## 3. Start Frontend (Next.js)

Open a second PowerShell terminal in project root:

```powershell
cd C:\Users\sriva\mansara
Push-Location frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Frontend URL:
- http://127.0.0.1:3000

## 4. Import Your Colab Outputs (M1)

After downloading and extracting `m1_outputs.zip`, keep these files:
- `m1_summary.json`
- `m1_aligned_payload.json`

Open frontend at http://127.0.0.1:3000 and on the home page:
1. Enter a Session ID (any string, for example `session-001`)
2. Fill `M1 summary path` with your local absolute path to `m1_summary.json`
3. Fill `M1 aligned payload path` with your local absolute path to `m1_aligned_payload.json`
4. Click `Load M1 Output`

If successful, the app moves to correction flow with imported scene data.

## 5. Run and Import Milestone 2 (Minimal Offline)

After M1 artifacts are available in Colab, run:

```python
import os
import sys

repo = "/content/mansara"
os.chdir(repo)
sys.path.append(os.path.join(repo, "gpu_worker", "pipeline"))

from offline_m2_pipeline import run_m2_pipeline

m2 = run_m2_pipeline(
  m1_output_dir="/content/m1_outputs/session_001",
  summary_path="/content/m1_outputs/session_001/m1_summary.json",
  aligned_payload_path="/content/m1_outputs/session_001/m1_aligned_payload.json",
  output_path="/content/m1_outputs/session_001/m2_result.json",
)

print("M2 objects:", len(m2.get("objects", [])))
print("M2 windows:", len(m2.get("windows", [])))
print("M2 doors:", len(m2.get("doors", [])))
```

Then in frontend home page:
1. Fill `M1 summary path`
2. Fill `M1 aligned payload path`
3. Fill `M2 result path`
4. Click `Load M2 Output`

The backend route `POST /api/load_m2` merges M1 room geometry with M2 objects/openings and validates the final SceneScript.

### 4.1 Interpreting M1 Results

- If your scan quality is low, the backend now returns warnings and the correction page shows pipeline status.
- Typical warnings:
  - Very low registration ratio
  - Too few sparse points
  - Too few camera poses
- In those cases, room fallback defaults are used and object list may be empty.
- You can still continue in design mode and add objects manually using agent commands like `Add sofa`.

To improve scan quality for the next run:
- Walk slower with smoother camera motion
- Ensure better lighting
- Keep higher overlap between consecutive views
- Capture 30-45s video around full room perimeter

## 6. Optional API Import (without UI)

You can import directly with API:

Endpoint:
- POST `http://127.0.0.1:8000/api/load_m1`

JSON body:

```json
{
  "session_id": "session-001",
  "summary_path": "C:/path/to/m1_summary.json",
  "aligned_payload_path": "C:/path/to/m1_aligned_payload.json"
}
```

M2 endpoint:
- POST `http://127.0.0.1:8000/api/load_m2`

```json
{
  "session_id": "session-001",
  "summary_path": "C:/path/to/m1_summary.json",
  "aligned_payload_path": "C:/path/to/m1_aligned_payload.json",
  "m2_result_path": "C:/path/to/m2_result.json"
}
```

## 7. Stop Servers

In each terminal, press `Ctrl + C`.

## 8. Current Status

Implemented:
- M1 pipeline (frame extraction + COLMAP + alignment)
- M1 import endpoint and frontend loader
- M2 minimal pipeline (lightweight depth + contour detections + 3D lifting + fusion)
- M2 import endpoint and frontend loader

Not yet implemented:
- Full M2 heavy stack (Depth + DINO + SAM + object fusion)
- Live backend proxy to cloud worker

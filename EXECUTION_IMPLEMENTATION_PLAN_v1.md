# Execution Implementation Plan v1

Date: 2026-03-27
Source inputs:
- PROPER_IMPLEMENTATION_PLAN.md
- CORRECTED_IMPLEMENTATION_PLAN_v3.md

## 1) Goal
Build a working Room Design AI system in the correct order:
1. Geometry and SceneScript quality first
2. Interactive 3D UI second
3. Agent actions third
4. Shopping features after geometry is stable

This plan follows the corrected architecture and explicitly avoids high-risk shortcuts that were flagged in the corrected document.

## 2) Ground Rules
- Source of truth schema: SceneScript v2 with per-field confidence.
- Development mode first: offline precomputed scenes.
- Live GPU worker integration only after offline flow is stable.
- Window/door detection is optional and confidence-scored.
- If reconstruction quality is poor, pipeline tier must be marked as partial or approximate.

## 3) Delivery Strategy

### Phase A (implemented now): Foundation + offline workflow
Deliverables:
- Monorepo structure with frontend, backend, gpu_worker, shared
- FastAPI backend with baseline routers
- Session memory with version history and undo
- SceneScript v2 model + JSON schema file
- Precomputed scene loading endpoint
- Demo fallback SceneScript
- Frontend shell for upload, scan, correction, design pages
- Frontend API client + app store + confidence-aware object list

Outcome:
- End-to-end local demo is possible using precomputed scene JSON.
- UI and backend contract stabilize before heavy CV compute integration.

### Phase B: CV pipeline modules (offline execution)
Deliverables:
- Frame extraction module
- COLMAP execution and alignment stubs with proper conventions
- Depth estimation alignment skeleton
- DINO/SAM placeholders and object fusion interfaces
- Scene builder with confidence-aware normalization

Outcome:
- Pipeline contracts are implemented and testable with mock/precomputed outputs.

### Phase C: Live processing
Deliverables:
- GPU worker HTTP endpoint
- FastAPI proxy to worker
- Scan status reporting and stage progression
- Pipeline tier classification (metric/partial/approximate)

Outcome:
- Real upload-to-scan workflow.

## 4) Concrete Build Tasks

### Task Group 1: Repository scaffolding
- Create folders for frontend, backend, gpu_worker, shared.
- Create baseline configuration and dependency manifests.

### Task Group 2: Backend core
- Implement FastAPI app bootstrapping.
- Implement routers:
  - upload
  - scan (precomputed mode first)
  - scene
  - agent (stub action path)
  - undo
  - shop (stub)
- Implement services:
  - scene validation
  - scene builder placeholders
- Implement models:
  - SceneScript v2 pydantic models

### Task Group 3: Frontend core
- Build basic Next.js app routes:
  - /
  - /scan
  - /correct
  - /design
- Add store and API utility.
- Render confidence fields in correction list.

### Task Group 4: Shared contract and demo assets
- Add shared scene_schema.json.
- Add backend demo scene for immediate load.

### Task Group 5: Verification
- Run backend import/start check.
- Validate folder and file outputs.
- Confirm API contracts are wired at code level.

## 5) Non-Goals for this build pass
- Full CV model inference (COLMAP/Depth/SAM) running in this pass.
- Product marketplace production integration.
- Authentication and persistence database.

## 6) Risks and Mitigation
- Risk: Scope explosion from trying to implement all CV in one pass.
  - Mitigation: Lock to offline-first architecture and contracts now.
- Risk: Incorrect coordinate conventions later.
  - Mitigation: Keep dedicated alignment and conversion modules in gpu_worker pipeline.
- Risk: UI-agent churn due to unstable schema.
  - Mitigation: Freeze SceneScript v2 shape now and validate all scene writes.

## 7) What will be implemented right now
In this run, I will complete Phase A foundation fully:
- Create the project structure.
- Implement backend with real endpoints for upload/load_precomputed/get_scene/update_scene/undo.
- Add stubs for agent and shop to keep API complete.
- Add demo scene and schema.
- Create frontend app shell with routes and confidence-aware correction UI.

## 8) Completion Criteria for this run
- New plan file exists (this document).
- Backend app code exists and composes successfully.
- Frontend structure exists and compiles conceptually from code organization.
- Shared schema and demo scene exist.
- System can be demonstrated using precomputed scene loading path.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agent, scan, scene, shop, undo, upload

app = FastAPI(title="Room Design AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(scan.router)
app.include_router(scene.router)
app.include_router(agent.router)
app.include_router(undo.router)
app.include_router(shop.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

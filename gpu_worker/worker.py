"""Phase B GPU worker placeholder.

This worker is intentionally lightweight in Phase A. The endpoint contracts are
prepared so live integration can be added after offline pipeline validation.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health() -> tuple[dict, int]:
    return {"status": "ok"}, 200


@app.post("/process")
def process() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id", "unknown")
    return jsonify(
        {
            "session_id": session_id,
            "status": "not_implemented",
            "message": "Use offline precomputed mode in Phase A"
        }
    ), 501


if __name__ == "__main__":
    app.run(port=5000)

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field


@dataclass
class SessionState:
    scene: dict | None = None
    history: list[dict] = field(default_factory=list)
    room_width: float | None = None
    room_depth: float | None = None
    uploaded_video_path: str | None = None
    version: int = 0


class SessionStore:
    def __init__(self, max_history_versions: int = 20) -> None:
        self._max_history_versions = max_history_versions
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionState] = {}

    def create_empty(self, session_id: str, room_width: float, room_depth: float, video_path: str) -> None:
        with self._lock:
            self._sessions[session_id] = SessionState(
                scene=None,
                history=[],
                room_width=room_width,
                room_depth=room_depth,
                uploaded_video_path=video_path,
                version=0,
            )

    def create_from_scene(self, session_id: str, scene: dict) -> None:
        with self._lock:
            self._sessions[session_id] = SessionState(
                scene=copy.deepcopy(scene),
                history=[],
                version=1,
            )

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            state = self._sessions.get(session_id)
            return copy.deepcopy(state) if state else None

    def get_scene(self, session_id: str) -> dict | None:
        state = self.get(session_id)
        return state.scene if state else None

    def update_scene(self, session_id: str, new_scene: dict, push_history: bool = True) -> int:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("Session not found")

            state = self._sessions[session_id]
            if push_history and state.scene is not None:
                state.history.append(copy.deepcopy(state.scene))
                if len(state.history) > self._max_history_versions:
                    state.history.pop(0)

            state.scene = copy.deepcopy(new_scene)
            state.version += 1
            return state.version

    def undo(self, session_id: str) -> tuple[dict, int]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("Session not found")

            state = self._sessions[session_id]
            if not state.history:
                if state.scene is None:
                    raise ValueError("No scene available")
                return copy.deepcopy(state.scene), state.version

            previous_scene = state.history.pop()
            state.scene = previous_scene
            state.version = max(1, state.version - 1)
            return copy.deepcopy(state.scene), state.version


session_store = SessionStore(max_history_versions=20)

from pydantic import BaseModel


class AgentRequest(BaseModel):
    session_id: str
    instruction: str
    selected_object_id: str | None = None


class AgentResponse(BaseModel):
    action: dict
    scene: dict
    message: str

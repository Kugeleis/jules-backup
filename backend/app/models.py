from typing import Any, Optional
from pydantic import BaseModel


class PlanStep(BaseModel):
    id: int
    title: str
    details: Optional[str] = ""
    completed: bool = False
    completion_message: Optional[str] = None


class PlanState(BaseModel):
    raw_markdown: str = ""
    steps: list[PlanStep] = []
    current_step_id: Optional[int] = None


class Message(BaseModel):
    role: str  # system, user, assistant, tool
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class TaskItem(BaseModel):
    id: str
    title: str
    prompt: str
    status: str  # in_progress, waiting_for_user, completed, error
    workspace_path: Optional[str] = None
    plan_state: Optional[PlanState] = None
    waiting_for_user: bool = False
    pending_user_prompt: Optional[str] = None
    is_completed: bool = False
    submission_details: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class TaskCreateRequest(BaseModel):
    prompt: str
    workspace_path: Optional[str] = None
    title: Optional[str] = None


class TaskInitRequest(BaseModel):
    prompt: str
    workspace_path: Optional[str] = None
    model_provider: Optional[str] = "gemini"


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]


class UserResponseRequest(BaseModel):
    response: str

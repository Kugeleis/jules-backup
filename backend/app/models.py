from typing import Any

from pydantic import BaseModel


class PlanStep(BaseModel):
    id: int
    title: str
    details: str | None = ""
    completed: bool = False
    completion_message: str | None = None


class PlanState(BaseModel):
    raw_markdown: str = ""
    steps: list[PlanStep] = []
    current_step_id: int | None = None


class Message(BaseModel):
    role: str  # system, user, assistant, tool
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class TaskItem(BaseModel):
    id: str
    title: str
    prompt: str
    status: str  # in_progress, waiting_for_user, completed, error
    workspace_path: str | None = None
    plan_state: PlanState | None = None
    waiting_for_user: bool = False
    pending_user_prompt: str | None = None
    is_completed: bool = False
    submission_details: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class TaskCreateRequest(BaseModel):
    prompt: str
    workspace_path: str | None = None
    title: str | None = None


class TaskInitRequest(BaseModel):
    prompt: str
    workspace_path: str | None = None
    model_provider: str | None = "gemini"


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]


class UserResponseRequest(BaseModel):
    response: str

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


class TaskInitRequest(BaseModel):
    prompt: str
    workspace_path: str | None = None
    model_provider: str | None = "gemini"  # gemini, openai, anthropic, mock


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]


class UserResponseRequest(BaseModel):
    response: str

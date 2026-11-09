from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    id: int
    title: str
    details: Optional[str] = ""
    completed: bool = False
    completion_message: Optional[str] = None

class PlanState(BaseModel):
    raw_markdown: str = ""
    steps: List[PlanStep] = []
    current_step_id: Optional[int] = None

class Message(BaseModel):
    role: str # system, user, assistant, tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class TaskInitRequest(BaseModel):
    prompt: str
    workspace_path: Optional[str] = None
    model_provider: Optional[str] = "gemini" # gemini, openai, anthropic, mock

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class UserResponseRequest(BaseModel):
    response: str

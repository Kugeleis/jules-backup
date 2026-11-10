import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agent import TOOL_DEFINITIONS, JulesAgentEngine
from app.config import config
from app.db import TaskDatabase
from app.models import (
    TaskCreateRequest,
    TaskInitRequest,
    ToolCallRequest,
    UserResponseRequest,
)

app = FastAPI(title="Jules Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve default workspace root from config or environment
configured_ws = config.workspace.root
backend_dir = Path(__file__).resolve().parent.parent
default_workspace = os.environ.get(
    "WORKSPACE_ROOT",
    os.path.abspath(backend_dir / configured_ws),
)

db = TaskDatabase()
engine = JulesAgentEngine(default_workspace, db=db)


@app.get("/api/health")
def health_check():
    active_task = engine.get_active_task()
    return {
        "status": "ok",
        "workspace": engine.get_workspace_root(),
        "active_task_id": engine.active_task_id,
        "total_tasks": len(db.list_tasks()),
        "active_task_title": active_task.title if active_task else None,
    }


@app.get("/api/tools")
def list_tools():
    return {"tools": TOOL_DEFINITIONS}


# ----------------- Task History Management ----------------- #


@app.get("/api/tasks")
def get_tasks():
    tasks = db.list_tasks()
    return {
        "active_task_id": engine.active_task_id,
        "tasks": [t.model_dump() for t in tasks],
    }


@app.post("/api/tasks")
def create_task(req: TaskCreateRequest):
    task = engine.create_task(
        prompt=req.prompt,
        workspace_path=req.workspace_path,
        title=req.title,
    )
    return {
        "status": "created",
        "task": task.model_dump(),
        "active_task_id": engine.active_task_id,
    }


@app.get("/api/tasks/{task_id}")
def get_task_details(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    messages = db.get_messages(task_id)
    return {
        "task": task.model_dump(),
        "messages": [m.model_dump() for m in messages],
    }


@app.post("/api/tasks/{task_id}/activate")
def activate_task(task_id: str):
    task = engine.set_active_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "activated", "task": task.model_dump()}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    success = db.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    if engine.active_task_id == task_id:
        remaining = db.list_tasks()
        engine.active_task_id = remaining[0].id if remaining else None
    return {"status": "deleted", "active_task_id": engine.active_task_id}


# ----------------- Task Context Tool & User Actions ----------------- #


@app.post("/api/tasks/{task_id}/tool/execute")
async def execute_task_tool(task_id: str, req: ToolCallRequest):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result: dict[str, Any] = await engine.execute_tool_async(
        req.name, req.arguments, task_id=task_id
    )
    updated_task = db.get_task(task_id)
    return {
        "tool": req.name,
        "result": result,
        "task": updated_task.model_dump() if updated_task else None,
    }


@app.post("/api/tasks/{task_id}/user/reply")
def reply_to_task_user(task_id: str, req: UserResponseRequest):
    try:
        updated_task = engine.reply_to_user(req.response, task_id=task_id)
        return {"status": "received", "task": updated_task.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------- Active Task Compatibility Endpoints ----------------- #


@app.get("/api/state")
def get_state():
    active_task = engine.get_active_task()
    if not active_task:
        return {
            "workspace_root": engine.default_workspace_root,
            "plan_state": None,
            "waiting_for_user": False,
            "pending_user_prompt": None,
            "is_completed": False,
            "submission_details": None,
            "messages": [],
            "task_id": None,
        }
    messages = db.get_messages(active_task.id)
    return {
        "workspace_root": active_task.workspace_path or engine.default_workspace_root,
        "plan_state": active_task.plan_state.model_dump()
        if active_task.plan_state
        else None,
        "waiting_for_user": active_task.waiting_for_user,
        "pending_user_prompt": active_task.pending_user_prompt,
        "is_completed": active_task.is_completed,
        "submission_details": active_task.submission_details,
        "messages": [m.model_dump() for m in messages],
        "task_id": active_task.id,
        "title": active_task.title,
    }


@app.post("/api/task/init")
def init_task(req: TaskInitRequest):
    task = engine.create_task(prompt=req.prompt, workspace_path=req.workspace_path)
    return {
        "status": "initialized",
        "prompt": req.prompt,
        "task_id": task.id,
        "task": task.model_dump(),
    }


@app.post("/api/tool/execute")
async def execute_tool(req: ToolCallRequest):
    if not engine.active_task_id:
        engine.create_task(prompt="Ad-hoc tool execution")
    result: dict[str, Any] = await engine.execute_tool_async(
        req.name, req.arguments, task_id=engine.active_task_id
    )
    return {"tool": req.name, "result": result}


@app.post("/api/user/reply")
def reply_to_user(req: UserResponseRequest):
    try:
        updated = engine.reply_to_user(req.response, task_id=engine.active_task_id)
        return {"status": "received", "task": updated.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Mount static frontend
static_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../frontend/dist")
)
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


def main() -> None:
    import uvicorn

    host = (
        config.server.host
        if hasattr(config, "server") and hasattr(config.server, "host")
        else "0.0.0.0"
    )
    port = (
        config.server.port
        if hasattr(config, "server") and hasattr(config.server, "port")
        else 8000
    )
    uvicorn.run(app, host=host, port=port)

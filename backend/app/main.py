import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.models import TaskInitRequest, ToolCallRequest, UserResponseRequest
from backend.app.agent import JulesAgentEngine, TOOL_DEFINITIONS

app = FastAPI(title="Jules Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
engine = JulesAgentEngine(WORKSPACE_ROOT)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "workspace": engine.workspace_root}

@app.get("/api/tools")
def list_tools():
    return {"tools": TOOL_DEFINITIONS}

@app.get("/api/state")
def get_state():
    return {
        "workspace_root": engine.workspace_root,
        "plan_state": engine.plan_state,
        "waiting_for_user": engine.waiting_for_user,
        "pending_user_prompt": engine.pending_user_prompt,
        "is_completed": engine.is_completed,
        "submission_details": engine.submission_details,
        "messages": [m.dict() for m in engine.messages]
    }

@app.post("/api/task/init")
def init_task(req: TaskInitRequest):
    global engine
    if req.workspace_path:
        engine = JulesAgentEngine(req.workspace_path)
    engine.messages.append({
        "role": "user",
        "content": req.prompt
    })
    return {"status": "initialized", "prompt": req.prompt}

@app.post("/api/tool/execute")
async def execute_tool(req: ToolCallRequest):
    result = await engine.execute_tool_async(req.name, req.arguments)
    return {"tool": req.name, "result": result}

@app.post("/api/user/reply")
def reply_to_user(req: UserResponseRequest):
    if not engine.waiting_for_user:
        raise HTTPException(status_code=400, detail="Agent is not waiting for user input.")
    engine.waiting_for_user = False
    engine.pending_user_prompt = None
    engine.messages.append({
        "role": "user",
        "content": req.response
    })
    return {"status": "received", "message": req.response}

# Mount static frontend if available
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

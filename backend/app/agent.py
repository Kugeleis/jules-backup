import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from backend.app.models import Message, PlanState, PlanStep
from backend.app.tools import ToolExecutor
from backend.app.planner import parse_plan_markdown

TOOL_DEFINITIONS = [
    {
        "name": "list_files",
        "description": "Lists all files and directories under the given directory (defaults to repo root).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory path to list files from."}
            }
        }
    },
    {
        "name": "read_file",
        "description": "Reads the content of the specified file in the repo.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path of the file to read."}
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "write_file",
        "description": "Use this to create a new file or overwrite an existing file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path of the file to create or overwrite."},
                "content": {"type": "string", "description": "The content to write to the file."}
            },
            "required": ["filepath", "content"]
        }
    },
    {
        "name": "replace_with_git_merge_diff",
        "description": "Performs targeted search-and-replace to modify an existing file using conflict markers.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path of the file to modify."},
                "merge_diff": {"type": "string", "description": "The diff in Git merge diff format."}
            },
            "required": ["filepath", "merge_diff"]
        }
    },
    {
        "name": "run_in_bash_session",
        "description": "Runs the given bash command in the persistent shell session.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "set_plan",
        "description": "Use it to set or update the multi-step plan in Markdown format.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {"type": "string", "description": "The plan in Markdown format."}
            },
            "required": ["plan"]
        }
    },
    {
        "name": "plan_step_complete",
        "description": "Marks the current plan step as complete, with a message explaining what actions you took.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "A succinct descriptive message explaining what actions were taken."}
            },
            "required": ["message"]
        }
    },
    {
        "name": "pre_commit_instructions",
        "description": "Get instructions on pre commit checks needed before submitting.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "request_user_input",
        "description": "Asks the user a question or asks for input and waits for a response.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The question or prompt for the user."}
            },
            "required": ["message"]
        }
    },
    {
        "name": "message_user",
        "description": "Sends a message/update to the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to send."},
                "continue_working": {"type": "boolean", "description": "Whether to continue working immediately."}
            },
            "required": ["message", "continue_working"]
        }
    },
    {
        "name": "submit",
        "description": "Commits code changes and requests PR submission.",
        "parameters": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string"},
                "commit_message": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"}
            },
            "required": ["branch_name", "commit_message", "title", "description"]
        }
    }
]

class JulesAgentEngine:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.tools = ToolExecutor(workspace_root)
        self.plan_state: Optional[PlanState] = None
        self.messages: List[Message] = []
        self.waiting_for_user = False
        self.pending_user_prompt: Optional[str] = None
        self.is_completed = False
        self.submission_details: Optional[Dict[str, Any]] = None

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool execution synchronously or asynchronously."""
        if name == "list_files":
            return self.tools.list_files(args.get("path", ""))
        elif name == "read_file":
            return self.tools.read_file(args.get("filepath", ""))
        elif name == "write_file":
            return self.tools.write_file(args.get("filepath", ""), args.get("content", ""))
        elif name == "replace_with_git_merge_diff":
            return self.tools.replace_with_git_merge_diff(args.get("filepath", ""), args.get("merge_diff", ""))
        elif name == "delete_file":
            return self.tools.delete_file(args.get("filepath", ""))
        elif name == "rename_file":
            return self.tools.rename_file(args.get("filepath", ""), args.get("new_filepath", ""))
        elif name == "set_plan":
            raw = args.get("plan", "")
            self.plan_state = parse_plan_markdown(raw)
            return {"result": f"Plan updated with {len(self.plan_state.steps)} steps."}
        elif name == "plan_step_complete":
            msg = args.get("message", "")
            if self.plan_state and self.plan_state.current_step_id is not None:
                step = next((s for s in self.plan_state.steps if s.id == self.plan_state.current_step_id), None)
                if step:
                    step.completed = True
                    step.completion_message = msg
                next_step = next((s for s in self.plan_state.steps if not s.completed), None)
                self.plan_state.current_step_id = next_step.id if next_step else None
                return {"result": f"Step marked complete: {msg}"}
            return {"result": f"Marked complete: {msg}"}
        elif name == "pre_commit_instructions":
            return {
                "result": "Pre-commit checklist:\n"
                          "1. Run all repository test suites and linters.\n"
                          "2. Verify diffs are clean and no temporary files are left.\n"
                          "3. Complete code review and verification checks.\n"
                          "4. Call 'submit' tool when all checks pass."
            }
        elif name == "request_user_input":
            self.waiting_for_user = True
            self.pending_user_prompt = args.get("message", "")
            return {"result": "Waiting for user input..."}
        elif name == "message_user":
            return {"result": f"Message displayed to user: {args.get('message')}"}
        elif name == "submit":
            self.is_completed = True
            self.submission_details = args
            return {"result": f"Successfully submitted change to branch '{args.get('branch_name')}'."}
        else:
            return {"error": f"Unknown tool '{name}'"}

    async def execute_tool_async(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "run_in_bash_session":
            cmd = args.get("command", "")
            return await self.tools.run_in_bash(cmd)
        return self.execute_tool(name, args)

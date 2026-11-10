from typing import Any, Optional

from app.db import TaskDatabase
from app.models import Message, PlanStep, TaskItem
from app.planner import parse_plan_markdown
from app.tools import ToolExecutor

TOOL_DEFINITIONS = [
    {
        "name": "list_files",
        "description": "Lists all files and directories under the given directory (defaults to repo root).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list files from.",
                }
            },
        },
    },
    {
        "name": "read_file",
        "description": "Reads the content of the specified file in the repo.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "The path of the file to read.",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "write_file",
        "description": "Use this to create a new file or overwrite an existing file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "The path of the file to create or overwrite.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "replace_with_git_merge_diff",
        "description": "Performs targeted search-and-replace to modify an existing file using conflict markers.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "The path of the file to modify.",
                },
                "merge_diff": {
                    "type": "string",
                    "description": "The diff in Git merge diff format.",
                },
            },
            "required": ["filepath", "merge_diff"],
        },
    },
    {
        "name": "run_in_bash_session",
        "description": "Runs the given bash command in the persistent shell session.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."}
            },
            "required": ["command"],
        },
    },
    {
        "name": "set_plan",
        "description": "Use it to set or update the multi-step plan in Markdown format.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "The plan in Markdown format.",
                }
            },
            "required": ["plan"],
        },
    },
    {
        "name": "plan_step_complete",
        "description": "Marks the current plan step as complete, with a message explaining what actions you took.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A succinct descriptive message explaining what actions were taken.",
                }
            },
            "required": ["message"],
        },
    },
    {
        "name": "pre_commit_instructions",
        "description": "Get instructions on pre commit checks needed before submitting.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "request_user_input",
        "description": "Asks the user a question or asks for input and waits for a response.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The question or prompt for the user.",
                }
            },
            "required": ["message"],
        },
    },
    {
        "name": "message_user",
        "description": "Sends a message/update to the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to send."},
                "continue_working": {
                    "type": "boolean",
                    "description": "Whether to continue working immediately.",
                },
            },
            "required": ["message", "continue_working"],
        },
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
                "description": {"type": "string"},
            },
            "required": ["branch_name", "commit_message", "title", "description"],
        },
    },
]


class JulesAgentEngine:
    def __init__(self, default_workspace_root: str, db: Optional[TaskDatabase] = None):
        self.default_workspace_root: str = default_workspace_root
        self.db = db or TaskDatabase()
        self.active_task_id: Optional[str] = None

    def get_workspace_root(self, task_id: Optional[str] = None) -> str:
        tid = task_id or self.active_task_id
        if tid:
            task = self.db.get_task(tid)
            if task and task.workspace_path:
                return task.workspace_path
        return self.default_workspace_root

    def create_task(
        self,
        prompt: str,
        workspace_path: Optional[str] = None,
        title: Optional[str] = None,
    ) -> TaskItem:
        task = self.db.create_task(
            prompt=prompt,
            workspace_path=workspace_path or self.default_workspace_root,
            title=title,
        )
        self.active_task_id = task.id
        return task

    def get_active_task(self) -> Optional[TaskItem]:
        if not self.active_task_id:
            return None
        return self.db.get_task(self.active_task_id)

    @property
    def plan_state(self):
        active = self.get_active_task()
        return active.plan_state if active else None

    @property
    def waiting_for_user(self) -> bool:
        active = self.get_active_task()
        return active.waiting_for_user if active else False

    @property
    def pending_user_prompt(self) -> Optional[str]:
        active = self.get_active_task()
        return active.pending_user_prompt if active else None

    @property
    def is_completed(self) -> bool:
        active = self.get_active_task()
        return active.is_completed if active else False

    @property
    def submission_details(self) -> Optional[dict[str, Any]]:
        active = self.get_active_task()
        return active.submission_details if active else None

    @property
    def messages(self) -> list[Message]:
        if not self.active_task_id:
            return []
        return self.db.get_messages(self.active_task_id)

    def set_active_task(self, task_id: str) -> Optional[TaskItem]:
        task = self.db.get_task(task_id)
        if task:
            self.active_task_id = task.id
        return task

    def execute_tool(
        self, name: str, args: dict[str, Any], task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Dispatches tool execution synchronously within the task context."""
        tid = task_id or self.active_task_id
        workspace_root = self.get_workspace_root(tid)
        tools = ToolExecutor(workspace_root)
        task = self.db.get_task(tid) if tid else None

        if name == "list_files":
            return tools.list_files(args.get("path", ""))
        elif name == "read_file":
            return tools.read_file(args.get("filepath", ""))
        elif name == "write_file":
            return tools.write_file(args.get("filepath", ""), args.get("content", ""))
        elif name == "replace_with_git_merge_diff":
            return tools.replace_with_git_merge_diff(
                args.get("filepath", ""), args.get("merge_diff", "")
            )
        elif name == "delete_file":
            return tools.delete_file(args.get("filepath", ""))
        elif name == "rename_file":
            return tools.rename_file(
                args.get("filepath", ""), args.get("new_filepath", "")
            )
        elif name == "set_plan":
            raw = args.get("plan", "")
            new_plan = parse_plan_markdown(raw)
            if not tid:
                created = self.create_task(prompt="Plan execution")
                tid = created.id
            self.db.update_task(tid, plan_state=new_plan)
            self.db.add_message(
                tid,
                Message(
                    role="assistant",
                    content=f"Set execution plan with {len(new_plan.steps)} steps.",
                    tool_calls=[{"name": "set_plan", "arguments": args}],
                ),
            )
            return {"result": f"Plan updated with {len(new_plan.steps)} steps."}
        elif name == "plan_step_complete":
            msg = args.get("message", "")
            if task and task.plan_state and task.plan_state.current_step_id is not None:
                plan_state = task.plan_state
                step: Optional[PlanStep] = next(
                    (s for s in plan_state.steps if s.id == plan_state.current_step_id),
                    None,
                )
                if step:
                    step.completed = True
                    step.completion_message = msg
                next_step: Optional[PlanStep] = next(
                    (s for s in plan_state.steps if not s.completed), None
                )
                plan_state.current_step_id = next_step.id if next_step else None
                if tid:
                    self.db.update_task(tid, plan_state=plan_state)
                    self.db.add_message(
                        tid,
                        Message(
                            role="assistant",
                            content=f"Completed plan step: {msg}",
                            tool_calls=[
                                {"name": "plan_step_complete", "arguments": args}
                            ],
                        ),
                    )
                return {"result": f"Step marked complete: {msg}"}
            return {"result": f"Marked complete: {msg}"}
        elif name == "pre_commit_instructions":
            res = (
                "Pre-commit checklist:\n"
                "1. Run all repository test suites and linters.\n"
                "2. Verify diffs are clean and no temporary files are left.\n"
                "3. Complete code review and verification checks.\n"
                "4. Call 'submit' tool when all checks pass."
            )
            if tid:
                self.db.add_message(
                    tid,
                    Message(
                        role="tool",
                        name="pre_commit_instructions",
                        content=res,
                    ),
                )
            return {"result": res}
        elif name == "request_user_input":
            user_msg = args.get("message", "")
            if tid:
                self.db.update_task(
                    tid,
                    waiting_for_user=True,
                    pending_user_prompt=user_msg,
                    status="waiting_for_user",
                )
                self.db.add_message(
                    tid,
                    Message(
                        role="assistant",
                        content=user_msg,
                        tool_calls=[{"name": "request_user_input", "arguments": args}],
                    ),
                )
            return {"result": "Waiting for user input..."}
        elif name == "message_user":
            user_msg = args.get("message", "")
            if tid:
                self.db.add_message(
                    tid,
                    Message(
                        role="assistant",
                        content=user_msg,
                        tool_calls=[{"name": "message_user", "arguments": args}],
                    ),
                )
            return {"result": f"Message displayed to user: {user_msg}"}
        elif name == "submit":
            if tid:
                self.db.update_task(
                    tid,
                    is_completed=True,
                    status="completed",
                    submission_details=args,
                )
                self.db.add_message(
                    tid,
                    Message(
                        role="assistant",
                        content=f"Submitted task to branch '{args.get('branch_name')}'.",
                        tool_calls=[{"name": "submit", "arguments": args}],
                    ),
                )
            return {
                "result": f"Successfully submitted change to branch '{args.get('branch_name')}'."
            }
        else:
            return {"error": f"Unknown tool '{name}'"}

    async def execute_tool_async(
        self, name: str, args: dict[str, Any], task_id: Optional[str] = None
    ) -> dict[str, Any]:
        tid = task_id or self.active_task_id
        if name == "run_in_bash_session":
            workspace_root = self.get_workspace_root(tid)
            tools = ToolExecutor(workspace_root)
            cmd = args.get("command", "")
            res = await tools.run_in_bash(cmd)
            if tid:
                self.db.add_message(
                    tid,
                    Message(
                        role="tool",
                        name="run_in_bash_session",
                        content=f"$ {cmd}\n{res.get('output', '')}",
                    ),
                )
            return res
        return self.execute_tool(name, args, task_id=tid)

    def reply_to_user(
        self, response_text: str, task_id: Optional[str] = None
    ) -> TaskItem:
        tid = task_id or self.active_task_id
        if not tid:
            raise ValueError("No task specified or active.")
        task = self.db.get_task(tid)
        if not task:
            raise ValueError(f"Task '{tid}' not found.")
        if not task.waiting_for_user:
            raise ValueError("Task is not waiting for user input.")

        self.db.update_task(
            tid,
            waiting_for_user=False,
            pending_user_prompt=None,
            status="in_progress",
        )
        self.db.add_message(
            tid,
            Message(role="user", content=response_text),
        )
        return self.db.get_task(tid)  # type: ignore

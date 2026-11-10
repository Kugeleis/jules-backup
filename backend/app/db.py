import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from app.config import config
from app.models import Message, PlanState, TaskItem


def get_db_path() -> str:
    db_path = config.database.path
    if not os.path.isabs(db_path):
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        db_path = os.path.join(backend_dir, db_path)
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path


class TaskDatabase:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_db_path()
        self._shared_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    workspace_path TEXT,
                    plan_state TEXT,
                    waiting_for_user INTEGER DEFAULT 0,
                    pending_user_prompt TEXT,
                    is_completed INTEGER DEFAULT 0,
                    submission_details TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def create_task(
        self,
        prompt: str,
        workspace_path: str | None = None,
        title: str | None = None,
    ) -> TaskItem:
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now(UTC).isoformat()
        if not title:
            first_line = (
                prompt.strip().splitlines()[0] if prompt.strip() else "Untitled Task"
            )
            title = (first_line[:50] + "...") if len(first_line) > 50 else first_line

        task = TaskItem(
            id=task_id,
            title=title,
            prompt=prompt,
            status="in_progress",
            workspace_path=workspace_path,
            created_at=now,
            updated_at=now,
            waiting_for_user=False,
            is_completed=False,
        )

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, title, prompt, status, workspace_path, plan_state,
                    waiting_for_user, pending_user_prompt, is_completed,
                    submission_details, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.title,
                    task.prompt,
                    task.status,
                    task.workspace_path,
                    None,
                    0,
                    None,
                    0,
                    None,
                    task.created_at,
                    task.updated_at,
                ),
            )
            conn.execute(
                """
                INSERT INTO messages (task_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (task.id, "user", prompt, now),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

        return task

    def list_tasks(self) -> list[TaskItem]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            rows = cursor.fetchall()
            tasks: list[TaskItem] = []
            for r in rows:
                plan_state = json.loads(r["plan_state"]) if r["plan_state"] else None
                submission_details = (
                    json.loads(r["submission_details"])
                    if r["submission_details"]
                    else None
                )
                tasks.append(
                    TaskItem(
                        id=r["id"],
                        title=r["title"],
                        prompt=r["prompt"],
                        status=r["status"],
                        workspace_path=r["workspace_path"],
                        plan_state=PlanState(**plan_state) if plan_state else None,
                        waiting_for_user=bool(r["waiting_for_user"]),
                        pending_user_prompt=r["pending_user_prompt"],
                        is_completed=bool(r["is_completed"]),
                        submission_details=submission_details,
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return tasks
        finally:
            if self._shared_conn is None:
                conn.close()

    def get_task(self, task_id: str) -> TaskItem | None:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            r = cursor.fetchone()
            if not r:
                return None
            plan_state = json.loads(r["plan_state"]) if r["plan_state"] else None
            submission_details = (
                json.loads(r["submission_details"]) if r["submission_details"] else None
            )
            return TaskItem(
                id=r["id"],
                title=r["title"],
                prompt=r["prompt"],
                status=r["status"],
                workspace_path=r["workspace_path"],
                plan_state=PlanState(**plan_state) if plan_state else None,
                waiting_for_user=bool(r["waiting_for_user"]),
                pending_user_prompt=r["pending_user_prompt"],
                is_completed=bool(r["is_completed"]),
                submission_details=submission_details,
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
        finally:
            if self._shared_conn is None:
                conn.close()

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        plan_state: PlanState | None = None,
        waiting_for_user: bool | None = None,
        pending_user_prompt: str | None = None,
        is_completed: bool | None = None,
        submission_details: dict[str, Any] | None = None,
    ):
        now = datetime.now(UTC).isoformat()
        fields = ["updated_at = ?"]
        values: list[Any] = [now]

        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if plan_state is not None:
            fields.append("plan_state = ?")
            values.append(json.dumps(plan_state.model_dump()))
        if waiting_for_user is not None:
            fields.append("waiting_for_user = ?")
            values.append(1 if waiting_for_user else 0)
        if pending_user_prompt is not None:
            fields.append("pending_user_prompt = ?")
            values.append(pending_user_prompt)
        if is_completed is not None:
            fields.append("is_completed = ?")
            values.append(1 if is_completed else 0)
        if submission_details is not None:
            fields.append("submission_details = ?")
            values.append(json.dumps(submission_details))

        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"

        conn = self._get_connection()
        try:
            conn.execute(query, values)
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def delete_task(self, task_id: str) -> bool:
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._shared_conn is None:
                conn.close()

    def add_message(self, task_id: str, message: Message):
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO messages (task_id, role, content, tool_calls, tool_call_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    message.role,
                    message.content,
                    json.dumps(message.tool_calls) if message.tool_calls else None,
                    message.tool_call_id,
                    message.name,
                    now,
                ),
            )
            conn.execute(
                "UPDATE tasks SET updated_at = ? WHERE id = ?",
                (now, task_id),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def get_messages(self, task_id: str) -> list[Message]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE task_id = ? ORDER BY id ASC",
                (task_id,),
            )
            rows = cursor.fetchall()
            msgs: list[Message] = []
            for r in rows:
                tool_calls = json.loads(r["tool_calls"]) if r["tool_calls"] else None
                msgs.append(
                    Message(
                        role=r["role"],
                        content=r["content"],
                        tool_calls=tool_calls,
                        tool_call_id=r["tool_call_id"],
                        name=r["name"],
                    )
                )
            return msgs
        finally:
            if self._shared_conn is None:
                conn.close()

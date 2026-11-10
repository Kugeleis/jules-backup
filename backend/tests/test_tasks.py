from box import Box
from fastapi.testclient import TestClient

from app.agent import JulesAgentEngine
from app.config import config
from app.db import TaskDatabase
from app.main import app
from app.models import Message


def test_config_loading():
    assert isinstance(config, Box)
    assert hasattr(config, "database")
    assert hasattr(config, "workspace")
    assert hasattr(config, "server")
    assert config.database.path == "jules.db"


def test_task_database_crud(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = TaskDatabase(db_file)

    # Create task
    task = db.create_task(prompt="Build a calculator", title="Calc App")
    assert task.id is not None
    assert task.title == "Calc App"
    assert task.status == "in_progress"
    assert not task.waiting_for_user

    # List tasks
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == task.id

    # Messages
    msgs = db.get_messages(task.id)
    assert len(msgs) == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "Build a calculator"

    # Add assistant message
    db.add_message(task.id, Message(role="assistant", content="Plan drafted"))
    msgs = db.get_messages(task.id)
    assert len(msgs) == 2
    assert msgs[1].content == "Plan drafted"

    # Update task state
    db.update_task(
        task.id,
        status="waiting_for_user",
        waiting_for_user=True,
        pending_user_prompt="Confirm?",
    )
    updated = db.get_task(task.id)
    assert updated.status == "waiting_for_user"
    assert updated.waiting_for_user is True
    assert updated.pending_user_prompt == "Confirm?"

    # Persistence verification: reload from fresh DB instance
    db_reloaded = TaskDatabase(db_file)
    tasks_reloaded = db_reloaded.list_tasks()
    assert len(tasks_reloaded) == 1
    assert tasks_reloaded[0].id == task.id
    assert tasks_reloaded[0].status == "waiting_for_user"
    assert len(db_reloaded.get_messages(task.id)) == 2

    # Delete task
    assert db.delete_task(task.id) is True
    assert len(db.list_tasks()) == 0


def test_agent_multi_task_management(tmp_path):
    db_file = str(tmp_path / "agent_tasks.db")
    db = TaskDatabase(db_file)
    engine = JulesAgentEngine(str(tmp_path), db=db)

    task1 = engine.create_task(prompt="Task 1")
    task2 = engine.create_task(prompt="Task 2")
    assert engine.active_task_id == task2.id

    # Execute plan in task 2
    engine.execute_tool(
        "set_plan", {"plan": "1. *Step A*\n2. *Step B*"}, task_id=task2.id
    )
    t2 = db.get_task(task2.id)
    assert t2.plan_state is not None
    assert len(t2.plan_state.steps) == 2

    # Task 1 remains unaffected
    t1 = db.get_task(task1.id)
    assert t1.plan_state is None

    # Switch active task to task 1
    engine.set_active_task(task1.id)
    assert engine.active_task_id == task1.id
    assert engine.plan_state is None


def test_api_task_history_endpoints():
    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "total_tasks" in res.json()

    # 2. Create task
    res = client.post("/api/tasks", json={"prompt": "API Task 1", "title": "API Test"})
    assert res.status_code == 200
    task_id = res.json()["task"]["id"]

    # 3. List tasks
    res = client.get("/api/tasks")
    assert res.status_code == 200
    task_ids = [t["id"] for t in res.json()["tasks"]]
    assert task_id in task_ids

    # 4. Get specific task details
    res = client.get(f"/api/tasks/{task_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["task"]["id"] == task_id
    assert len(data["messages"]) >= 1

    # 5. Execute tool within task
    res = client.post(
        f"/api/tasks/{task_id}/tool/execute",
        json={"name": "request_user_input", "arguments": {"message": "Need input"}},
    )
    assert res.status_code == 200
    assert res.json()["task"]["status"] == "waiting_for_user"

    # 6. User reply to task
    res = client.post(
        f"/api/tasks/{task_id}/user/reply",
        json={"response": "Here is input"},
    )
    assert res.status_code == 200
    assert res.json()["task"]["status"] == "in_progress"

    # 7. Delete task
    res = client.delete(f"/api/tasks/{task_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

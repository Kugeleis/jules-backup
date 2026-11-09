import os
from typing import Any

from app.agent import JulesAgentEngine
from app.diff_utils import apply_git_merge_diff
from app.models import PlanState
from app.planner import parse_plan_markdown


def test_diff_engine():
    original = "line 1\nline 2\nline 3\n"
    diff = "<<<<<<< SEARCH\nline 2\n=======\nline 2 modified\n>>>>>>> REPLACE"
    success, updated, err = apply_git_merge_diff(original, diff)
    assert success
    assert "line 2 modified" in updated
    assert "line 1" in updated
    assert "line 3" in updated


def test_planner():
    md = """1. *Step one*\n   - Detail one\n2. *Step two*\n   - Detail two\n3. *Complete pre commit steps*\n4. *Submit the change.*"""
    state: PlanState = parse_plan_markdown(md)
    assert len(state.steps) == 4
    assert state.steps[0].title == "Step one"
    assert state.current_step_id == 1


def test_agent_tools(tmp_path):
    workspace = str(tmp_path)
    agent = JulesAgentEngine(workspace)

    # write file
    res: dict[str, Any] = agent.execute_tool("write_file", {"filepath": "hello.txt", "content": "world"})
    assert "error" not in res
    assert os.path.exists(os.path.join(workspace, "hello.txt"))

    # read file
    res: dict[str, Any] = agent.execute_tool("read_file", {"filepath": "hello.txt"})
    assert res.get("result") == "world"

    # list files
    res: dict[str, Any] = agent.execute_tool("list_files", {})
    assert "hello.txt" in res.get("result", [])

    # git merge diff
    diff = "<<<<<<< SEARCH\nworld\n=======\nearth\n>>>>>>> REPLACE"
    res: dict[str, Any] = agent.execute_tool("replace_with_git_merge_diff", {"filepath": "hello.txt", "merge_diff": diff})
    assert "error" not in res
    assert agent.execute_tool("read_file", {"filepath": "hello.txt"}).get("result") == "earth"

    # planning execution
    agent.execute_tool("set_plan", {"plan": "1. *Step 1*\n2. *Step 2*"})
    assert agent.plan_state is not None
    assert agent.plan_state.current_step_id == 1
    agent.execute_tool("plan_step_complete", {"message": "Done step 1"})
    assert agent.plan_state is not None
    assert agent.plan_state.current_step_id == 2
    assert agent.plan_state.steps[0].completed is True
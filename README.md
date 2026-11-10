# Jules Coding Agent - Full System Backup & Self-Hosting Guide

This repository contains the comprehensive backup, architecture specification, system prompt definitions, backend execution engine, and frontend user interface for **Jules** (Google's asynchronous coding agent).

---

## 📁 Repository Contents

- **`SYSTEM.md`**: Complete architectural breakdown, sandbox execution lifecycle, ReAct agent loop, and security model.
- **`PROMPTS.md`**: Verbatim system instructions, tool calling JSON schemas, planning guidelines, and Git merge diff format specifications.
- **`backend/`**:
  - `app/agent.py`: Agent engine orchestrating tool dispatch, planning state, and ReAct loop.
  - `app/tools.py`: Tool implementations (`run_in_bash_session`, `write_file`, `read_file`, `replace_with_git_merge_diff`, `list_files`, etc.).
  - `app/planner.py`: Multi-step Markdown plan parser and lifecycle tracker.
  - `app/diff_utils.py`: Git merge conflict marker diff parser and applier.
  - `app/main.py`: FastAPI server serving both API endpoints and the frontend dashboard.
  - `tests/`: Automated unit and integration tests for tools, planning, and diff handling.
- **`frontend/dist/`**: Single-Page Application dashboard featuring:
  - Plan step tracker with dynamic completion states.
  - Interactive activity & tool execution stream.
  - Real-time diff and file preview inspector.
- **`Dockerfile` & `docker-compose.yml`**: Full containerization setup for running the agent in an isolated sandbox.
- **`setup.sh`**: Quickstart automated setup script.

---

## 🚀 Quick Start (Local Run)

### Prerequisites

- Python 3.10+
- `pip`
- Git

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Run Tests

Verify that all tools and diff engines operate correctly:

```bash
PYTHONPATH=. pytest backend/tests
```

### 3. Launch Jules Agent Studio

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the Jules dashboard.

---

## 🐳 Running with Docker

Run Jules in a sandboxed, containerized environment:

```bash
docker compose up --build
```

The dashboard will be accessible at `http://localhost:8000`.

---

## ⚙️ Configuration & Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `WORKSPACE_ROOT` | Target repository directory for the agent to inspect and edit | Current working directory |
| `GEMINI_API_KEY` | Google Gemini API Key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | Optional |
| `OPENAI_API_KEY` | OpenAI API Key | Optional |

---

## 🛠️ Tool System Reference

The agent supports the following native tools:

- `list_files`: Browse directory trees safely within workspace bounds.
- `read_file`: Inspect file contents.
- `write_file`: Overwrite or create new files.
- `replace_with_git_merge_diff`: Surgical edits using `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`.
- `delete_file` & `rename_file`: Workspace file management.
- `run_in_bash_session`: Execute commands, tests, and build tools in shell.
- `set_plan` & `plan_step_complete`: Multi-step planning tracker.
- `request_user_input` & `message_user`: User interaction.
- `submit`: Final change submission and pull request creation.

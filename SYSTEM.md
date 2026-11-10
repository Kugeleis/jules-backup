# Jules Agent System: Architecture & Technical Specification

## 1. Executive Overview

Jules is an autonomous, asynchronous coding agent designed to interact with software repositories, analyze codebases, plan multi-step solutions, interact with users when requirements need clarification, write code, run verification and testing suites in a sandboxed bash environment, and submit changes via Git.

This document outlines the complete architectural blueprint, technology stack, agent loop, tool specifications, and runtime requirements needed to reconstruct and self-host the Jules platform.

---

## 2. High-Level Architecture

The system consists of four primary subsystems:

```
+-------------------------------------------------------------------------+
|                              Frontend UI                                |
|  (Task view, Chat stream, Plan tracker, Diff inspector, Terminal view)  |
+-----------------------------------+-------------------------------------+
                                    | HTTP / WebSocket / SSE
                                    v
+-------------------------------------------------------------------------+
|                             Agent Backend                               |
|   - Session & Workspace Manager                                         |
|   - Agentic Execution Loop (ReAct / Function Calling)                   |
|   - Model Provider Gateway (Gemini API, Anthropic, OpenAI, Local LLMs)  |
|   - Tool Dispatcher & Security Sandbox Controller                       |
+-----------------------------------+-------------------------------------+
                                    | Docker API / gRPC / Local Exec
                                    v
+-------------------------------------------------------------------------+
|                        Execution Sandbox (Devbox)                       |
|   - Ephemeral Ubuntu/Debian container running tmux / bash session       |
|   - Pre-installed toolchains: Node/NVM, Python/Pyenv, Go, Rust, Java... |
|   - Git CLI configured with repo working tree                           |
|   - Headless browser (Playwright / Chromium) for web verification       |
+-------------------------------------------------------------------------+
```

---

## 3. Technology Stack

### A. Frontend Layer

- **Framework**: Modern Single-Page Application (HTML5, Modern CSS, ES6 / React / Vue compatible)
- **Features**:
  - Live conversation & agent thought streaming
  - Step-by-step Plan visualizer with real-time status indicators
  - Interactive tool execution card views (command, output, exit code)
  - Unified Git merge diff viewer and syntax highlighting
  - Live preview / screenshot gallery viewer

### B. Backend Agent Layer

- **Runtime**: Python 3.11+
- **Web Framework**: FastAPI / Starlette, Uvicorn
- **Concurrency**: Asynchronous event loop (`asyncio`) handling streaming tool invocations
- **Data Models**: Pydantic v2 schemas for all tool declarations and agent messages
- **LLM Support**: Pluggable provider system (Gemini 1.5 Pro / 2.0 Flash, Claude 3.5 Sonnet, GPT-4o, DeepSeek)

### C. Sandbox & Environment Layer

- **Host**: Linux / Docker containerization
- **Session Manager**: `tmux` persistent pseudo-terminal sessions
- **Filesystem**: Volume-mounted isolated workspace directory (`/app` or configured repo root)
- **Tooling**:
  - Languages: Node.js (v22), Python (3.11+), Go (1.22+), Rust (Cargo), JDK (21), .NET
  - Build Tools: Make, CMake, Maven, Gradle, Bun
  - Testing: Pytest, Jest, Playwright

---

## 4. Agent Execution Lifecycle

1. **Task Initialization**:
   - Agent is spun up with repo cloned into the sandbox root directory.
   - Initial user prompt is injected alongside the core System Instruction and Tool Declarations.

2. **Exploration & Deep Planning Phase**:
   - Agent lists files, reads `README.md`, `AGENTS.md`, and inspects directory layout.
   - Clarifying questions can be exchanged using `request_user_input`.
   - A structured plan is registered via `set_plan`.

3. **Autonomous Execution Phase**:
   - Agent iteratively executes tools:
     - `read_file` to inspect code
     - `write_file` or `replace_with_git_merge_diff` to modify source code
     - `run_in_bash_session` to compile, build, run linters, and execute unit tests
     - `frontend_verification_instructions` / Playwright for UI validation
   - Steps in the plan are marked complete via `plan_step_complete`.

4. **Pre-Commit & Finalization**:
   - Agent calls `pre_commit_instructions` to ensure quality gates pass.
   - Agent commits the code and requests pull request submission via `submit`.

---

## 5. Security & Isolation Model

- Agent commands run in non-root or unprivileged containers with isolated cgroups.
- File operations are constrained within the repo root unless explicitly authorized.
- Safe tool execution prevents infinite loops via configurable timeouts on bash processes.

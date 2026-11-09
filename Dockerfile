FROM ghcr.io/astral-sh/uv:trixie-slim

# venv lives OUTSIDE /app, so a bind mount over /app (docker compose dev setups) can't hide it
ENV DEBIAN_FRONTEND=noninteractive \
    WORKSPACE_ROOT=/app \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Repo root is /app (WORKSPACE_ROOT); the backend lives in /app/backend
WORKDIR /app/backend

# apt has built-in retries; a failing install now fails the build
RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer: only lockfile + pyproject, cached until deps change.
# --locked: fail if uv.lock is out of sync. uv retries transient network errors itself.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Application code (keep .venv, .git etc. out via .dockerignore)
COPY . /app

# Run as non-root; /opt/venv and /opt/python are world-readable.
# /data is the writable spot for runtime files (group 0 + g=u also works with arbitrary UIDs).
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /data \
    && chown 10001:0 /data \
    && chmod 775 /data
USER 10001

EXPOSE 8000

# cwd is /app/backend, so `app` (backend/app/main.py) is importable; uvicorn adds cwd to sys.path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

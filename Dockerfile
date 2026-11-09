FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE_ROOT=/app

RUN apt-get update && apt-get install -y \
    curl \
    git \
    tmux \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Setup Python virtualenv
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application files
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

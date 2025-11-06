FROM python:3.10-bullseye

# Install build dependencies
SHELL [ "/bin/bash", "-c" ]

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libcairo2-dev \
    ffmpeg \
    libpango1.0-dev && \
    pip install --no-cache-dir --upgrade pip && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    source $HOME/.local/bin/env

ENV PATH="/root/.local/bin:${PATH}"

# check uv version
RUN uv --version

# Set working directory
WORKDIR /app

RUN useradd -m bot

RUN uv init enginimate && \
    cd enginimate && \
    uv venv && \
    source .venv/bin/activate && \
    uv add manim && \
    yes '' | manim init project manim_test --default

RUN chown -R bot /app/enginimate/

# Run with limited privileges
USER bot

WORKDIR /app/enginimate/manim_test

# Default command
CMD ["python3", "-c", "print('Container ready')"]
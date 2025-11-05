FROM python:3.10-bullseye

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libcairo2-dev \
    libpango1.0-dev && \
    pip install --no-cache-dir --upgrade pip && \
    curl -LsSf https://astral.sh/uv/install.sh | sh \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

RUN uv init enginimate && \
    cd enginimate && \
    source .venv/bin/activate && \
    uv add manim && \
    manim init project . --default

# Run with limited privileges
USER bot

RUN chown -R bot /app/enginimate

WORKDIR /app/enginimate

# Default command
CMD ["python3", "-c", "print('Container ready')"]
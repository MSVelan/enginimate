FROM python:3.12

# Install build dependencies
SHELL [ "/bin/bash", "-c" ]

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libcairo2-dev \
    ffmpeg \
    texlive \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-pictures \
    texlive-fonts-extra \
    texlive-science \
    tipa \
    dvisvgm \
    redis-server \
    libpango1.0-dev && \
    pip install --no-cache-dir --upgrade pip && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    source $HOME/.local/bin/env

ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# RUN useradd -m bot

RUN uv init enginimate && \
    cd enginimate && \
    uv venv && \
    source .venv/bin/activate && \
    uv add manim \
    cloudinary \
    fastapi \
    pydantic \
    redis \
    hiredis \
    sse-starlette \
    uvicorn[standard]

# yes '' | manim init project manim_test --default

# RUN chown -R bot /app/enginimate/

# RUN mkdir -p /app/enginimate/data/ && chown bot:bot /app/enginimate/data
RUN mkdir -p /app/enginimate/data/

VOLUME [ "/app/enginimate/data" ]

# Run with limited privileges
# USER bot
# ENV HOME=/home/bot \
#     PYTHONUNBUFFERED=1

ENV PYTHONUNBUFFERED=1

WORKDIR /app/enginimate

# COPY --chown=bot:bot app.py .
# COPY --chown=bot:bot manim_executor.py .

COPY app.py .
COPY manim_executor.py .

ENV PATH="/app/enginimate/.venv/bin:/usr/bin:/usr/local/bin:${PATH}"

# add __init__.py in manim_test on startup
# WORKDIR /app/enginimate/manim_test

EXPOSE 7860

CMD ["sh", "-c", "redis-server --bind 0.0.0.0 --port 6379 & exec uvicorn app:app --workers 2 --host 0.0.0.0 --port 7860"]
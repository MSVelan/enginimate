FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Copy application files
COPY --chown=user:user app.py .
COPY --chown=user:user requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER user
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "app:app", "--workers", "5", "--host", "0.0.0.0", "--port", "7860"]
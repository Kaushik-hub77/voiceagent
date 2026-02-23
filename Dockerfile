FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HOME=/home/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create system group & user and create the home directory (-m)
# set shell to nologin for safety
RUN groupadd -r app && useradd -r -m -d /home/app -g app -s /usr/sbin/nologin app

# Copy project metadata and lockfile, then install deps (runs as root)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --inexact

# Copy application code
COPY app ./app

# Logs directory (will be bound to host ./logs)
RUN mkdir -p /app/logs

# Make sure home and cache dirs exist and are owned by app before switching
RUN mkdir -p /home/app/.cache && chown -R app:app /home/app /app /app/logs

# Download NLTK data required by the app (may create files in HOME)
RUN uv run python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')" || true

# Ensure any files created above by root are owned by app
RUN chown -R app:app /home/app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI app defined in app.voice_main:app on port 8000
CMD ["uv", "run", "uvicorn", "app.voice_main:app", "--host", "0.0.0.0", "--port", "8000"]

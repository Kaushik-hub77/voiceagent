#!/bin/bash

# Run AI LLM Service locally for development

set -e

echo "🏃 Starting AI LLM Service (Development Mode)"

# Ensure dependencies are installed using your preferred dependency manager

# Set development environment
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check for API keys
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Some features may not work."
fi

# Download NLTK data if needed
echo "📚 Ensuring NLTK data is available..."
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# Run with auto-reload
echo "🔄 Starting with auto-reload..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir app \
    --log-level debug \
    --access-log

#!/bin/bash

# Code formatting script for AI LLM Service

set -e

echo "🎨 Formatting code..."

# Ensure dependencies are installed using your preferred dependency manager

# Run Black formatter
echo "🖤 Running Black..."
black app/ tests/ scripts/

# Run isort for import sorting
echo "🔀 Running isort..."
isort app/ tests/ scripts/

# Run flake8 for linting
echo "🔍 Running flake8..."
flake8 app/ tests/ scripts/ --max-line-length=88 --extend-ignore=E203,W503

# Run mypy for type checking (optional, can be slow)
echo "📝 Running mypy..."
mypy app/ --ignore-missing-imports || echo "⚠️  MyPy found issues (non-blocking)"

echo "✅ Code formatting completed!"

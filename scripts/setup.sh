#!/bin/bash

# AI LLM Service Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up AI LLM Service development environment..."

# Check if Python 3.9+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION or higher is required. You have Python $PYTHON_VERSION."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Dependencies should be installed using your preferred dependency manager
echo "📚 Please install dependencies using your preferred dependency manager"

# Download NLTK data
echo "📖 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp env.template .env 2>/dev/null || echo "# Copy from env.template and fill in your API keys" > .env
    echo "⚠️  Please edit .env file and add your API keys"
else
    echo "✅ .env file already exists"
fi

# Create logs directory
mkdir -p logs

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys:"
echo "   - OPENAI_API_KEY (required)"
echo "   - ANTHROPIC_API_KEY (optional)"
echo "   - GOOGLE_API_KEY (optional)"
echo ""
echo "2. Run the service:"
echo "   ./scripts/run_local.sh"
echo ""
echo "3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "Happy coding! 🚀"

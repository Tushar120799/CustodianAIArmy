#!/bin/bash

# Custodian AI Army Installation Script
# This script sets up the environment and installs dependencies

echo "🤖 Custodian AI Army Installation Script"
echo "========================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $python_version is installed, but Python $required_version or higher is required."
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and install build tools
echo "⬆️  Upgrading pip and installing build tools..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your GEMINI_API_KEY"
else
    echo "✅ Environment file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your GEMINI_API_KEY"
echo "2. Activate the virtual environment: source .venv/bin/activate"
echo "3. Run the application: python3 main.py"
echo "4. Open your browser and go to http://localhost:8000"
echo ""
echo "For more information, see README.md"
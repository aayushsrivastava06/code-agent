#!/bin/bash
# Code Agent — Unix/Mac launcher

set -e

echo ""
echo "================================================"
echo "  Code Agent — Claude Code Clone (Free AI)"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Install it from: https://www.python.org/downloads/"
    exit 1
fi

# Use python3 if available, else python
if command -v python3 &>/dev/null; then
    PYTHON=python3
    PIP=pip3
else
    PYTHON=python
    PIP=pip
fi

echo "Using: $($PYTHON --version)"

# Check we're in the right directory
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found. Run this from the code-agent directory."
    exit 1
fi

# Install dependencies if needed
if [ ! -f ".deps_installed" ]; then
    echo ""
    echo "Installing dependencies..."
    $PIP install -r requirements.txt
    touch .deps_installed
    echo "Dependencies installed!"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "No .env file found. Running setup wizard..."
    $PYTHON main.py --setup
    echo ""
fi

echo "Starting Code Agent..."
echo "Workspace: $(pwd)"
echo ""

$PYTHON main.py "$@"

#!/bin/bash

# Start script for 1inch Fusion+ API
echo "Starting 1inch Fusion+ API Server"
echo "================================="

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# 1inch API Configuration
ONE_INCH_API_KEY=your_api_key_here

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=portfolio_optimizer

# Optional: Set log level
LOG_LEVEL=INFO
EOF
    echo ".env file created. Please edit it to add your actual API key."
    echo ""
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for Python virtual environment
if [ -d ".venv" ] || [ -d "venv" ]; then
    # Virtual environment exists
    if [ -d ".venv" ]; then
        VENV_DIR=".venv"
    else
        VENV_DIR="venv"
    fi
    
    echo "Activating virtual environment..."
    source $VENV_DIR/bin/activate
else
    echo "No virtual environment found. Consider creating one with:"
    echo "python -m venv .venv"
    echo "source .venv/bin/activate"
    echo ""
fi

# Install or update dependencies
echo "Checking dependencies..."
pip install -r requirements.txt

# Start the server
echo ""
echo "Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Note: The script will hang here while the server is running
# Press Ctrl+C to stop the server 
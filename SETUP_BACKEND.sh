#!/bin/bash

# SIMA Backend Setup Script
# Sets up Python environment and installs dependencies

echo "╔════════════════════════════════════════╗"
echo "║    SIMA Backend Setup                  ║"
echo "║    FastAPI + Python                    ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.8+"
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi
python3 --version

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Virtual environment created and activated"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install core requirements
echo "Installing core dependencies..."
pip install fastapi>=0.110
pip install uvicorn[standard]>=0.27
pip install pydantic>=2.7
pip install pydantic-settings>=2.2
pip install sqlalchemy>=2.0
pip install psycopg[binary]>=3.1
pip install python-jose>=3.3
pip install passlib[bcrypt]>=1.7
pip install boto3>=1.34
pip install requests>=2.31
pip install prometheus-client>=0.20

echo ""
echo "✓ Dependencies installed successfully"

# Test the installation
echo ""
echo "Testing installation..."
python3 -c "import fastapi; import uvicorn; print('✓ FastAPI and Uvicorn imported successfully')"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║    Backend Setup Complete!             ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "To start the backend server, run:"
echo ""
echo "  source venv/bin/activate"
echo "  python3 -m uvicorn core.app.main:app --reload --port 5000"
echo ""
echo "The API will be available at:"
echo "  http://localhost:5000"
echo "  http://localhost:5000/docs (interactive documentation)"
echo ""

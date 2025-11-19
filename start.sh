#!/bin/bash

# Canteen Ordering System - Quick Start Script

echo "🍽️  Starting Canteen Ordering System..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! pip show Flask > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the application
echo ""
echo "✅ Starting Flask application..."
echo ""
echo "📱 Customer Interface: http://localhost:5000"
echo "🔐 Admin Panel: http://localhost:5000/admin/login"
echo ""
echo "Default Admin Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python app.py

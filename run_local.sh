#!/bin/bash

# Simple script to run the function locally

echo "🚀 Starting local development server..."

# Load .env file if it exists
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for required environment variables
if [ -z "$POLYGON_API_KEY" ]; then
    echo "❌ Error: POLYGON_API_KEY not set"
    echo "Please create a .env file with:"
    echo "POLYGON_API_KEY=your_key_here"
    echo "BASIC_AUTH_PASSWORD=your_password_here"
    exit 1
fi

if [ -z "$BASIC_AUTH_PASSWORD" ]; then
    echo "⚠️  Warning: BASIC_AUTH_PASSWORD not set (using default 'password')"
    export BASIC_AUTH_PASSWORD="password"
fi

# Run the functions framework
echo "🌐 Server starting on http://localhost:8080"
echo "📊 Test URL: http://localhost:8080?ticker=AAPL"
echo ""
echo "Example curl command:"
echo "curl -H \"Authorization: Basic \$(echo -n '${BASIC_AUTH_USERNAME:-admin}:$BASIC_AUTH_PASSWORD' | base64)\" \\"
echo "  \"http://localhost:8080?ticker=AAPL&duration=day&size=800x400\" --output test.png"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the functions framework with exported environment variables
python3 -m functions_framework --target=generate_spark_graph --debug --port=8080
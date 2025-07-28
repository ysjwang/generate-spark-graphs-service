#!/usr/bin/env python3
"""Local testing script for the spark graph generator"""

import os
import sys
import base64
import requests
import subprocess
import time
from threading import Thread

# Load environment variables from .env file
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Start the functions framework server
def start_server():
    cmd = [
        sys.executable, '-m', 'functions_framework',
        '--target=generate_spark_graph',
        '--port=8080',
        '--debug'
    ]
    
    # Environment variables are already loaded by load_env()
    return subprocess.Popen(cmd)

# Test the API
def test_api():
    base_url = "http://localhost:8080"
    
    # Get credentials from environment
    username = os.environ.get('BASIC_AUTH_USERNAME', 'admin')
    password = os.environ.get('BASIC_AUTH_PASSWORD', '')
    
    if not password:
        print("❌ BASIC_AUTH_PASSWORD not set in .env or .env.yaml")
        return
    
    # Create auth header
    credentials = f"{username}:{password}"
    auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"
    
    headers = {
        'Authorization': auth_header
    }
    
    # Test cases
    test_cases = [
        {
            'name': 'Basic test - AAPL daily',
            'params': {'ticker': 'AAPL'},
            'save_as': 'test_aapl_daily.png'
        },
        {
            'name': 'Google hourly',
            'params': {'ticker': 'GOOGL', 'duration': 'hour'},
            'save_as': 'test_googl_hourly.png'
        },
        {
            'name': 'Tesla weekly with custom size',
            'params': {'ticker': 'TSLA', 'duration': 'week', 'size': '800x400'},
            'save_as': 'test_tsla_weekly.png'
        },
        {
            'name': 'Microsoft monthly',
            'params': {'ticker': 'MSFT', 'duration': 'month', 'size': '1200x600'},
            'save_as': 'test_msft_monthly.png'
        },
        {
            'name': 'Invalid ticker (should fail)',
            'params': {'ticker': 'INVALID123'},
            'save_as': None
        },
        {
            'name': 'No auth (should fail)',
            'params': {'ticker': 'AAPL'},
            'save_as': None,
            'skip_auth': True
        }
    ]
    
    print("\n🧪 Running API tests...\n")
    
    for test in test_cases:
        print(f"📊 Test: {test['name']}")
        
        # Prepare request
        url = base_url
        params = test['params']
        test_headers = {} if test.get('skip_auth') else headers
        
        try:
            response = requests.get(url, params=params, headers=test_headers)
            
            if response.status_code == 200:
                print(f"   ✅ Success! Status: {response.status_code}")
                
                # Save image if specified
                if test['save_as']:
                    with open(test['save_as'], 'wb') as f:
                        f.write(response.content)
                    print(f"   💾 Saved to: {test['save_as']}")
            else:
                print(f"   ❌ Failed! Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()

def main():
    print("🚀 Starting local test server...\n")
    
    # Load environment variables
    load_env()
    
    # Check for required variables
    if not os.environ.get('POLYGON_API_KEY'):
        print("❌ POLYGON_API_KEY not found!")
        print("Please create a .env file with:")
        print("POLYGON_API_KEY=your_key_here")
        print("BASIC_AUTH_PASSWORD=your_password_here")
        return
    
    # Start the server
    server_process = start_server()
    
    print("⏳ Waiting for server to start...")
    time.sleep(3)  # Give server time to start
    
    try:
        # Run tests
        test_api()
        
        print("\n✨ Tests complete!")
        print("📌 Server is still running. Press Ctrl+C to stop.")
        print("🌐 You can also test manually at: http://localhost:8080")
        print("\nExample curl command:")
        
        username = os.environ.get('BASIC_AUTH_USERNAME', 'admin')
        password = os.environ.get('BASIC_AUTH_PASSWORD', 'password')
        print(f'curl -H "Authorization: Basic {base64.b64encode(f"{username}:{password}".encode()).decode()}" \\')
        print('  "http://localhost:8080?ticker=AAPL&duration=day" --output manual_test.png')
        
        # Keep server running
        server_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
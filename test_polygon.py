#!/usr/bin/env python3
"""Test script to debug Polygon.io API issues"""

import os
import requests
from datetime import datetime, timedelta
import json

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Reading from environment only.")
    pass

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')

def test_polygon_api():
    if not POLYGON_API_KEY:
        print("❌ POLYGON_API_KEY not set!")
        print("Please set it in .env file or export POLYGON_API_KEY='your_key'")
        return
    
    print(f"✓ API Key found (first 8 chars): {POLYGON_API_KEY[:8]}...")
    
    # Test 1: Check API key validity
    print("\n1. Testing API key validity...")
    url = "https://api.polygon.io/v1/marketstatus/now"
    response = requests.get(url, params={'apiKey': POLYGON_API_KEY})
    
    if response.status_code == 403:
        print("❌ Invalid API key!")
        return
    elif response.status_code == 200:
        print("✓ API key is valid")
        market_status = response.json()
        print(f"  Market status: {market_status.get('market', 'Unknown')}")
    
    # Test 2: Test different tickers
    print("\n2. Testing stock data retrieval...")
    tickers = ['AAPL', 'GOOGL', 'INVALID_TICKER']
    
    for ticker in tickers:
        print(f"\nTesting {ticker}...")
        
        # Last day of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        
        response = requests.get(url, params={
            'apiKey': POLYGON_API_KEY,
            'sort': 'asc',
            'limit': 50000
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Results count: {len(data.get('results', []))}")
            if data.get('results'):
                first_bar = data['results'][0]
                print(f"  First timestamp: {datetime.fromtimestamp(first_bar['t']/1000)}")
                print(f"  Close price: ${first_bar['c']}")
        else:
            print(f"  ❌ Error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    
    # Test 3: Check if free tier has limitations
    print("\n3. Checking API tier limitations...")
    url = "https://api.polygon.io/v1/reference/tickers"
    response = requests.get(url, params={
        'apiKey': POLYGON_API_KEY,
        'limit': 1
    })
    
    if response.status_code == 200:
        print("✓ Can access reference data")
    else:
        print("❌ Cannot access reference data (might be tier limitation)")

if __name__ == "__main__":
    test_polygon_api()
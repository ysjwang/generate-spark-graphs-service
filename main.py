import functions_framework
import base64
import os
from flask import jsonify, make_response
import requests
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
import json

# Environment variables
POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')
BASIC_AUTH_USERNAME = os.environ.get('BASIC_AUTH_USERNAME', 'admin')
BASIC_AUTH_PASSWORD = os.environ.get('BASIC_AUTH_PASSWORD')


def verify_basic_auth(request):
    """Verify basic authentication."""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    
    try:
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        return username == BASIC_AUTH_USERNAME and password == BASIC_AUTH_PASSWORD
    except Exception:
        return False


def get_duration_params(duration):
    """Convert duration string to start/end dates."""
    end_date = datetime.now()
    
    duration_map = {
        'hour': timedelta(hours=1),
        'day': timedelta(days=1),
        'week': timedelta(weeks=1),
        'month': timedelta(days=30)
    }
    
    if duration not in duration_map:
        raise ValueError(f"Invalid duration: {duration}")
    
    start_date = end_date - duration_map[duration]
    
    # For hour duration, use minute bars; for others use appropriate timespan
    if duration == 'hour':
        timespan = 'minute'
        multiplier = 1
    elif duration == 'day':
        timespan = 'minute'
        multiplier = 5
    elif duration == 'week':
        timespan = 'hour'
        multiplier = 1
    else:  # month
        timespan = 'day'
        multiplier = 1
    
    return start_date, end_date, timespan, multiplier


def fetch_stock_data(ticker, start_date, end_date, timespan, multiplier):
    """Fetch stock data from Polygon.io API."""
    base_url = "https://api.polygon.io/v2/aggs/ticker"
    
    # Adjust for free tier - they have a 2-year limitation
    two_years_ago = datetime.now() - timedelta(days=730)
    if start_date < two_years_ago:
        start_date = two_years_ago
    
    params = {
        'apiKey': POLYGON_API_KEY,
        'sort': 'asc',
        'limit': 50000,
        'adjusted': 'true'  # Use adjusted prices
    }
    
    url = f"{base_url}/{ticker}/range/{multiplier}/{timespan}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
    
    print(f"Fetching from URL: {url}")  # Debug URL
    
    response = requests.get(url, params=params)
    
    # Log full response for debugging
    print(f"Response status code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Response body: {response.text}")
        response.raise_for_status()
    
    data = response.json()
    
    # Debug logging
    print(f"Polygon API Response Status: {data.get('status')}")
    print(f"Results count: {len(data.get('results', []))}")
    print(f"Full response keys: {data.keys()}")
    
    if data.get('status') == 'ERROR':
        error_msg = data.get('error', 'Unknown error')
        raise ValueError(f"Polygon API error: {error_msg}")
    
    if data.get('status') == 'OK' and data.get('resultsCount', 0) == 0:
        # No results but valid response
        raise ValueError(f"No data available for {ticker}. The market might be closed or this ticker has no recent trading activity.")
    
    if not data.get('results'):
        # Provide more helpful error message with actual response
        raise ValueError(f"No data available for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}. Response: {json.dumps(data)[:200]}")
    
    return data['results']


def create_spark_graph_image(prices, size=(480, 480)):
    """Generate a spark graph image from price data."""
    # Extract closing prices
    values = [bar['c'] for bar in prices]
    
    if not values:
        raise ValueError("No price data available")
    
    # Create figure with transparent background
    dpi = 100
    fig_width = size[0] / dpi
    fig_height = size[1] / dpi
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    
    # Create x-axis values
    x = np.arange(len(values))
    
    # Plot the spark line
    ax.plot(x, values, color='#1f77b4', linewidth=2)
    
    # Fill area under the curve
    ax.fill_between(x, values, alpha=0.3, color='#1f77b4')
    
    # Remove all axes and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add subtle grid
    ax.grid(True, alpha=0.1, linestyle='-', linewidth=0.5)
    
    # Adjust margins
    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    
    # Save to BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close()
    
    buffer.seek(0)
    return buffer.getvalue()


@functions_framework.http
def generate_spark_graph(request):
    """Cloud Function entry point."""
    # Check authentication
    if not verify_basic_auth(request):
        return make_response(
            jsonify({'error': 'Unauthorized'}),
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )
    
    # Check for required environment variables
    if not POLYGON_API_KEY:
        return jsonify({'error': 'POLYGON_API_KEY not configured'}), 500
    
    if not BASIC_AUTH_PASSWORD:
        return jsonify({'error': 'BASIC_AUTH_PASSWORD not configured'}), 500
    
    try:
        # Parse request parameters
        ticker = request.args.get('ticker', '').upper()
        duration = request.args.get('duration', 'day').lower()
        size_param = request.args.get('size', '480x480')
        
        # Validate ticker
        if not ticker:
            return jsonify({'error': 'Missing required parameter: ticker'}), 400
        
        # Parse size
        try:
            width, height = map(int, size_param.split('x'))
            size = (width, height)
        except ValueError:
            return jsonify({'error': 'Invalid size format. Use WIDTHxHEIGHT (e.g., 480x480)'}), 400
        
        # Validate size limits
        if width < 100 or height < 100 or width > 2000 or height > 2000:
            return jsonify({'error': 'Size must be between 100x100 and 2000x2000'}), 400
        
        # Get duration parameters
        start_date, end_date, timespan, multiplier = get_duration_params(duration)
        
        # Fetch stock data
        stock_data = fetch_stock_data(ticker, start_date, end_date, timespan, multiplier)
        
        # Generate spark graph
        image_data = create_spark_graph_image(stock_data, size)
        
        # Return PNG image
        response = make_response(image_data)
        response.headers['Content-Type'] = 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
        
        return response
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return jsonify({'error': 'Invalid Polygon.io API key'}), 403
        elif e.response.status_code == 404:
            return jsonify({'error': 'Ticker not found'}), 404
        else:
            return jsonify({'error': 'Error fetching stock data'}), 500
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
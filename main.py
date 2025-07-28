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
import pytz

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


def fetch_company_name(ticker):
    """Fetch company name from Polygon.io API."""
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    
    params = {
        'apiKey': POLYGON_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                return data['results'].get('name', ticker)
    except Exception as e:
        print(f"Error fetching company name: {e}")
    
    return ticker  # Fallback to ticker if company name not found


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


def create_spark_graph_image(prices, ticker, company_name, size=(480, 480)):
    """Generate a spark graph image from price data with labels and axes."""
    # Extract data
    values = [bar['c'] for bar in prices]
    timestamps = [bar['t'] for bar in prices]
    
    if not values:
        raise ValueError("No price data available")
    
    # Create figure with white background
    dpi = 100
    fig_width = size[0] / dpi
    fig_height = size[1] / dpi
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi, facecolor='white')
    ax.set_facecolor('white')
    
    # Create x-axis values
    x = np.arange(len(values))
    
    # Plot the spark line
    ax.plot(x, values, color='#1f77b4', linewidth=2.5)
    
    # Calculate dynamic Y-axis bounds
    min_price = min(values)
    max_price = max(values)
    price_range = max_price - min_price
    
    # Add padding (5% of range on each side, or at least 0.5% of the price)
    if price_range > 0:
        padding = max(price_range * 0.05, min_price * 0.005)
    else:
        # If no price change, use 1% of price as padding
        padding = min_price * 0.01
    
    y_min = min_price - padding
    y_max = max_price + padding
    
    # Set Y-axis limits
    ax.set_ylim(y_min, y_max)
    
    # Fill area under the curve (from y_min to show relative change)
    ax.fill_between(x, values, y_min, alpha=0.2, color='#1f77b4')
    
    # Configure axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_linewidth(0.5)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Y-axis formatting (prices)
    ax.yaxis.set_major_locator(plt.MaxNLocator(5))
    ax.set_ylabel('Price ($)', fontsize=10)
    
    # Format y-axis labels as currency
    def format_price(x, p):
        return f'${x:,.0f}' if x >= 1 else f'${x:.2f}'
    ax.yaxis.set_major_formatter(plt.FuncFormatter(format_price))
    
    # X-axis formatting (time)
    # Select a subset of timestamps to show (avoid overcrowding)
    num_labels = min(6, len(timestamps))
    indices = np.linspace(0, len(timestamps)-1, num_labels, dtype=int)
    
    ax.set_xticks(indices)
    
    # Format timestamps based on data range
    time_range = timestamps[-1] - timestamps[0]
    if time_range < 86400000:  # Less than a day (in milliseconds)
        date_format = '%H:%M'
    elif time_range < 604800000:  # Less than a week
        date_format = '%b %d\n%H:%M'
    else:
        date_format = '%b %d'
    
    labels = []
    est_tz = pytz.timezone('US/Eastern')
    
    for idx in indices:
        # Convert milliseconds to datetime in UTC, then to EST
        dt_utc = datetime.fromtimestamp(timestamps[idx] / 1000, tz=pytz.UTC)
        dt_est = dt_utc.astimezone(est_tz)
        labels.append(dt_est.strftime(date_format))
    
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel('Time (EST)', fontsize=10)
    
    # Add title with ticker and company name
    plt.title(f'{ticker} - {company_name}', fontsize=14, fontweight='bold', pad=15)
    
    # Add current price annotation
    current_price = values[-1]
    price_change = values[-1] - values[0]
    price_change_pct = (price_change / values[0]) * 100
    
    # Color based on price change
    change_color = '#2ca02c' if price_change >= 0 else '#d62728'
    
    # Add price info as text
    price_text = f'${current_price:,.2f}'
    change_text = f'{"+" if price_change >= 0 else ""}{price_change:.2f} ({price_change_pct:+.2f}%)'
    
    ax.text(0.02, 0.98, price_text, transform=ax.transAxes, 
            fontsize=12, fontweight='bold', verticalalignment='top')
    ax.text(0.02, 0.91, change_text, transform=ax.transAxes, 
            fontsize=10, color=change_color, verticalalignment='top')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save to BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
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
        
        # Fetch company name
        company_name = fetch_company_name(ticker)
        
        # Fetch stock data
        stock_data = fetch_stock_data(ticker, start_date, end_date, timespan, multiplier)
        
        # Generate spark graph
        image_data = create_spark_graph_image(stock_data, ticker, company_name, size)
        
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
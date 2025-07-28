# Stock Spark Graph Generator Service

A Google Cloud Function that generates spark graphs (small, simple graphs without axes) for stock price data using the Polygon.io API.

## Features

- Generates PNG spark graphs for stock tickers
- Supports multiple time durations (hour, day, week, month)
- Customizable graph size
- Basic authentication protection
- Uses Polygon.io for real-time stock data

## API Endpoint

```
GET /
```

### Parameters

- `ticker` (required): Stock ticker symbol (e.g., AAPL, GOOGL)
- `duration` (optional): Time period for the graph
  - `hour` - Last hour (default: 1-minute bars)
  - `day` - Last day (default: 5-minute bars)
  - `week` - Last week (hourly bars)
  - `month` - Last 30 days (daily bars)
  - Default: `day`
- `size` (optional): Image size in format WIDTHxHEIGHT
  - Default: `480x480`
  - Min: `100x100`
  - Max: `2000x2000`

### Authentication

The API uses HTTP Basic Authentication. Include the Authorization header:

```
Authorization: Basic base64(username:password)
```

### Example Request

```bash
curl -H "Authorization: Basic $(echo -n 'admin:yourpassword' | base64)" \
  "https://your-function-url/generate-spark-graph?ticker=AAPL&duration=day&size=600x300"
```

## Local Development

1. Install dependencies:
```bash
pip3 install -r requirements.txt
# Optional: for testing scripts
pip3 install python-dotenv
```

2. Create `.env` file with your credentials:
```bash
POLYGON_API_KEY=your_polygon_api_key
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your_password
```

3. Run locally:
```bash
# Option 1: Using the provided script (recommended)
./run_local.sh

# Option 2: Run directly (make sure to export env vars first)
export POLYGON_API_KEY=your_polygon_api_key
export BASIC_AUTH_PASSWORD=your_password
python3 -m functions_framework --target=generate_spark_graph --debug

# Option 3: Run automated tests
python3 test_local.py
```

## Deployment

1. Set environment variables:
```bash
export POLYGON_API_KEY="your_polygon_api_key"
export BASIC_AUTH_PASSWORD="your_secure_password"
export BASIC_AUTH_USERNAME="admin"  # optional, defaults to 'admin'
```

2. Deploy to GCP:
```bash
./deploy.sh YOUR_PROJECT_ID us-central1
```

Or manually:
```bash
gcloud functions deploy generate-spark-graph \
    --gen2 \
    --runtime=python311 \
    --region=us-central1 \
    --source=. \
    --entry-point=generate_spark_graph \
    --trigger-http \
    --allow-unauthenticated \
    --memory=512MB \
    --timeout=30s \
    --set-env-vars POLYGON_API_KEY="$POLYGON_API_KEY",BASIC_AUTH_USERNAME="$BASIC_AUTH_USERNAME",BASIC_AUTH_PASSWORD="$BASIC_AUTH_PASSWORD"
```

## Environment Variables

- `POLYGON_API_KEY` (required): Your Polygon.io API key
- `BASIC_AUTH_USERNAME` (optional): Username for basic auth (default: "admin")
- `BASIC_AUTH_PASSWORD` (required): Password for basic auth

## Response

- Success: Returns a PNG image with `Content-Type: image/png`
- Error: Returns JSON with error message and appropriate HTTP status code

## Error Codes

- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid credentials)
- `403`: Forbidden (invalid Polygon.io API key)
- `404`: Not Found (ticker not found)
- `500`: Internal Server Error

## Requirements

- Python 3.11+
- Google Cloud Functions
- Polygon.io API key (get one at https://polygon.io)
#!/bin/bash

# Deploy script for GCP Cloud Function
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
FUNCTION_NAME="generate-spark-graph"

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if required environment variables are set
if [ -z "$POLYGON_API_KEY" ]; then
    echo "Error: POLYGON_API_KEY environment variable is not set"
    echo "Please set it using: export POLYGON_API_KEY='your_key'"
    echo "Or create a .env file with POLYGON_API_KEY=your_key"
    exit 1
fi

if [ -z "$BASIC_AUTH_PASSWORD" ]; then
    echo "Error: BASIC_AUTH_PASSWORD environment variable is not set"
    echo "Please set it using: export BASIC_AUTH_PASSWORD='your_password'"
    echo "Or create a .env file with BASIC_AUTH_PASSWORD=your_password"
    exit 1
fi

echo "Deploying Cloud Function to project: $PROJECT_ID in region: $REGION"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=generate_spark_graph \
    --trigger-http \
    --allow-unauthenticated \
    --memory=512MB \
    --timeout=30s \
    --max-instances=100 \
    --set-env-vars POLYGON_API_KEY="$POLYGON_API_KEY",BASIC_AUTH_USERNAME="${BASIC_AUTH_USERNAME:-admin}",BASIC_AUTH_PASSWORD="$BASIC_AUTH_PASSWORD" \
    --project=$PROJECT_ID

echo "Deployment complete!"
echo "Function URL: https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"
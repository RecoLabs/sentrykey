#!/bin/bash
# Script to create an AWS Lambda Layer for the Slack Secret Detection Bot

# Default region
AWS_REGION=${1:-us-east-1}

# Find Python 3.9 executable
PYTHON_CMD=$(which python3.9 || which python3 || which python)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: Python 3.9 not found"
    exit 1
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "Using $PYTHON_VERSION"
echo "Using AWS region: $AWS_REGION"

# Step 1: Create a directory structure for the layer
echo "Creating directory structure for Lambda layer..."
rm -rf slack-bot-layer
mkdir -p slack-bot-layer/python

# Step 2: Create a requirements.txt file
echo "Creating requirements.txt with necessary dependencies..."
cat > slack-bot-layer/requirements.txt << EOF
slack_sdk>=3.19.0
boto3>=1.26.0
botocore>=1.29.0
EOF

# Step 3: Create and activate a virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv slack-bot-layer/venv
source slack-bot-layer/venv/bin/activate || source slack-bot-layer/venv/Scripts/activate

# Step 4: Install pip in the virtual environment
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Step 5: Install the dependencies to the layer directory
echo "Installing dependencies to the layer directory..."
cd slack-bot-layer
pip install -r requirements.txt -t python/ --no-cache-dir

# Step 6: Remove unnecessary files to reduce size
echo "Cleaning up unnecessary files..."
find python/ -type d -name "__pycache__" -exec rm -rf {} +
find python/ -type f -name "*.pyc" -delete
find python/ -type f -name "*.pyo" -delete
find python/ -type d -name "*.dist-info" -exec rm -rf {} +
find python/ -type d -name "*.egg-info" -exec rm -rf {} +

# Step 7: Zip the layer contents
echo "Creating zip archive of the layer..."
zip -r slack-bot-layer.zip python/

# Step 8: Create the layer in AWS Lambda
echo "Publishing the layer to AWS Lambda..."
LAYER_VERSION=$(aws lambda publish-layer-version \
  --layer-name slack-secret-detector-layer \
  --description "Dependencies for Slack Secret Detector Bot" \
  --zip-file fileb://slack-bot-layer.zip \
  --compatible-runtimes python3.9 \
  --compatible-architectures "arm64" "x86_64" \
  --region $AWS_REGION \
  --query 'Version' \
  --output text)

# Step 9: Deactivate virtual environment and clean up
deactivate
cd ..
rm -rf slack-bot-layer

echo "Layer creation complete! Layer version: ${LAYER_VERSION}"
echo "You can now reference this layer in your Lambda function in the $AWS_REGION region"
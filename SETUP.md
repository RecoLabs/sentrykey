# Setting up the Slack Secret Detector

This guide explains how to set up the Slack Secret Detector using the provided CLI script.

## Prerequisites

1. Python 3.9 or higher
2. AWS CLI configured with appropriate credentials
3. Slack Workspace admin access

## Project Structure

Ensure your project has the following structure before running the setup script:
```
.
├── src/
│   ├── __init__.py
│   ├── lambda_function.py
│   ├── slack_utils.py
│   ├── password_detector.py
│   └── bedrock_analyzer.py
├── requirements.txt
├── setup_requirements.txt
└── setup_secret_detector.py
```

The `requirements.txt` file should contain all dependencies needed by the Lambda function:
```
slack-sdk>=3.19.0
boto3>=1.26.0
botocore>=1.29.0
```

## Installation

1. Install the required Python packages for the setup script:
   ```bash
   pip install -r setup_requirements.txt
   ```

2. Make the setup script executable:
   ```bash
   chmod +x setup_secret_detector.py
   ```

## Usage

Basic usage with required parameters:
```bash
./setup_secret_detector.py \
  --slack-token "xoxb-your-token-here" \
  --alert-channel-id "C12345678"
```

Advanced usage with all options:
```bash
./setup_secret_detector.py \
  --slack-token "xoxb-your-token-here" \
  --alert-channel-id "C12345678" \
  --region "us-east-1" \
  --use-bedrock \
  --bedrock-model "anthropic.claude-3-haiku-20240307-v1:0"
```

### Parameters

- `--slack-token`: (Required) Your Slack Bot User OAuth Token
- `--alert-channel-id`: (Required) The Slack channel ID where security alerts will be sent
- `--region`: (Optional) AWS region to deploy to (default: us-east-1)
- `--use-bedrock`: (Optional) Enable AI-based detection using Amazon Bedrock
- `--bedrock-model`: (Optional) Specify the Bedrock model ID (default: Claude 3 Haiku)

## What the Script Does

1. Creates an IAM role with necessary permissions
2. Stores the Slack token securely in AWS Secrets Manager
3. Creates the Lambda function with the secret detector code
4. Sets up an API Gateway endpoint
5. Provides instructions for configuring the Slack App

## After Running the Script

1. Go to your [Slack App settings](https://api.slack.com/apps)
2. Enable Event Subscriptions
3. Set the Request URL to the provided API Gateway URL
4. Subscribe to these bot events:
   - message.channels
   - message.groups
   - message.im
   - message.mpim
   - member_joined_channel
   - channel_created

## Troubleshooting

- If you see "EntityAlreadyExists" messages, don't worry - the script will use existing resources
- Make sure your AWS credentials have sufficient permissions
- Check CloudWatch Logs if the Lambda function isn't working as expected
- Verify that all required Slack bot scopes are enabled in your Slack App settings

## Security Notes

- The Slack token is stored securely in AWS Secrets Manager
- The Lambda function uses minimal IAM permissions
- API Gateway endpoints use HTTPS
- No sensitive information is logged or stored 
# Slack Secrets Detector

![SentryKey Security Bot](SentryKey%20Security%20Bot.png)

A serverless application that detects passwords and sensitive credentials shared in Slack channels and sends security alerts.

## Overview

This AWS Lambda function monitors Slack messages for potential credentials, passwords, or sensitive information. When detected, it sends alerts to a designated security channel and a direct message to the user who posted the sensitive information.

Features:
- **Pattern-based detection**: Uses regex patterns to identify various credential formats
- **AI-powered analysis**: Optional integration with Amazon Bedrock for AI-based detection
- **Comprehensive monitoring**: Works in all channel types (public, private, DMs)
- **Auto-join capability**: Can automatically join new channels when invited
- **Real-time monitoring**: Processes Slack events as they occur
- **Security alerts**: Sends notifications to a security team channel
- **User education**: Notifies users when they share sensitive information

## Prerequisites

- AWS Account
- Slack Workspace with admin privileges
- [Node.js](https://nodejs.org/) and npm
- [Python 3.9](https://www.python.org/downloads/)

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch" and provide a name (e.g., "Password Detector") and select your workspace
3. Go to "OAuth & Permissions" and add these scopes:
   - `channels:history` - Read messages in public channels
   - `channels:join` - Join public channels
   - `channels:read` - Get channel information
   - `chat:write` - Send alert messages
   - `groups:history` - Read messages in private channels
   - `groups:read` - View private channel information
   - `im:history` - Read direct messages
   - `im:read` - View direct message information
   - `mpim:history` - Read group direct messages
   - `mpim:read` - View group direct message information
   - `users:read` - View basic user information
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`) for later use

### 2. Create a Security Alert Channel

1. Create a private channel in Slack (e.g., `#security-alerts`)
2. Add your bot to this channel
3. Copy the channel ID for deployment

### 3. Deploy the Lambda Function

1. Clone this repository
2. Install dependencies:
   ```
   npm install
   ```
3. Install the Serverless Python Requirements plugin:
   ```
   npm install --save serverless-python-requirements
   ```
4. Deploy the function:
   ```
   serverless deploy \
     --param="slackBotToken=xoxb-your-token-here" \
     --param="alertChannelId=C12345678" \
     --param="useBedrock=true"
   ```

### 4. Configure Slack Events API

1. Take the API Gateway URL from the deployment output
2. Go to your Slack App configuration
3. Navigate to "Event Subscriptions" and enable events
4. Enter your Lambda URL as the Request URL
5. Subscribe to the `message.channels` bot event
6. Save changes

## Usage

Once deployed, the bot will automatically:

1. Monitor messages in all channels where it's invited (public, private, and DMs)
2. Join new channels when invited
3. Detect potential passwords and credentials
4. Send alerts to the security team
5. Notify users who post sensitive information

### Channel Access

The bot can work in:
- Public channels (after being invited or joining)
- Private channels (requires explicit invitation)
- Direct messages (requires user to initiate)
- Multi-person direct messages (requires explicit addition)

Note: For privacy and security reasons, the bot will only join channels it's explicitly invited to.

### Using AI Detection

To enable Amazon Bedrock for AI-based detection:

1. Deploy with `useBedrock=true`
2. Set the Bedrock model (defaults to Claude 3 Haiku):
   ```
   --param="bedrockModel=anthropic.claude-3-haiku-20240307-v1:0"
   ```
3. Ensure your AWS account has access to the specified model

The AI detection can identify credentials and sensitive information that might not match the predefined patterns.

## Development

### Local Testing

1. Set up a local environment:
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a .env file with test credentials:
   ```
   SLACK_BOT_TOKEN_DEV=xoxb-your-token
   ALERT_CHANNEL_ID=C12345678
   ```

3. Run tests:
   ```
   pytest
   ```

### Project Structure

- `src/`: Source code modules
- `tests/`: Test cases
- `serverless.yml`: Deployment configuration
- `requirements.txt`: Python dependencies

## Step 5: Test the Bot

1. In any public channel where your bot is present, post a message containing a fake password, like:
   ```
   password = "MyTestPassword123!"
   ```
2. Check your security alert channel for the notification
3. Verify that the user who posted the message received a direct message

## Monitoring and Maintenance

- Check CloudWatch Logs for any errors or issues with the Lambda function
- Periodically review the detection patterns to reduce false positives
- Consider adding additional security features like automatically deleting detected passwords (requires additional permissions)

## Cost Estimation

The Secret Detector uses several AWS services, each with its own pricing model. Here's an estimated monthly cost breakdown for typical usage:

### AWS Lambda
- Free tier: 1M requests/month and 400,000 GB-seconds of compute time
- Beyond free tier:
  - $0.20 per 1M requests
  - $0.0000166667 per GB-second
  - Estimated cost for 100k messages/month: ~$0.10

### API Gateway
- Free tier: 1M API calls/month
- Beyond free tier:
  - $3.50 per million API calls
  - Estimated cost for 100k calls/month: Free (within free tier)

### AWS Secrets Manager
- No free tier
- $0.40 per secret per month
- $0.05 per 10,000 API calls
- Estimated monthly cost: ~$0.45

### CloudWatch Logs
- Free tier: 5GB data ingestion, 5GB data storage
- Beyond free tier:
  - $0.50 per GB ingested
  - $0.03 per GB stored
  - Estimated cost for typical usage: Free (within free tier)

### Amazon Bedrock (Optional)
If using AI-based detection with Claude 3 Haiku:
- No free tier
- $0.00025 per 1K input tokens
- $0.00125 per 1K output tokens
- Estimated cost for 100k messages/month: ~$5-10

### Total Estimated Monthly Cost
- Basic setup (without Bedrock): ~$0.55
- With Bedrock AI detection: ~$5.55-10.55

Note: These are rough estimates based on typical usage patterns. Actual costs may vary depending on:
- Number of messages processed
- Length of messages
- Frequency of secret detection
- Region selection
- Usage patterns
- Whether you're within free tier limits

To optimize costs:
1. Stay within free tier limits where possible
2. Monitor usage with AWS Cost Explorer
3. Set up billing alerts
4. Consider using pattern-based detection instead of AI for lower volumes

## Security Considerations

- The Lambda function never logs or stores actual credentials
- AWS Secrets Manager securely stores the Slack token
- We use minimal permissions IAM roles
- All sensitive information handling follows security best practices

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

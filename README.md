# Slack Secrets Detector

![SentryKey Security Bot](assets/images/SentryKey%20Security%20Bot.png)

A Python application that detects passwords and sensitive credentials shared in Slack channels and sends security alerts.

## Project Structure

```
.
├── assets/                 # Static assets (images, icons)
│   └── images/            # Image files
├── docs/                  # Documentation
│   ├── SETUP.md          # Setup instructions
│   └── SETUP GUIDE.md    # Detailed setup guide
├── setup/                # Setup scripts
│   ├── setup_secret_detector.py  # Main setup script
│   └── setup_requirements.txt   # Setup script dependencies
├── src/                  # Source code
│   ├── bedrock_analyzer.py
│   ├── init.py
│   └── slack_utils.py
├── tests/               # Test files
├── requirements.txt     # Python dependencies
└── .env.example        # Example environment variables
```

## Overview

This application monitors Slack messages for potential credentials, passwords, or sensitive information. When detected, it sends alerts to a designated security channel and a direct message to the user who posted the sensitive information.

Features:
- **Pattern-based detection**: Uses regex patterns to identify various credential formats
- **AI-powered analysis**: Optional integration with Amazon Bedrock for AI-based detection
- **Comprehensive monitoring**: Works in all channel types (public, private, DMs)
- **Auto-join capability**: Can automatically join new channels when invited
- **Real-time monitoring**: Processes Slack events as they occur
- **Security alerts**: Sends notifications to a security team channel
- **User education**: Notifies users when they share sensitive information

## Prerequisites

- Python 3.9 or higher
- Slack Workspace with admin privileges

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
3. Copy the channel ID for configuration

### 3. Set Up the Environment

1. Clone this repository
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your configuration:
   ```
   cp .env.example .env
   ```
5. Edit `.env` with your Slack token and channel ID:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token-here
   ALERT_CHANNEL_ID=C12345678
   USE_BEDROCK=true  # Optional: Set to false to disable AI detection
   ```

### 4. Run the Setup Script

1. Run the setup script:
   ```
   python setup/setup_secret_detector.py
   ```

## Usage

Once configured, the bot will automatically:

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

1. Set `USE_BEDROCK=true` in your `.env` file
2. Configure your AWS credentials if using Bedrock
3. The AI detection can identify credentials and sensitive information that might not match the predefined patterns

## Development

### Local Testing

1. Set up a local environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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

## Step 5: Test the Bot

1. In any public channel where your bot is present, post a message containing a fake password, like:
   ```
   password = "MyTestPassword123!"
   ```
2. Check your security alert channel for the notification
3. Verify that the user who posted the message received a direct message

## Security Considerations

- The application never logs or stores actual credentials
- All sensitive information handling follows security best practices
- Use environment variables for sensitive configuration
- Implement proper access controls and monitoring

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
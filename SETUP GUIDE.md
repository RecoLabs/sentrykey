# Slack Password Detection Bot Setup Guide

This guide will walk you through setting up a Slack bot that automatically scans messages in public channels for potential passwords or credentials, and alerts your security team when they're detected.

## Overview

The bot is designed to run as an AWS Lambda function that receives events from Slack via the Events API. When a message containing potential password patterns is detected, the bot will:

1. Send an alert to a designated security channel
2. Send a direct message to the user who posted the potential password
3. Log the event (without capturing the actual password)

## Prerequisites

- AWS Account
- Slack Workspace with admin privileges
- [Serverless Framework](https://www.serverless.com/) installed
- [Node.js](https://nodejs.org/) and [npm](https://www.npmjs.com/) installed
- [Python 3.9](https://www.python.org/downloads/) installed

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch" and provide a name (e.g., "Password Detector") and select your workspace
3. Under "Basic Information", note your App's credentials for later use
4. Navigate to "OAuth & Permissions" and add the following scopes:
   - `channels:history` - To read messages in public channels
   - `channels:read` - To get channel information
   - `chat:write` - To send alert messages
   - `im:write` - To send direct messages to users
   - `links:read` - To create permalinks to messages
5. Install the app to your workspace
6. Copy the "Bot User OAuth Token" (starts with `xoxb-`) for later use

## Step 2: Create a Security Alert Channel

1. Create a new private channel in Slack (e.g., `#security-alerts`)
2. Invite your bot to this channel
3. Copy the channel ID for later use (Right-click the channel > Copy Link > Extract the ID from the URL)

## Step 3: Deploy the Lambda Function

1. Clone or download this project
2. Install Serverless Framework if you haven't already:
   ```
   npm install -g serverless
   ```
3. Install the plugin for Python dependencies:
   ```
   npm install --save serverless-python-requirements
   ```
4. Create a `requirements.txt` file with these dependencies:
   ```
   slack_sdk
   boto3
   ```
5. Deploy the function using Serverless Framework:
   ```
   serverless deploy --param="slackBotToken=xoxb-your-token-here" --param="alertChannelId=C12345678"
   ```
   Replace the token and channel ID with your actual values

## Step 4: Configure Slack Events API

1. Note the API endpoint URL from the Serverless deployment output
2. Go back to your Slack App configuration at [api.slack.com/apps](https://api.slack.com/apps)
3. Navigate to "Event Subscriptions" and enable events
4. Enter your Lambda function URL in the "Request URL" field
   - Slack will send a verification challenge to your endpoint
   - If your Lambda is set up correctly, it will automatically respond and verify
5. Under "Subscribe to bot events", add the `message.channels` event
6. Save your changes

## Step 5: Test the Bot

1. In any public channel where your bot is present, post a message containing a fake password, like:
   ```
   password = "MyTestPassword123!"
   ```
2. Check your security alert channel for the notification
3. Verify that the user who posted the message received a direct message

## Customizing Password Detection

The bot comes with predefined patterns for detecting passwords, but you may want to customize these based on your organization's needs. Edit the `PASSWORD_PATTERNS` list in the Lambda function code to add or modify detection patterns.

## Monitoring and Maintenance

- Check CloudWatch Logs for any errors or issues with the Lambda function
- Periodically review the detection patterns to reduce false positives
- Consider adding additional security features like automatically deleting detected passwords (requires additional permissions)

## Security Considerations

- The bot intentionally does not log or store the actual passwords it detects
- AWS Secrets Manager is used to securely store the Slack token
- Consider implementing IP restrictions on your Lambda function for additional security

"""
Slack utilities for the Password Detector

This module handles all interactions with the Slack API, including
fetching channel information, sending alerts, and managing authentication.
"""

import os
import json
import logging
import boto3
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logger = logging.getLogger()

# Initialize the Slack client as a module-level variable
slack_client = None


def initialize_slack_client() -> WebClient:
    """
    Initialize the Slack WebClient with the bot token
    
    Returns:
        WebClient: Initialized Slack client
    """
    global slack_client
    if slack_client is not None:
        return slack_client
        
    # Get the Slack bot token
    token = get_slack_token()
    
    # Initialize the WebClient with the token
    slack_client = WebClient(token=token)
    return slack_client


def get_slack_token() -> str:
    """
    Get the Slack bot token from AWS Secrets Manager or environment variables
    
    Returns:
        str: The Slack bot token
    """
    # Check if we should bypass Secrets Manager for development/testing
    if os.environ.get('SLACK_BOT_TOKEN_DEV'):
        logger.warning("Using development Slack token from environment variables")
        return os.environ.get('SLACK_BOT_TOKEN_DEV')
    
    # Get configuration for Secrets Manager
    secret_name = os.environ.get('SECRET_NAME')
    region_name = os.environ.get('REGION_NAME')
    
    if not secret_name or not region_name:
        logger.error("SECRET_NAME or REGION_NAME environment variables not set")
        raise ValueError("Required environment variables are missing")
    
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        # Get the secret value
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        
        # Parse the secret JSON
        secret = json.loads(get_secret_value_response['SecretString'])
        
        # Return the Slack bot token
        if 'SLACK_BOT_TOKEN' not in secret:
            logger.error(f"SLACK_BOT_TOKEN not found in Secret {secret_name}")
            raise ValueError(f"SLACK_BOT_TOKEN not found in Secret {secret_name}")
            
        return secret['SLACK_BOT_TOKEN']
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e


def get_channel_info(channel_id: str) -> str:
    """
    Get channel name from Slack API
    
    Args:
        channel_id: The Slack channel ID
        
    Returns:
        str: The channel name
    """
    client = initialize_slack_client()
    try:
        response = client.conversations_info(channel=channel_id)
        return response['channel']['name']
    except SlackApiError as e:
        logger.error(f"Error getting channel info: {e}")
        return "unknown-channel"


def create_message_link(channel_id: str, message_ts: str) -> str:
    """
    Create a link to a Slack message
    
    Args:
        channel_id: The Slack channel ID
        message_ts: The message timestamp
        
    Returns:
        str: URL link to the message
    """
    # Format: https://workspace-name.slack.com/archives/CHANNEL_ID/p1234567890123456
    # The "p" + timestamp with the decimal removed creates a valid message link
    message_ts_clean = message_ts.replace('.', '')
    return f"https://slack.com/archives/{channel_id}/p{message_ts_clean}"


def send_alert(channel_id: str, user_id: str, message_ts: str, 
              channel_name: str, message_link: str) -> None:
    """
    Send security alert about potential password/credential detection
    
    Args:
        channel_id: The ID of the alert channel to send to
        user_id: The ID of the user who posted the credential
        message_ts: The timestamp of the message
        channel_name: The name of the channel where credential was detected
        message_link: Link to the message containing the credential
    """
    client = initialize_slack_client()
    
    try:
        # Don't attempt to send if alert channel ID is empty
        if not channel_id:
            logger.error("Alert channel ID is not configured")
            return
            
        # Create a rich message with link to the original message
        response = client.chat_postMessage(
            channel=channel_id,
            text=f"🚨 *SECURITY ALERT*: Potential password detected in a Slack message",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚨 *SECURITY ALERT*: Potential password detected in a public channel"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Channel:*\n#{channel_name}"
                        },
                        {
                            "type": "mrkdwn", 
                            "text": f"*Posted by:*\n<@{user_id}>"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{message_link}|View message in channel>"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "This message was flagged because it appears to contain credentials or passwords which should not be shared in public channels."
                        }
                    ]
                }
            ]
        )
        logger.info(f"Alert sent to channel {channel_id}")
        
        # Also send a direct message to the user who posted the potential password
        send_dm_to_user(user_id, message_link)
        
    except SlackApiError as e:
        logger.error(f"Error sending alert: {e}")


def send_dm_to_user(user_id: str, message_link: str) -> None:
    """
    Send a direct message to a user about credential detection
    
    Args:
        user_id: The Slack user ID to message
        message_link: Link to the message containing the credential
    """
    client = initialize_slack_client()
    
    try:
        client.chat_postMessage(
            channel=user_id,
            text="Security Notice: We detected what appears to be a password or credential in your recent Slack message. For security reasons, please remove it and share credentials through secure channels only.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔒 *Security Notice*: We detected what appears to be sensitive credentials in your recent Slack message."
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "For security reasons, please:\n• Delete the message containing the credentials immediately\n• Rotate any exposed credentials as soon as possible\n• Use a password manager or secrets manager for sharing credentials"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View My Message"
                            },
                            "url": message_link,
                            "style": "primary"
                        }
                    ]
                }
            ]
        )
        logger.info(f"DM sent to user {user_id}")
    except SlackApiError as e:
        logger.error(f"Error sending DM to user: {e}")


def join_channel(channel_id: str) -> bool:
    """
    Join a Slack channel
    
    Args:
        channel_id: The Slack channel ID
        
    Returns:
        bool: True if joined successfully, False otherwise
    """
    client = initialize_slack_client()
    try:
        client.conversations_join(channel=channel_id)
        logger.info(f"Successfully joined channel {channel_id}")
        return True
    except SlackApiError as e:
        logger.error(f"Error joining channel: {e}")
        return False


def handle_channel_membership_event(event: Dict[str, Any]) -> None:
    """
    Handle channel membership events (invites, joins, channel creation)
    
    Args:
        event: The Slack event data
    """
    try:
        # Check if auto-join is enabled
        auto_join = os.environ.get('AUTO_JOIN_CHANNELS', 'false').lower() == 'true'
        
        if event.get('type') == 'member_joined_channel':
            channel_id = event.get('channel')
            user_id = event.get('user')
            
            # Get bot's own user ID
            auth_response = initialize_slack_client().auth_test()
            bot_user_id = auth_response['user_id']
            
            # If the bot was added to a channel
            if user_id == bot_user_id:
                logger.info(f"Bot was added to channel {channel_id}")
                
        elif event.get('type') == 'channel_created' and auto_join:
            channel_data = event.get('channel', {})
            channel_id = channel_data.get('id')
            channel_name = channel_data.get('name')
            
            if channel_id:
                logger.info(f"Attempting to join newly created channel #{channel_name} ({channel_id})")
                if join_channel(channel_id):
                    # Send a welcome message to the channel
                    client = initialize_slack_client()
                    try:
                        client.chat_postMessage(
                            channel=channel_id,
                            text="👋 Hello! I'm the Secret Detector bot. I'll help keep this channel secure by detecting any accidentally shared passwords or credentials.",
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "👋 *Hello! I'm the Secret Detector bot*"
                                    }
                                },
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "I'll help keep this channel secure by monitoring for accidentally shared passwords or credentials. If I detect any sensitive information, I'll notify the security team and the message author."
                                    }
                                }
                            ]
                        )
                        logger.info(f"Sent welcome message to channel #{channel_name}")
                    except SlackApiError as e:
                        logger.error(f"Error sending welcome message: {e}")
                
    except Exception as e:
        logger.error(f"Error handling channel membership event: {e}")

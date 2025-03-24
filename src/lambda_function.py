"""
Main Lambda handler function for Slack Password Detector

This module contains the AWS Lambda handler function that processes
incoming Slack events, detects potential passwords or credentials,
and sends alerts when sensitive information is found.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Import other modules
from .password_detector import detect_passwords
from .slack_utils import get_channel_info, create_message_link, send_alert, handle_channel_membership_event
from .bedrock_analyzer import analyze_with_bedrock

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for Slack Password Detector
    
    Processes incoming Slack events, handles URL verification challenges,
    and scans messages for potential passwords or sensitive information.
    
    Args:
        event: The event dict from AWS Lambda
        context: The context object from AWS Lambda
        
    Returns:
        Dict containing statusCode and body for the Lambda response
    """
    logger.info("Password detection lambda triggered")
    
    try:
        # Parse the incoming event from Slack
        body = parse_event_body(event)
        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({'status': 'error', 'message': 'Invalid event format'})
            }
            
        # Handle Slack URL verification challenge
        if body.get('type') == 'url_verification':
            logger.info("Received URL verification challenge from Slack")
            return handle_url_verification(body)
        
        # Process Slack events
        if 'event' in body:
            process_slack_event(body['event'])
            
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'ok'})
        }
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'status': 'error', 'message': str(e)})
        }


def parse_event_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse the event body from the Lambda event
    
    Args:
        event: The Lambda event
        
    Returns:
        Parsed body as dict, or None if invalid
    """
    if 'body' not in event:
        return None
        
    if isinstance(event['body'], str):
        try:
            return json.loads(event['body'])
        except json.JSONDecodeError:
            logger.error("Failed to parse event body as JSON")
            return None
    else:
        return event['body']


def handle_url_verification(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Slack URL verification challenge
    
    Args:
        body: The parsed event body containing the challenge
        
    Returns:
        Response with the challenge value
    """
    challenge = body['challenge']
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'challenge': challenge})
    }


def process_slack_event(slack_event: Dict[str, Any]) -> None:
    """
    Process Slack events and check for sensitive information
    
    Args:
        slack_event: The Slack event to process
    """
    # Initialize variables
    message_data = {}
    channel_id = None
    user_id = None
    message_ts = None
    text = ""
    
    # Handle different event types
    event_type = slack_event.get('type')
    
    # Handle channel creation event
    if event_type == 'channel_created':
        channel_data = slack_event.get('channel', {})
        channel_id = channel_data.get('id')
        channel_name = channel_data.get('name')
        creator_id = channel_data.get('creator')
        
        if channel_id:
            logger.info(f"New channel created: #{channel_name} (ID: {channel_id}) by user {creator_id}")
            handle_channel_membership_event(slack_event)
        return
    
    # Handle member joined channel event
    if event_type == 'member_joined_channel':
        handle_channel_membership_event(slack_event)
        return
    
    if event_type == 'message':
        # Extract message details based on subtype
        message_details = extract_message_details(slack_event)
        if not message_details:
            return  # Skip processing for deleted messages or other invalid types
            
        channel_id, user_id, message_ts, text, message_data = message_details
        
        # Process messages in all channels except bot messages
        is_bot = slack_event.get('bot_id') is not None or (message_data and message_data.get('bot_id') is not None)
        
        if not is_bot and user_id and text:
            scan_and_alert(channel_id, user_id, message_ts, text)


def extract_message_details(slack_event: Dict[str, Any]) -> Optional[tuple]:
    """
    Extract message details based on message subtype
    
    Args:
        slack_event: The Slack event
        
    Returns:
        Tuple of (channel_id, user_id, message_ts, text, message_data) or None if we should skip
    """
    # Check if this is a message edit/update
    if slack_event.get('subtype') == 'message_changed':
        message_data = slack_event.get('message', {})
        channel_id = slack_event.get('channel')
        user_id = message_data.get('user')
        message_ts = message_data.get('ts')
        text = message_data.get('text', '')
        logger.info(f"Processing edited message from user {user_id} in channel {channel_id}")
        return channel_id, user_id, message_ts, text, message_data
    
    # Handle message deletion (skip processing)
    elif slack_event.get('subtype') == 'message_deleted':
        logger.info("Message was deleted, skipping password detection")
        return None
    
    # Regular new message
    else:
        channel_id = slack_event.get('channel')
        user_id = slack_event.get('user')
        message_ts = slack_event.get('ts')
        text = slack_event.get('text', '')
        if text == '':
            # If no text in the message, use the full event for debugging
            text = json.dumps(slack_event)
        logger.info(f"Processing new message from user {user_id} in channel {channel_id}")
        return channel_id, user_id, message_ts, text, {}


def scan_and_alert(channel_id: str, user_id: str, message_ts: str, text: str) -> None:
    """
    Scan message text for sensitive information and send alerts if found
    
    Args:
        channel_id: The Slack channel ID
        user_id: The Slack user ID
        message_ts: The message timestamp
        text: The message text to scan
    """
    try:
        # Get channel info
        channel_name = get_channel_info(channel_id)
        
        # Alert channel ID
        alert_channel_id = os.environ.get('ALERT_CHANNEL_ID', '')

        if alert_channel_id == channel_id:
            return

        # Create message link
        message_link = create_message_link(channel_id, message_ts)
        
        
        # Check if the message contains potential passwords
        USE_BEDROCK_AI = os.environ.get('USE_BEDROCK_AI', 'false').lower() == 'true'
        
        if USE_BEDROCK_AI:
            # Use AI-based detection
            is_sensitive = analyze_with_bedrock(text)
            if is_sensitive:
                logger.info(f"Bedrock AI detected sensitive information in channel {channel_id}")
                send_alert(alert_channel_id, user_id, message_ts, channel_name, message_link)
        else:
            # Use pattern-based detection
            detected = detect_passwords(text)
            if detected:
                logger.info(f"Pattern matching detected {len(detected)} potential credential(s) in channel {channel_id}")
                send_alert(alert_channel_id, user_id, message_ts, channel_name, message_link)
    except Exception as e:
        logger.error(f"Error during message scanning: {str(e)}")

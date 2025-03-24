"""
Tests for the Lambda handler function
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Import the functions to test
from src.lambda_function import (
    lambda_handler,
    parse_event_body,
    handle_url_verification,
    process_slack_event
)


@pytest.fixture
def slack_challenge_event():
    """Fixture for Slack URL verification challenge event"""
    return {
        'body': json.dumps({
            'type': 'url_verification',
            'challenge': 'test_challenge_token'
        })
    }


@pytest.fixture
def slack_message_event():
    """Fixture for Slack message event"""
    return {
        'body': json.dumps({
            'event': {
                'type': 'message',
                'user': 'U12345',
                'channel': 'C12345',
                'ts': '1234567890.123456',
                'text': 'Hello with password: secretpassword123',
                'channel_type': 'channel'
            }
        })
    }


def test_parse_event_body():
    """Test parsing of Lambda event body"""
    # Test with JSON string
    event = {'body': '{"key": "value"}'}
    body = parse_event_body(event)
    assert body == {'key': 'value'}
    
    # Test with dict body
    event = {'body': {'key': 'value'}}
    body = parse_event_body(event)
    assert body == {'key': 'value'}
    
    # Test with invalid JSON
    event = {'body': 'not json'}
    body = parse_event_body(event)
    assert body is None
    
    # Test with missing body
    event = {'not_body': 'value'}
    body = parse_event_body(event)
    assert body is None


def test_handle_url_verification():
    """Test handling of Slack URL verification challenge"""
    body = {'challenge': 'test_challenge_token'}
    response = handle_url_verification(body)
    
    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'
    assert json.loads(response['body']) == {'challenge': 'test_challenge_token'}


@patch('src.lambda_function.scan_and_alert')
@patch('src.lambda_function.extract_message_details')
def test_process_slack_event(mock_extract, mock_scan):
    """Test processing of Slack events"""
    # Mock the extract function to return test data
    mock_extract.return_value = ('C12345', 'U12345', '1234567890.123456', 'Test message', {})
    
    # Test with valid message event
    slack_event = {
        'type': 'message',
        'channel_type': 'channel',
        'user': 'U12345',
        'bot_id': None
    }
    
    process_slack_event(slack_event)
    
    # Verify extract was called
    mock_extract.assert_called_once_with(slack_event)
    
    # Verify scan was called with the right parameters
    mock_scan.assert_called_once_with('C12345', 'U12345', '1234567890.123456', 'Test message')


@patch('src.lambda_function.process_slack_event')
def test_lambda_handler_with_event(mock_process, slack_message_event):
    """Test lambda_handler with message event"""
    response = lambda_handler(slack_message_event, {})
    
    assert response['statusCode'] == 200
    assert json.loads(response['body']) == {'status': 'ok'}
    mock_process.assert_called_once()


def test_lambda_handler_with_challenge(slack_challenge_event):
    """Test lambda_handler with URL verification challenge"""
    response = lambda_handler(slack_challenge_event, {})
    
    assert response['statusCode'] == 200
    assert json.loads(response['body']) == {'challenge': 'test_challenge_token'}


@patch('src.lambda_function.parse_event_body')
def test_lambda_handler_with_error(mock_parse):
    """Test lambda_handler with error handling"""
    # Force an exception
    mock_parse.side_effect = Exception("Test error")
    
    response = lambda_handler({'body': {}}, {})
    
    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])
    assert 'Test error' in json.loads(response['body'])['message']

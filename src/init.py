"""
Slack Password Detector - AWS Lambda function

This package provides a Slack integration that detects when passwords,
credentials, or other sensitive information are shared in public Slack
channels, and sends alerts to security teams.

Main components:
- Password detection using regex patterns
- AI-based sensitive content detection using Amazon Bedrock
- Slack integration for alerts and notifications
- AWS Lambda handler for serverless deployment
"""

__version__ = '1.0.0'

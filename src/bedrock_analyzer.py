"""
Amazon Bedrock integration for detecting sensitive information

This module handles the integration with Amazon Bedrock for AI-based
analysis of text to detect potential credentials and sensitive information.
"""

import os
import json
import logging
import boto3
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()

# Global bedrock client
bedrock_runtime_client = None


def get_bedrock_client():
    """
    Get or initialize the Amazon Bedrock client
    
    Returns:
        boto3.client: The Bedrock runtime client
    """
    global bedrock_runtime_client
    
    if bedrock_runtime_client is not None:
        return bedrock_runtime_client
        
    # Get configuration
    region_name = os.environ.get('BEDROCK_REGION', 'us-east-1')
    
    # Initialize the Bedrock Runtime client
    try:
        bedrock_runtime_client = boto3.client(
            service_name='bedrock-runtime', 
            region_name=region_name
        )
        logger.info(f"Initialized Bedrock runtime client in region {region_name}")
        return bedrock_runtime_client
    except Exception as e:
        logger.error(f"Error initializing Bedrock client: {str(e)}")
        raise e


def analyze_with_bedrock(content: str) -> bool:
    """
    Use Amazon Bedrock to analyze text for sensitive information
    
    This function sends text to Amazon Bedrock AI models for analysis
    to determine if it contains passwords, credentials, or other sensitive
    information that should not be shared in public channels.
    
    Args:
        content: The text content to analyze
        
    Returns:
        bool: True if sensitive information is detected, False otherwise
    """
    try:
        # Get configuration
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')

        
        # Get the Bedrock client
        bedrock_runtime = get_bedrock_client()
        
        logger.info(f"Analyzing content with Bedrock model: {model_id}")
        
        # Create a clear prompt that focuses on sensitive information detection
        prompt = f"""
        Check the following content and determine if it contains any sensitive information such as:
        - Passwords
        - Secret keys
        - API tokens
        - Private keys
        - Credentials
        - Authentication tokens
        - Database connection strings
        - Personal access tokens
        
        Respond ONLY with "true" if sensitive information is detected, otherwise respond with "false".
        
        Content:
        {content}
        """
        
        # Prepare the appropriate request body based on the model provider
        if "anthropic" in model_id.lower():
            # Anthropic Claude models
            body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "top_k": 250,
                "temperature": 1,
                "top_p": 0.999,
                "messages": [
                {
                    "role": "user",
                    "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                    ]
                }
                ]
            }
        )
        elif "amazon" in model_id.lower():
            # Amazon Titan models
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 50,
                    "temperature": 0,
                    "topP": 0.9,
                    "stopSequences": []
                }
            })
        elif "ai21" in model_id.lower():
            # AI21 Jurassic models
            body = json.dumps({
                "prompt": prompt,
                "maxTokens": 50,
                "temperature": 0,
                "topP": 0.9,
            })
        else:
            # Default format
            body = json.dumps({
                "prompt": prompt,
                "max_tokens": 50, 
                "temperature": 0
            })
        
        # Make the API call to Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        # Read and parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the result based on the model type
        if "anthropic" in model_id.lower():
            answer = response_body.get('content', [{}])[0].get('text', '').strip().lower()
        elif "amazon" in model_id.lower():
            answer = response_body.get('results', [{}])[0].get('outputText', '').strip().lower()
        elif "ai21" in model_id.lower():
            answer = response_body.get('completions', [{}])[0].get('data', {}).get('text', '').strip().lower()
        else:
            answer = response_body.get('completion', '').strip().lower()
        
        logger.info(f"Bedrock analysis result: '{answer}'")
        
        # Determine if sensitive information was detected
        is_sensitive = "true" in answer.lower()
        
        return is_sensitive
        
    except Exception as e:
        logger.error(f"Error during Bedrock analysis: {str(e)}")
        # Fall back to true (sensitive) to be conservative in case of errors
        return True


def get_model_info() -> Dict[str, Any]:
    """
    Get information about available Bedrock models
    
    This function can be used for debugging or diagnostics to see
    which foundation models are available in the current region.
    
    Returns:
        Dict: Information about available Bedrock models
    """
    try:
        region_name = os.environ.get('BEDROCK_REGION', 'us-east-1')
        
        # Use the bedrock client (not runtime)
        bedrock_client = boto3.client(
            service_name='bedrock',
            region_name=region_name
        )
        
        # List available foundation models
        foundation_models = bedrock_client.list_foundation_models()
        
        # Get the currently configured model
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')
        
        # Find the configured model in the list
        matching_model = next(
            (model for model in foundation_models.get("modelSummaries", []) 
             if model.get("modelId") == model_id),
            None
        )
        
        return {
            "current_model": model_id,
            "matching_model": matching_model,
            "available_models": [
                {"id": model.get("modelId"), "name": model.get("modelName")}
                for model in foundation_models.get("modelSummaries", [])
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        return {"error": str(e)}

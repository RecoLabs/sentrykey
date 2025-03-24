"""
Password detection module for Slack Password Detector

This module contains the logic for detecting potential passwords and credentials
in text using regular expression patterns.
"""

import re
import logging
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger()

# Pattern for password detection
# This regex looks for common password patterns including:
# - Words like "password", "pwd", "pass" followed by separators and characters
# - Patterns like API keys (alphanumeric strings with typical lengths)
# - Credential-like strings that often match password formats
# - Service-specific credentials (AWS, GitHub, database connections, etc.)
# - Common credential format patterns used in various contexts
PASSWORD_PATTERNS = [
    # Basic password patterns
    r'password\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'passwd\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'pwd\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'pass\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'passw\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # API keys and tokens
    r'api[_-]?key\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'api[_-]?secret\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'secret[_-]?key\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'access[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'auth[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'bearer\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'client[_-]?secret\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # AWS specific patterns
    r'aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*[\'"`]?([A-Z0-9]{20})[\'"`]?',
    r'aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'arn:aws:secretsmanager:[^:]+:[^:]+:secret:[^\'"`\s]+',
    r'(AKIA[0-9A-Z]{16})',  # AWS Access Key ID pattern
    
    # Database connection strings
    r'(?:mongodb|postgres|mysql|jdbc|redis|ldap)://[^\s\'"`]+:[^\s\'"`]+@[^\s\'"`]+',
    r'(?:mongodb|postgres|mysql|jdbc|redis|ldap)://[^@]+@[^\s\'"`]+',
    r'connection[_-]?string\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'conn[_-]?str\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # GitHub and other service tokens
    r'github[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'gh[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'oauth[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'personal[_-]?access[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'slack[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'slack[_-]?webhook\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # Common credential formats
    r'(xox[pbaors]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{32})',  # Slack tokens
    r'(sk-[a-zA-Z0-9]{48})',  # OpenAI/API keys
    r'(gh[pousr]_[A-Za-z0-9_]{36,255})',  # GitHub tokens
    r'(key-[a-zA-Z0-9]{32,64})',  # Various API keys
    r'(sq0csp-[0-9A-Za-z\\-_]{43}|EAAA[a-zA-Z0-9]{60})',  # Square, Facebook tokens
    
    # General credential patterns
    r'[\'"`]((?:[a-zA-Z0-9_\-\.]+){16,64})[\'"`]',  # Long alphanumeric strings in quotes
    r'[\'"`]([a-zA-Z0-9+/]{40,})[\'"`]',  # Base64-like strings in quotes
    r'[\'"`]([a-zA-Z0-9]{32,})[\'"`]',  # Long alphanumeric strings (typical for hashes/keys)
    
    # Private keys/certificates
    r'-----BEGIN\s+(?:RSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----',
    r'-----BEGIN\s+CERTIFICATE-----',
    
    # SSH private key files
    r'id_rsa\b',
    r'id_dsa\b',
    r'id_ed25519\b',
    
    # Other specific credential types
    r'authorization:\s*Basic\s+[a-zA-Z0-9+/]+={0,2}',  # Basic auth headers
    r'authorization:\s*Bearer\s+[a-zA-Z0-9._\-]+',  # Bearer tokens
    r'refresh[_-]?token\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'session[_-]?(?:token|key|secret)\s*[=:]\s*[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # Environment variable patterns often containing credentials
    r'export\s+(\w+)=[\'"`]?([^\s\'"`]+)[\'"`]?',
    r'set\s+(\w+)=[\'"`]?([^\s\'"`]+)[\'"`]?',
    
    # IP address with port and potential credentials
    r'([a-zA-Z0-9_\.\-]+):([a-zA-Z0-9_\-]+)@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'
]


def detect_passwords(text: str) -> List[Dict[str, Any]]:
    """
    Detect potential passwords and credentials in text using regex patterns
    
    This function scans the provided text for patterns matching various types of
    credentials including passwords, API keys, tokens, and private keys.
    
    Args:
        text: The text content to scan for credentials
        
    Returns:
        A list of dictionaries containing information about detected credentials.
        Each dictionary includes the pattern that matched and the position in the text.
        The actual credential values are not included for security reasons.
    """
    detected_passwords = []
    
    # Loop through all password patterns
    for pattern in PASSWORD_PATTERNS:
        try:
            # Find all matches for the current pattern
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                # We don't want to include the actual password in our logs or alerts
                # Just noting that something matched our pattern
                detected_passwords.append({
                    'pattern': pattern,
                    'position': match.start(),
                    'pattern_type': categorize_pattern(pattern)
                })
        except Exception as e:
            # Log any errors with specific patterns but continue processing
            logger.error(f"Error matching pattern '{pattern}': {str(e)}")
    
    # Log summary of detections (without sensitive info)
    if detected_passwords:
        pattern_types = set(d['pattern_type'] for d in detected_passwords)
        logger.info(f"Detected {len(detected_passwords)} potential credentials of types: {', '.join(pattern_types)}")
    
    return detected_passwords


def categorize_pattern(pattern: str) -> str:
    """
    Categorize a regex pattern based on what type of credential it detects
    
    Args:
        pattern: The regex pattern string
        
    Returns:
        A string representing the category of the pattern
    """
    pattern_lower = pattern.lower()
    
    # Categorize based on pattern content
    if any(keyword in pattern_lower for keyword in ["password", "pwd", "pass"]):
        return "Password"
    elif "key" in pattern_lower:
        return "API/Secret Key"
    elif "token" in pattern_lower:
        return "Token"
    elif "aws" in pattern_lower:
        return "AWS Credential"
    elif any(db in pattern_lower for db in ["mongodb", "postgres", "mysql", "redis"]):
        return "Database Connection"
    elif "begin" in pattern_lower and "key" in pattern_lower:
        return "Private Key"
    elif "authorization" in pattern_lower:
        return "Authorization Header"
    elif any(service in pattern_lower for service in ["github", "slack", "openai"]):
        return "Service Token"
    else:
        return "Generic Credential"


def evaluate_risk(detected_items: List[Dict[str, Any]]) -> str:
    """
    Evaluate the risk level based on detected credential patterns
    
    Args:
        detected_items: List of detected credential items
        
    Returns:
        Risk level as string: "Low", "Medium", or "High"
    """
    if not detected_items:
        return "None"
        
    # Count unique pattern types
    pattern_types = set(item['pattern_type'] for item in detected_items)
    
    # Determine risk level
    if len(pattern_types) > 1:
        return "High"  # Multiple types of credentials detected
    elif any(p_type in ["Private Key", "AWS Credential", "Database Connection"] 
             for p_type in pattern_types):
        return "High"  # High-value credential types
    elif len(detected_items) > 2:
        return "Medium"  # Multiple instances of the same credential type
    else:
        return "Low"  # Single potential credential detected

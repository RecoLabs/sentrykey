#!/usr/bin/env python3
"""
CLI script to set up the Slack Secret Detector Lambda function in AWS.
This script handles:
1. Creating the IAM role and policies
2. Creating the AWS Secrets Manager secret for Slack token
3. Creating and configuring the Lambda function
4. Setting up API Gateway endpoint
"""

import argparse
import json
import time
import boto3
import os
import sys
import shutil
import zipfile
from botocore.exceptions import ClientError

def create_iam_role(iam_client):
    """Create or update IAM role for Lambda function"""
    try:
        role_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }
        
        try:
            # Try to create new role
            response = iam_client.create_role(
                RoleName='SlackSecretDetectorRole',
                AssumeRolePolicyDocument=json.dumps(role_policy)
            )
            print("✅ Created new IAM role")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print("ℹ️ IAM role exists, updating policies...")
                response = iam_client.get_role(RoleName='SlackSecretDetectorRole')
            else:
                raise
        
        # Detach any existing managed policies
        existing_policies = iam_client.list_attached_role_policies(
            RoleName='SlackSecretDetectorRole'
        )
        for policy in existing_policies.get('AttachedPolicies', []):
            iam_client.detach_role_policy(
                RoleName='SlackSecretDetectorRole',
                PolicyArn=policy['PolicyArn']
            )
        
        # Attach necessary policies
        policy_arns = [
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws:iam::aws:policy/SecretsManagerReadWrite'
        ]
        
        for policy_arn in policy_arns:
            iam_client.attach_role_policy(
                RoleName='SlackSecretDetectorRole',
                PolicyArn=policy_arn
            )
            
        # Update or add Bedrock policy if enabled
        try:
            iam_client.delete_role_policy(
                RoleName='SlackSecretDetectorRole',
                PolicyName='BedrockAccess'
            )
        except ClientError:
            pass  # Policy might not exist
            
        if args.use_bedrock:
            bedrock_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:ListFoundationModels",
                            "bedrock:InvokeModel",
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "AllowInference",
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:InvokeModel",
                            "bedrock:InvokeModelWithResponseStream",
                        ],
                        "Resource": [
                            f"arn:aws:bedrock:{args.region}::foundation-model/{args.bedrock_model}",
                            f"arn:aws:bedrock:{args.region}::foundation-model/anthropic.claude-*"
                        ]
                    }
                ]
            }
            
            iam_client.put_role_policy(
                RoleName='SlackSecretDetectorRole',
                PolicyName='BedrockAccess',
                PolicyDocument=json.dumps(bedrock_policy)
            )
            print("✅ Added Bedrock access policy")
            
        return response['Role']['Arn']
        
    except Exception as e:
        print(f"❌ Error managing IAM role: {str(e)}")
        raise

def create_secret(secrets_client, slack_token):
    """Create or update AWS Secrets Manager secret for Slack token"""
    try:
        secret_string = json.dumps({
            'SLACK_BOT_TOKEN': slack_token
        })
        
        try:
            # Try to create new secret
            response = secrets_client.create_secret(
                Name='slack-secret-detector-secrets',
                Description='Secrets for Slack Secret Detector',
                SecretString=secret_string
            )
            print("✅ Created new secret in AWS Secrets Manager")
            return response['ARN']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print("ℹ️ Secret exists, updating value...")
                # Update existing secret
                secrets_client.update_secret(
                    SecretId='slack-secret-detector-secrets',
                    Description='Secrets for Slack Secret Detector',
                    SecretString=secret_string
                )
                response = secrets_client.describe_secret(
                    SecretId='slack-secret-detector-secrets'
                )
                print("✅ Updated secret in AWS Secrets Manager")
                return response['ARN']
            raise
            
    except Exception as e:
        print(f"❌ Error managing secret: {str(e)}")
        raise

def create_lambda_package():
    """Create a ZIP package with all Lambda function code and dependencies"""
    try:
        # Create a temporary directory for packaging
        if os.path.exists('package'):
            shutil.rmtree('package')
        os.makedirs('package')
        
        # Copy all source files
        shutil.copytree('src', 'package/src')
        
        # Find Python executable
        python_cmd = None
        for cmd in ['python3.9', 'python3', 'python']:
            try:
                if os.system(f'{cmd} --version') == 0:
                    python_cmd = cmd
                    break
            except:
                continue
                
        if not python_cmd:
            raise Exception("Python 3.x not found. Please install Python 3.9 or later.")
        
        # Create and activate a virtual environment
        os.system(f'{python_cmd} -m venv package/venv')
        
        # Install dependencies
        if sys.platform == 'win32':
            pip_cmd = 'package\\venv\\Scripts\\pip'
            os.system(f'package\\venv\\Scripts\\python -m pip install --upgrade pip')
        else:
            pip_cmd = 'package/venv/bin/pip'
            os.system(f'package/venv/bin/python -m pip install --upgrade pip')
        
        # Install dependencies in the virtual environment
        os.system(f'{pip_cmd} install -r requirements.txt -t package/')
        
        # Remove unnecessary files
        if os.path.exists('package/venv'):
            shutil.rmtree('package/venv')
            
        # Create the ZIP file
        shutil.make_archive('lambda_package', 'zip', 'package')
        
        # Clean up
        shutil.rmtree('package')
        
        print("✅ Created Lambda deployment package")
        return True
        
    except Exception as e:
        print(f"❌ Error creating Lambda package: {str(e)}")
        if os.path.exists('package'):
            shutil.rmtree('package')
        if os.path.exists('lambda_package.zip'):
            os.remove('lambda_package.zip')
        return False

def get_latest_layer_version(lambda_client, layer_name):
    """Get the latest version of a Lambda layer"""
    try:
        response = lambda_client.list_layer_versions(
            LayerName=layer_name
        )
        if response['LayerVersions']:
            return response['LayerVersions'][0]['LayerVersionArn']
        return None
    except ClientError:
        return None

def wait_for_function_update_completion(lambda_client, function_name, max_retries=10):
    """Wait for Lambda function update to complete"""
    for i in range(max_retries):
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            if state == 'Active':
                return True
            elif state == 'Failed':
                print(f"❌ Function update failed: {response['Configuration'].get('StateReason', 'Unknown error')}")
                return False
            print(f"⏳ Waiting for function update to complete (attempt {i+1}/{max_retries})...")
            time.sleep(5)
        except ClientError as e:
            print(f"❌ Error checking function state: {str(e)}")
            return False
    print("❌ Timed out waiting for function update")
    return False

def create_log_group(logs_client, function_name):
    """Create CloudWatch log group for Lambda function"""
    try:
        log_group_name = f"/aws/lambda/{function_name}"
        logs_client.create_log_group(logGroupName=log_group_name)
        print(f"✅ Created CloudWatch log group: {log_group_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
            print(f"ℹ️ Log group already exists: {log_group_name}")
        else:
            raise

def ensure_layer_exists():
    """Ensure Lambda layer exists by running the layer builder script"""
    try:
        print("ℹ️ Creating Lambda layer...")
        
        # Check AWS credentials
        try:
            boto3.client('sts').get_caller_identity()
        except Exception as e:
            raise Exception(f"AWS credentials not configured correctly: {str(e)}")
            
        if not os.path.exists('setup/lambda_layer_builder.sh'):
            raise Exception("lambda_layer_builder.sh script not found")
            
        # Make the script executable
        os.chmod('setup/lambda_layer_builder.sh', 0o755)
        
        # Check Python installation
        python_cmd = None
        for cmd in ['python3.9', 'python3', 'python']:
            try:
                if os.system(f'{cmd} --version') == 0:
                    python_cmd = cmd
                    break
            except:
                continue
                
        if not python_cmd:
            raise Exception("Python 3.x not found. Please install Python 3.9 or later.")
            
        # Run the layer builder script with error output
        print("Running lambda_layer_builder.sh...")
        result = os.system('./setup/lambda_layer_builder.sh')
        if result != 0:
            raise Exception(f"Layer creation failed with exit code {result}")
            
        # Verify layer creation
        lambda_client = boto3.client('lambda', region_name=args.region)
        try:
            response = lambda_client.list_layer_versions(
                LayerName='slack-secret-detector-layer'
            )
            if not response.get('LayerVersions'):
                raise Exception("Layer was not created successfully in AWS")
            
            latest_version = response['LayerVersions'][0]
            print(f"✅ Layer created successfully - Version {latest_version['Version']}")
            print(f"   Layer ARN: {latest_version['LayerVersionArn']}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise Exception("Layer was not found in AWS after creation attempt")
            raise
            
    except Exception as e:
        print(f"❌ Error creating Lambda layer: {str(e)}")
        return False

def create_lambda_function(lambda_client, role_arn, secret_arn):
    """Create or update Lambda function"""
    try:
        # Create CloudWatch log group first
        logs_client = boto3.client('logs', region_name=args.region)
        create_log_group(logs_client, 'slack-secret-detector')
        
        # Ensure layer exists
        if not ensure_layer_exists():
            raise Exception("Failed to create Lambda layer")
        
        # Create the Lambda package
        if not create_lambda_package():
            raise Exception("Failed to create Lambda package")
            
        # Read the ZIP file
        with open('lambda_package.zip', 'rb') as f:
            lambda_code = f.read()
            
        environment = {
            'Variables': {
                'SECRET_NAME': 'slack-secret-detector-secrets',
                'REGION_NAME': args.region,
                'ALERT_CHANNEL_ID': args.alert_channel_id,
                'USE_BEDROCK_AI': str(args.use_bedrock).lower(),
                'AUTO_JOIN_CHANNELS': str(args.auto_join).lower(),
            }
        }
        
        if args.use_bedrock:
            environment['Variables']['BEDROCK_MODEL_ID'] = args.bedrock_model
            environment['Variables']['BEDROCK_REGION'] = args.region
            
        # Get the latest layer version
        layer_arn = get_latest_layer_version(lambda_client, 'slack-secret-detector-layer')
        if not layer_arn:
            raise Exception("Lambda layer not found after creation")
        layers = [layer_arn]
            
        try:
            # Try to get existing function
            lambda_client.get_function(FunctionName='slack-secret-detector')
            print("ℹ️ Lambda function exists, updating configuration...")
            
            # Wait for any in-progress updates to complete
            if not wait_for_function_update_completion(lambda_client, 'slack-secret-detector'):
                raise Exception("Function is in an invalid state")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Update function configuration
                    lambda_client.update_function_configuration(
                        FunctionName='slack-secret-detector',
                        Role=role_arn,
                        Environment=environment,
                        Layers=layers,
                        MemorySize=256,
                        Timeout=30
                    )
                    
                    # Wait for configuration update to complete
                    if not wait_for_function_update_completion(lambda_client, 'slack-secret-detector'):
                        raise Exception("Configuration update failed")
                    
                    # Update function code
                    response = lambda_client.update_function_code(
                        FunctionName='slack-secret-detector',
                        ZipFile=lambda_code,
                        Architectures=['arm64']
                    )
                    print("✅ Updated Lambda function")
                    break
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceConflictException' and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"⏳ Update in progress, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    raise
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("ℹ️ Creating new Lambda function...")
                # Create new function
                response = lambda_client.create_function(
                    FunctionName='slack-secret-detector',
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler='src.lambda.lambda_handler',
                    Code={'ZipFile': lambda_code},
                    Description='Detects secrets and sensitive information in Slack messages',
                    Timeout=30,
                    MemorySize=256,
                    Environment=environment,
                    Layers=layers,
                    Architectures=['arm64'],
                    PackageType='Zip'
                )
                print("✅ Created new Lambda function")
            else:
                raise
        
        # Clean up
        os.remove('lambda_package.zip')
        return response['FunctionArn']
        
    except Exception as e:
        # Clean up on any error
        if os.path.exists('lambda_package.zip'):
            os.remove('lambda_package.zip')
        print(f"❌ Error managing Lambda function: {str(e)}")
        raise

def create_function_url(lambda_client, function_name):
    """Create or update Lambda Function URL"""
    try:
        try:
            # Try to get existing URL config
            response = lambda_client.get_function_url_config(
                FunctionName=function_name
            )
            print("ℹ️ Function URL exists, updating configuration...")
            
            # Update URL configuration
            response = lambda_client.update_function_url_config(
                FunctionName=function_name,
                AuthType='NONE',
                Cors={
                    'AllowOrigins': ['*'],
                    'AllowMethods': ['POST'],
                    'AllowHeaders': ['content-type'],
                    'MaxAge': 300
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("ℹ️ Creating new Function URL...")
                # Create new URL configuration
                response = lambda_client.create_function_url_config(
                    FunctionName=function_name,
                    AuthType='NONE',
                    Cors={
                        'AllowOrigins': ['*'],
                        'AllowMethods': ['POST'],
                        'AllowHeaders': ['content-type'],
                        'MaxAge': 300
                    }
                )
            else:
                raise
                
        # Add resource-based policy to allow public access
        policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'lambda.amazonaws.com'},
                'Action': 'lambda:InvokeFunctionUrl',
                'Resource': f'arn:aws:lambda:{args.region}:{boto3.client("sts").get_caller_identity()["Account"]}:function:{function_name}',
                'Condition': {
                    'StringEquals': {'lambda:FunctionUrlAuthType': 'NONE'}
                }
            }]
        }
        
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='FunctionURLAllowPublicAccess',
                Action='lambda:InvokeFunctionUrl',
                Principal='*',
                FunctionUrlAuthType='NONE'
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceConflictException':
                raise
                
        print("✅ Created/Updated Function URL")
        return response['FunctionUrl']
        
    except Exception as e:
        print(f"❌ Error managing Function URL: {str(e)}")
        raise

def main(args):
    """Main function to set up the Secret Detector"""
    try:
        # Initialize AWS clients
        session = boto3.Session(region_name=args.region)
        iam = session.client('iam')
        secrets = session.client('secretsmanager')
        lambda_client = session.client('lambda')
        
        print("\n🚀 Setting up Slack Secret Detector...\n")
        
        # Create resources
        role_arn = create_iam_role(iam)
        time.sleep(10)  # Wait for IAM role to propagate
        
        secret_arn = create_secret(secrets, args.slack_token)
        lambda_arn = create_lambda_function(lambda_client, role_arn, secret_arn)
        function_url = create_function_url(lambda_client, 'slack-secret-detector')
        
        print("\n✨ Setup complete! Next steps:")
        print("1. Go to your Slack App settings at api.slack.com/apps")
        print("2. Navigate to 'Event Subscriptions'")
        print(f"3. Set the Request URL to: {function_url}")
        print("4. Subscribe to the following bot events:")
        print("   - message.channels")
        print("   - message.groups")
        print("   - message.im")
        print("   - message.mpim")
        print("   - member_joined_channel")
        print("   - channel_created")
        print("\n🔒 Your Secret Detector is ready to use!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up Slack Secret Detector in AWS')
    parser.add_argument('--region', default='us-east-1',
                      help='AWS region (default: us-east-1)')
    parser.add_argument('--slack-token', required=True,
                      help='Slack Bot User OAuth Token (xoxb-...)')
    parser.add_argument('--alert-channel-id', required=True,
                      help='Slack channel ID for security alerts')
    parser.add_argument('--use-bedrock', action='store_true',
                      help='Enable Amazon Bedrock AI detection')
    parser.add_argument('--bedrock-model',
                      default='us.anthropic.claude-3-5-haiku-20241022-v1:0',
                      help='Bedrock model ID for AI detection')
    parser.add_argument('--auto-join', action='store_true',
                      help='Enable automatic joining of channels')
    
    args = parser.parse_args()
    main(args) 
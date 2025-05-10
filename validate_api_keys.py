#!/usr/bin/env python3
"""
DMarket API Key Validator

This script validates your DMarket API keys and helps diagnose issues
when your balance shows $0.00. It checks:

1. If your API keys are in the correct format
2. If your API keys have the proper permissions
3. If your API keys can successfully authenticate with DMarket

If issues are found, it helps you regenerate/update your API keys.
"""

import os
import sys
import json
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Setup colored output for better readability
try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama
    
    def green(text): return f"{Fore.GREEN}{text}{Style.RESET_ALL}"
    def red(text): return f"{Fore.RED}{text}{Style.RESET_ALL}"
    def yellow(text): return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"
    def blue(text): return f"{Fore.BLUE}{text}{Style.RESET_ALL}"
    def magenta(text): return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"
except ImportError:
    # Fallback if colorama is not available
    def green(text): return text
    def red(text): return text
    def yellow(text): return text
    def blue(text): return text
    def magenta(text): return text

def load_env_vars() -> Dict[str, str]:
    """
    Load API keys from .env file or environment variables.
    
    Returns:
        Dict with API keys and URL
    """
    env_vars = {}
    
    # Try to load from .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print(f"{blue('Info:')} Loading API keys from .env file")
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        name, value = line.split("=", 1)
                        env_vars[name.strip()] = value.strip().strip("'\"")
        except Exception as e:
            print(f"{red('Error:')} Failed to load .env file: {e}")
    
    # Get from environment or use from .env
    api_keys = {
        "public_key": os.environ.get("DMARKET_PUBLIC_KEY", env_vars.get("DMARKET_PUBLIC_KEY", "")),
        "secret_key": os.environ.get("DMARKET_SECRET_KEY", env_vars.get("DMARKET_SECRET_KEY", "")),
        "api_url": os.environ.get("DMARKET_API_URL", env_vars.get("DMARKET_API_URL", "https://api.dmarket.com"))
    }
    
    return api_keys

def check_api_key_format(public_key: str, secret_key: str) -> Tuple[bool, list]:
    """
    Check if API keys have valid format.
    
    Args:
        public_key: DMarket public API key
        secret_key: DMarket secret API key
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check public key
    if not public_key:
        issues.append("Public key is empty")
    elif len(public_key) < 10:
        issues.append(f"Public key is too short ({len(public_key)} chars)")
    elif not all(c.isalnum() for c in public_key):
        issues.append("Public key contains invalid characters (should be alphanumeric)")
    
    # Check secret key
    if not secret_key:
        issues.append("Secret key is empty")
    elif len(secret_key) < 10:
        issues.append(f"Secret key is too short ({len(secret_key)} chars)")
    elif not all(c.isalnum() for c in secret_key):
        issues.append("Secret key contains invalid characters (should be alphanumeric)")
    
    return len(issues) == 0, issues

def test_api_auth(public_key: str, secret_key: str, endpoint: str = "/api/v1/account/balance") -> Dict[str, Any]:
    """
    Test API authentication by making a direct request.
    
    Args:
        public_key: DMarket public API key
        secret_key: DMarket secret API key
        endpoint: API endpoint to test
        
    Returns:
        Dict with test results
    """
    try:
        base_url = "https://api.dmarket.com"
        full_url = f"{base_url}{endpoint}"
        
        # Create timestamp for request
        timestamp = str(int(datetime.now().timestamp()))
        string_to_sign = f"GET{endpoint}{timestamp}"
        
        # Convert secret key to bytes if it's not already
        if isinstance(secret_key, bytes):
            secret_key_bytes = secret_key
        else:
            secret_key_bytes = secret_key.encode('utf-8')
        
        # Create signature
        signature = hmac.new(
            secret_key_bytes,
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Request headers
        headers = {
            "X-Api-Key": public_key,
            "X-Sign-Date": timestamp,
            "X-Request-Sign": f"dmar ed25519 {signature}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        print(f"{blue('Info:')} Testing API authentication with endpoint {endpoint}")
        
        # Send request
        response = requests.get(full_url, headers=headers, timeout=10)
        
        # Try to parse JSON response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"text": response.text}
        
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response_data
        }
        
    except Exception as e:
        print(f"{red('Error:')} Exception during API request: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def try_multiple_endpoints(public_key: str, secret_key: str) -> Dict[str, Any]:
    """
    Try multiple DMarket API endpoints to find one that works.
    
    Args:
        public_key: DMarket public API key
        secret_key: DMarket secret API key
        
    Returns:
        Dict with test results
    """
    endpoints = [
        # Новые эндпоинты согласно документации DMarket API
        "/api/v1/account/balance",
        "/api/v1/account/wallet/balance",
        "/exchange/v1/user/balance",
        # Старые эндпоинты
        "/account/v1/balance"
    ]
    
    results = {}
    success = False
    successful_endpoint = None
    
    for endpoint in endpoints:
        result = test_api_auth(public_key, secret_key, endpoint)
        results[endpoint] = result
        
        # If successful, save the endpoint and break
        if result.get("success"):
            print(f"{green('Success:')} API authentication successful with endpoint {endpoint}")
            success = True
            successful_endpoint = endpoint
            break
        else:
            status = result.get("status_code", "Error")
            print(f"{red('Failed:')} Endpoint {endpoint} returned status {status}")
    
    return {
        "success": success,
        "endpoint": successful_endpoint,
        "results": results
    }

def get_user_input_for_keys() -> Dict[str, str]:
    """
    Prompt user for new API keys.
    
    Returns:
        Dict with new API keys
    """
    print(f"\n{yellow('Please enter your DMarket API keys:')}")
    print("You can generate new keys at: https://dmarket.com/account/api")
    
    public_key = input("Public Key: ").strip()
    secret_key = input("Secret Key: ").strip()
    
    return {
        "public_key": public_key,
        "secret_key": secret_key,
        "api_url": "https://api.dmarket.com"
    }

def update_env_file(api_keys: Dict[str, str]) -> bool:
    """
    Update .env file with new API keys.
    
    Args:
        api_keys: Dict with API keys
        
    Returns:
        True if successful, False otherwise
    """
    try:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        env_vars = {}
        
        # Read existing file
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        name, value = line.split("=", 1)
                        env_vars[name.strip()] = value.strip()
        
        # Update API keys
        env_vars["DMARKET_PUBLIC_KEY"] = api_keys["public_key"]
        env_vars["DMARKET_SECRET_KEY"] = api_keys["secret_key"]
        env_vars["DMARKET_API_URL"] = api_keys["api_url"]
        
        # Write back to file
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# DMarket API configuration file\n")
            f.write("# Updated by validate_api_keys.py\n\n")
            
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        print(f"{green('Success:')} Updated .env file with new API keys")
        return True
        
    except Exception as e:
        print(f"{red('Error:')} Failed to update .env file: {e}")
        return False

def print_recommendations(has_format_issues: bool, auth_successful: bool):
    """
    Print recommendations based on test results.
    
    Args:
        has_format_issues: Whether there are format issues with keys
        auth_successful: Whether authentication was successful
    """
    print(f"\n{magenta('Recommendations:')}")
    
    if has_format_issues:
        print(f"1. {yellow('Your API keys have format issues.')}")
        print("   - Generate new API keys at https://dmarket.com/account/api")
        print("   - Make sure to copy the entire key without any extra spaces")
    
    if not auth_successful:
        if not has_format_issues:
            print(f"1. {yellow('Your API keys failed to authenticate.')}")
        print("   - Your API keys may be expired or revoked")
        print("   - Generate new API keys at https://dmarket.com/account/api")
        print("   - Make sure your account has API access enabled")
        print("   - Check that your account has sufficient permissions")
    
    if not has_format_issues and auth_successful:
        print(f"1. {green('Your API keys are valid and working correctly.')}")
        print("   - If you're still seeing $0.00 balance, check if you actually have funds in your DMarket account")
        print("   - You may need to add funds to your account")

def main():
    """Main function."""
    print("\n" + "=" * 70)
    print(" DMarket API Key Validator ".center(70, "="))
    print("=" * 70)
    
    # Load API keys
    api_keys = load_env_vars()
    
    # Check if we have API keys
    if not api_keys["public_key"] or not api_keys["secret_key"]:
        print(f"{yellow('Warning:')} No API keys found in environment or .env file")
        print("Would you like to enter API keys now? (y/n)")
        
        if input("> ").strip().lower() == "y":
            api_keys = get_user_input_for_keys()
        else:
            print(f"{red('Error:')} Cannot proceed without API keys")
            return
    
    # Check API key format
    print("\nChecking API key format...")
    valid_format, format_issues = check_api_key_format(api_keys["public_key"], api_keys["secret_key"])
    
    if valid_format:
        print(f"{green('Success:')} API keys have valid format")
    else:
        print(f"{red('Error:')} API keys have format issues:")
        for issue in format_issues:
            print(f"  - {issue}")
    
    # Test API authentication
    print("\nTesting API authentication...")
    auth_results = try_multiple_endpoints(api_keys["public_key"], api_keys["secret_key"])
    
    # Print recommendations
    print_recommendations(not valid_format, auth_results["success"])
    
    # Ask to update keys if there are issues
    if not valid_format or not auth_results["success"]:
        print("\nWould you like to update your API keys? (y/n)")
        
        if input("> ").strip().lower() == "y":
            new_keys = get_user_input_for_keys()
            update_env_file(new_keys)
            
            print("\nWould you like to verify the new keys? (y/n)")
            if input("> ").strip().lower() == "y":
                print(f"\n{magenta('Testing new API keys...')}")
                valid_format, format_issues = check_api_key_format(new_keys["public_key"], new_keys["secret_key"])
                
                if valid_format:
                    print(f"{green('Success:')} New API keys have valid format")
                    auth_results = try_multiple_endpoints(new_keys["public_key"], new_keys["secret_key"])
                    
                    if auth_results["success"]:
                        print(f"\n{green('Success:')} Your new API keys are working correctly!")
                        print(f"You can now run your DMarket bot with the new keys")
                    else:
                        print(f"\n{red('Error:')} Your new API keys still have authentication issues")
                        print(f"Please double-check your keys or contact DMarket support")
                else:
                    print(f"{red('Error:')} New API keys still have format issues")
    else:
        print(f"\n{green('Success:')} Your API keys are valid and working correctly!")

if __name__ == "__main__":
    main() 
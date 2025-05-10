#!/usr/bin/env python3
"""
DMarket API Key Diagnostic Script.
This script tests your DMarket API keys and performs various diagnostic checks
to identify why your balance might be showing $0.00.
"""

import os
import sys
import json
import asyncio
import logging
import hmac
import hashlib
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("python-dotenv package not installed. Environment variables must be set manually.")
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")

def get_api_keys() -> Dict[str, str]:
    """
    Get API keys from environment variables or user input.
    
    Returns:
        Dict with API keys information
    """
    public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
    api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")
    
    # If keys not found in environment, ask user
    if not public_key or not secret_key:
        logger.warning("API keys not found in environment variables")
        print("\nEnter your DMarket API keys:")
        public_key = input("Public key: ").strip()
        secret_key = input("Secret key: ").strip()
        
        # Validate that keys were entered
        if not public_key or not secret_key:
            logger.error("API keys are required for this test")
            sys.exit(1)
    
    return {
        "public_key": public_key,
        "secret_key": secret_key,
        "api_url": api_url
    }

def test_api_keys_sync(public_key: str, secret_key: str, endpoint: str = "/account/v1/balance") -> Dict[str, Any]:
    """
    Test API keys by making a direct synchronous request to DMarket API.
    
    Args:
        public_key: DMarket API public key
        secret_key: DMarket API secret key
        endpoint: API endpoint to test
        
    Returns:
        Dict with test results
    """
    base_url = "https://api.dmarket.com"
    full_url = f"{base_url}{endpoint}"
    
    try:
        # Create timestamp for request
        timestamp = str(int(datetime.now().timestamp()))
        string_to_sign = f"GET{endpoint}{timestamp}"
        
        # Create HMAC signature
        signature = hmac.new(
            secret_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Request headers
        headers = {
            "X-Api-Key": public_key,
            "X-Request-Sign": f"dmar ed25519 {signature}",
            "X-Sign-Date": timestamp
        }
        
        logger.info(f"Making direct API request to {endpoint}")
        
        # Send request
        response = requests.get(full_url, headers=headers)
        
        # Parse response
        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text}
        
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response_data
        }
        
        if response.status_code == 200:
            logger.info(f"API request successful: {endpoint}")
        else:
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            
        return result
    
    except Exception as e:
        logger.error(f"Exception during API request: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

def try_all_balance_endpoints(api_keys: Dict[str, str]) -> Dict[str, Any]:
    """
    Try all known balance endpoints to see which ones work.
    
    Args:
        api_keys: Dictionary with API keys
        
    Returns:
        Dict with test results for all endpoints
    """
    endpoints = [
        "/account/v1/user/balance",  # New endpoint
        "/v1/user/balance",          # Alternative endpoint
        "/account/v1/balance",       # Old endpoint
    ]
    
    results = {}
    
    for endpoint in endpoints:
        result = test_api_keys_sync(
            api_keys["public_key"],
            api_keys["secret_key"],
            endpoint
        )
        
        results[endpoint] = result
        
        if result["success"]:
            logger.info(f"✅ Successfully accessed endpoint: {endpoint}")
        else:
            logger.error(f"❌ Failed to access endpoint: {endpoint}")
    
    return results

def extract_balance_info(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract balance information from API responses.
    
    Args:
        results: Results from all endpoint tests
        
    Returns:
        Dict with balance information
    """
    balance_info = {
        "found_valid_endpoint": False,
        "found_balance_data": False,
        "balance_data": {},
        "raw_responses": {}
    }
    
    for endpoint, result in results.items():
        balance_info["raw_responses"][endpoint] = result
        
        if result.get("success", False):
            balance_info["found_valid_endpoint"] = True
            
            response = result.get("response", {})
            if response:
                # Check different balance formats
                
                # Format 1: usdAvailableToWithdraw
                if "usdAvailableToWithdraw" in response:
                    balance_info["found_balance_data"] = True
                    balance_info["balance_data"]["format"] = "usdAvailableToWithdraw"
                    
                    try:
                        usd_value = response["usdAvailableToWithdraw"]
                        if isinstance(usd_value, str):
                            balance = float(usd_value.replace('$', '').strip())
                        else:
                            balance = float(usd_value)
                            
                        balance_info["balance_data"]["balance"] = balance
                    except Exception as e:
                        balance_info["balance_data"]["parse_error"] = str(e)
                
                # Format 2: usd.amount
                elif "usd" in response:
                    balance_info["found_balance_data"] = True
                    
                    if isinstance(response["usd"], dict) and "amount" in response["usd"]:
                        balance_info["balance_data"]["format"] = "usd.amount"
                        try:
                            balance = float(response["usd"]["amount"]) / 100.0  # Convert cents to USD
                            balance_info["balance_data"]["balance"] = balance
                        except Exception as e:
                            balance_info["balance_data"]["parse_error"] = str(e)
                    elif isinstance(response["usd"], (int, float)):
                        balance_info["balance_data"]["format"] = "usd_numeric"
                        try:
                            balance = float(response["usd"]) / 100.0  # Typically in cents
                            balance_info["balance_data"]["balance"] = balance
                        except Exception as e:
                            balance_info["balance_data"]["parse_error"] = str(e)
                    elif isinstance(response["usd"], str):
                        balance_info["balance_data"]["format"] = "usd_string"
                        try:
                            balance = float(response["usd"].replace('$', '').strip())  # Typically in dollars
                            balance_info["balance_data"]["balance"] = balance
                        except Exception as e:
                            balance_info["balance_data"]["parse_error"] = str(e)
                
                # Format 3: totalBalance list
                elif "totalBalance" in response and isinstance(response["totalBalance"], list):
                    balance_info["found_balance_data"] = True
                    balance_info["balance_data"]["format"] = "totalBalance"
                    
                    for currency in response["totalBalance"]:
                        if isinstance(currency, dict) and currency.get("currency") == "USD":
                            try:
                                balance = float(currency.get("amount", 0)) / 100.0  # Typically in cents
                                balance_info["balance_data"]["balance"] = balance
                            except Exception as e:
                                balance_info["balance_data"]["parse_error"] = str(e)
                            break
                
                # Format 4: balance.usd
                elif "balance" in response and isinstance(response["balance"], dict) and "usd" in response["balance"]:
                    balance_info["found_balance_data"] = True
                    balance_info["balance_data"]["format"] = "balance.usd"
                    
                    usd_value = response["balance"]["usd"]
                    try:
                        if isinstance(usd_value, (int, float)):
                            balance = float(usd_value) / 100.0  # Typically in cents
                        elif isinstance(usd_value, str):
                            balance = float(usd_value.replace('$', '').strip())  # Typically in dollars
                        elif isinstance(usd_value, dict) and "amount" in usd_value:
                            balance = float(usd_value["amount"]) / 100.0  # Typically in cents
                        else:
                            balance = 0.0
                            
                        balance_info["balance_data"]["balance"] = balance
                    except Exception as e:
                        balance_info["balance_data"]["parse_error"] = str(e)
                
                # No known format
                else:
                    balance_info["balance_data"]["format"] = "unknown"
                    balance_info["balance_data"]["raw_response"] = response
    
    return balance_info

def analyze_issues(api_keys: Dict[str, str], results: Dict[str, Dict[str, Any]], balance_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze issues based on test results.
    
    Args:
        api_keys: API keys dict
        results: Test results for all endpoints
        balance_info: Extracted balance information
        
    Returns:
        Dict with analysis results
    """
    analysis = {
        "issues": [],
        "recommendations": [],
        "fatal_issues": False
    }
    
    # Check if we have a valid endpoint response
    if not balance_info["found_valid_endpoint"]:
        analysis["issues"].append("No valid API endpoint responses")
        analysis["fatal_issues"] = True
        
        # Check for 401 unauthorized errors
        unauthorized = False
        for endpoint, result in results.items():
            if result.get("status_code") == 401:
                unauthorized = True
                
        if unauthorized:
            analysis["issues"].append("API authentication failed (401 Unauthorized)")
            analysis["recommendations"].append("Verify your DMarket API keys are correct and have not expired")
            analysis["recommendations"].append("Generate new API keys in DMarket account settings")
        else:
            analysis["issues"].append("API endpoints are not accessible")
            analysis["recommendations"].append("Check your internet connection")
            analysis["recommendations"].append("Ensure DMarket API is not down for maintenance")
            analysis["recommendations"].append("Try running the script again later")
    
    # If we have valid endpoint responses but no balance data
    elif not balance_info["found_balance_data"]:
        analysis["issues"].append("API endpoints accessible but no balance data found")
        analysis["recommendations"].append("DMarket API response format may have changed")
        analysis["recommendations"].append("Contact DMarket support to verify your account status")
    
    # If we have balance data, check if the balance is zero
    elif balance_info.get("balance_data", {}).get("balance", 0) == 0:
        analysis["issues"].append("Balance is $0.00")
        analysis["recommendations"].append("Verify your DMarket account actually has funds")
        analysis["recommendations"].append("Check if your API keys have permission to read balance")
    
    # If there was an error parsing the balance
    if "parse_error" in balance_info.get("balance_data", {}):
        analysis["issues"].append(f"Error parsing balance data: {balance_info['balance_data']['parse_error']}")
        analysis["recommendations"].append("DMarket API response format may have changed")
    
    # Check public key format
    if not api_keys["public_key"] or len(api_keys["public_key"]) < 10:
        analysis["issues"].append("Public key seems too short or empty")
        analysis["recommendations"].append("Verify your public key is correct")
    
    # Check secret key format
    if not api_keys["secret_key"] or len(api_keys["secret_key"]) < 10:
        analysis["issues"].append("Secret key seems too short or empty")
        analysis["recommendations"].append("Verify your secret key is correct")
    
    return analysis

def print_summary(api_keys: Dict[str, str], results: Dict[str, Dict[str, Any]], balance_info: Dict[str, Any], analysis: Dict[str, Any]):
    """
    Print summary of diagnostic results.
    
    Args:
        api_keys: API keys dict
        results: Test results for all endpoints
        balance_info: Extracted balance information
        analysis: Analysis results
    """
    print("\n" + "=" * 80)
    print(" DMarket API Diagnostic Summary ".center(80, "="))
    print("=" * 80)
    
    # Print API key info (masked)
    public_key_masked = api_keys["public_key"][:5] + "..." + api_keys["public_key"][-3:] if len(api_keys["public_key"]) > 8 else "***"
    print(f"Public key: {public_key_masked}")
    print(f"API URL: {api_keys['api_url']}")
    
    # Print endpoint test results
    print("\nEndpoint Test Results:")
    for endpoint, result in results.items():
        status = "✅ Success" if result.get("success") else f"❌ Failed ({result.get('status_code', 'Error')})"
        print(f"  {endpoint}: {status}")
    
    # Print balance info
    print("\nBalance Information:")
    if balance_info["found_valid_endpoint"]:
        print("  Found valid API endpoint: Yes")
    else:
        print("  Found valid API endpoint: No")
        
    if balance_info["found_balance_data"]:
        print("  Found balance data: Yes")
        print(f"  Balance format: {balance_info['balance_data'].get('format', 'Unknown')}")
        
        if "balance" in balance_info["balance_data"]:
            balance = balance_info["balance_data"]["balance"]
            print(f"  Balance amount: ${balance:.2f}")
    else:
        print("  Found balance data: No")
    
    # Print issues and recommendations
    if analysis["issues"]:
        print("\nIssues Detected:")
        for i, issue in enumerate(analysis["issues"], 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNo issues detected.")
        
    if analysis["recommendations"]:
        print("\nRecommendations:")
        for i, rec in enumerate(analysis["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    # Print overall status
    print("\nOverall Status:")
    if not analysis["issues"]:
        print("✅ Your DMarket API configuration appears to be working correctly.")
    elif not analysis["fatal_issues"]:
        print("⚠️ Some issues were detected, but they might not prevent the bot from working.")
    else:
        print("❌ Critical issues were detected that will prevent the bot from working.")
        print("   Please follow the recommendations above to fix the issues.")
    
    print("\n" + "=" * 80)

def main():
    """Main function."""
    print("\n" + "=" * 80)
    print(" DMarket API Diagnostic Tool ".center(80, "="))
    print("=" * 80)
    print("This tool will test your DMarket API keys and help diagnose balance issues.\n")
    
    # Get API keys
    api_keys = get_api_keys()
    
    # Test all endpoints
    print("\nTesting all DMarket balance endpoints...")
    results = try_all_balance_endpoints(api_keys)
    
    # Extract and analyze balance information
    balance_info = extract_balance_info(results)
    analysis = analyze_issues(api_keys, results, balance_info)
    
    # Print summary
    print_summary(api_keys, results, balance_info, analysis)
    
    # Offer to update .env file if needed
    if "API authentication failed" in str(analysis["issues"]) or "key" in str(analysis["issues"]).lower():
        print("\nWould you like to update your API keys in the .env file? (y/n)")
        choice = input("> ").strip().lower()
        if choice == "y":
            print("Running create_env_file.py to update your .env file...")
            os.system("python create_env_file.py")

if __name__ == "__main__":
    main() 
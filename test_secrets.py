#!/usr/bin/env python3
"""
Test script to verify GitHub secrets are working
"""

import os
import sys

def test_environment_variables():
    """Test that environment variables are properly set."""
    print("🔐 Testing GitHub Secrets Configuration")
    print("=" * 50)
    
    # Test required environment variables
    required_vars = [
        'GUARDRAILS_API_KEY',
        'JWT_SECRET', 
        'GRAFANA_PASSWORD',
        'GRAFANA_SECRET_KEY',
        'DOCKER_USERNAME',
        'DOCKER_PASSWORD'
    ]
    
    all_present = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_present = False
    
    print("\n" + "=" * 50)
    
    if all_present:
        print("🎉 All secrets are properly configured!")
        return True
    else:
        print("⚠️  Some secrets are missing. Please check your GitHub repository settings.")
        return False

def test_api_key_format():
    """Test that the API key has the correct format."""
    api_key = os.getenv('GUARDRAILS_API_KEY')
    if api_key and api_key.startswith('gr_'):
        print("✅ API Key format is correct (starts with 'gr_')")
        return True
    else:
        print("❌ API Key format is incorrect (should start with 'gr_')")
        return False

def test_docker_credentials():
    """Test that Docker credentials are set."""
    docker_username = os.getenv('DOCKER_USERNAME')
    docker_password = os.getenv('DOCKER_PASSWORD')
    
    if docker_username and docker_password:
        print("✅ Docker credentials are configured")
        return True
    else:
        print("❌ Docker credentials are missing")
        return False

if __name__ == "__main__":
    print("Testing GitHub Secrets Configuration...")
    print()
    
    # Run all tests
    env_test = test_environment_variables()
    api_test = test_api_key_format()
    docker_test = test_docker_credentials()
    
    print("\n" + "=" * 50)
    
    if env_test and api_test and docker_test:
        print("🎉 All tests passed! Your secrets are properly configured.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check your configuration.")
        sys.exit(1)

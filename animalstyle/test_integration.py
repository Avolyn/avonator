#!/usr/bin/env python3
"""
Test script for minimal LlamaGuard-7b service
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any


async def test_service():
    """Test the LlamaGuard-7b service"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Minimal LlamaGuard-7b Service")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test health check
            print("🔍 Testing health check...")
            health_response = await client.get(f"{base_url}/health")
            health_data = health_response.json()
            print(f"Health: {health_data['status']}")
            print(f"Model loaded: {health_data['model_loaded']}")
            print(f"Device: {health_data['device']}")
            
            if health_data['status'] != 'healthy':
                print("❌ Service is not healthy")
                return False
            
            # Test single validation
            print("\n🔍 Testing single validation...")
            test_cases = [
                {
                    "text": "Hello, how are you today?",
                    "context": "user_input",
                    "expected_safe": True
                },
                {
                    "text": "This is a test of potentially harmful content.",
                    "context": "user_input", 
                    "expected_safe": None
                },
                {
                    "text": "I hope you have a wonderful day!",
                    "context": "ai_output",
                    "expected_safe": True
                }
            ]
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\nTest {i}: {test_case['text'][:30]}...")
                
                response = await client.post(
                    f"{base_url}/validate",
                    json={
                        "text": test_case["text"],
                        "context": test_case["context"]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Safe: {result['is_safe']}")
                    print(f"🎯 Confidence: {result['confidence']:.2f}")
                    print(f"⚠️  Violations: {len(result['violations'])}")
                    
                    if result['violations']:
                        for violation in result['violations']:
                            print(f"   - {violation}")
                    
                    # Check expectation
                    if test_case['expected_safe'] is not None:
                        if result['is_safe'] == test_case['expected_safe']:
                            print("✅ Matches expectation")
                        else:
                            print("⚠️  Doesn't match expectation")
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
            
            # Test batch validation
            print("\n🔍 Testing batch validation...")
            batch_texts = [
                "This is a safe message for testing.",
                "Another safe message for batch processing.",
                "This might be problematic content for testing."
            ]
            
            batch_response = await client.post(
                f"{base_url}/validate/batch",
                json={"texts": batch_texts}
            )
            
            if batch_response.status_code == 200:
                results = batch_response.json()
                print(f"✅ Batch validation completed: {len(results)} results")
                
                for i, result in enumerate(results):
                    print(f"  Result {i+1}: Safe={result['is_safe']}, Confidence={result['confidence']:.2f}")
            else:
                print(f"❌ Batch validation error: {batch_response.status_code}")
            
            print("\n🎉 All tests completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False


async def test_client_integration():
    """Test the client integration example"""
    print("\n🔍 Testing client integration...")
    
    try:
        from client_example import LlamaGuardClient, validate_user_input, validate_ai_output
        
        # Test client
        client = LlamaGuardClient()
        
        # Test health check
        health = await client.health_check()
        print(f"Client health check: {health['status']}")
        
        # Test validation functions
        user_safe = await validate_user_input("Hello, how are you?")
        print(f"User input validation: {user_safe}")
        
        ai_safe = await validate_ai_output("I'm doing well, thank you!")
        print(f"AI output validation: {ai_safe}")
        
        await client.close()
        print("✅ Client integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Client integration test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Minimal LlamaGuard-7b Service Tests")
    print("Make sure the service is running on http://localhost:8000")
    print()
    
    # Test service endpoints
    service_ok = await test_service()
    
    # Test client integration
    client_ok = await test_client_integration()
    
    if service_ok and client_ok:
        print("\n✅ All tests passed! Service is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the service configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

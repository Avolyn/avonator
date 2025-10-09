"""
Example usage of the FastAPI Guardrails Service

This script demonstrates how to use the FastAPI-based guardrails service
with different validation scenarios and guardrail configurations.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Service configuration
BASE_URL = "http://localhost:8000"
API_KEY = "default-api-key-change-in-production"

class GuardrailsClient:
    """Client for interacting with the FastAPI Guardrails Service."""
    
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def validate_text(
        self, 
        text: str, 
        guardrail_name: str = "default",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate text using the guardrails service."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/guardrails/validate",
                headers=self.headers,
                json={
                    "text": text,
                    "guardrail_name": guardrail_name,
                    "context": context or {}
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_health(self) -> Dict[str, Any]:
        """Get service health status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/v1/guardrails/health")
            response.raise_for_status()
            return response.json()
    
    async def get_configs(self) -> Dict[str, Any]:
        """Get available guardrail configurations."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/guardrails/configs",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

async def demonstrate_validation_scenarios():
    """Demonstrate various validation scenarios."""
    client = GuardrailsClient()
    
    print("🚀 FastAPI Guardrails Service Demo")
    print("=" * 50)
    
    # Check service health
    print("\n1. Checking service health...")
    try:
        health = await client.get_health()
        print(f"✅ Service Status: {health['status']}")
        print(f"📊 Models Loaded: {health['models_loaded']}")
        print(f"⏱️  Uptime: {health['uptime_seconds']:.2f} seconds")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Get available configurations
    print("\n2. Available guardrail configurations...")
    try:
        configs = await client.get_configs()
        print("📋 Available guardrails:")
        for name, config in configs['guardrails'].items():
            print(f"  - {name}: {config['description']}")
    except Exception as e:
        print(f"❌ Failed to get configs: {e}")
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Normal Text",
            "text": "Hello, this is a normal message. How are you today?",
            "guardrail": "default"
        },
        {
            "name": "Toxic Content",
            "text": "You are such a stupid idiot and I hate you!",
            "guardrail": "default"
        },
        {
            "name": "Very Negative Sentiment",
            "text": "This is absolutely terrible and I'm extremely disappointed with everything.",
            "guardrail": "default"
        },
        {
            "name": "Text with PII",
            "text": "My name is John Smith and my email is john.smith@example.com. Call me at 555-123-4567.",
            "guardrail": "strict"
        },
        {
            "name": "Long Text",
            "text": "This is a very long text that exceeds the normal length limits. " * 50,
            "guardrail": "default"
        },
        {
            "name": "Customer Service Message",
            "text": "I'm having issues with my order #12345. The product arrived damaged and I need a refund.",
            "guardrail": "customer_service"
        }
    ]
    
    print("\n3. Running validation scenarios...")
    print("-" * 50)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Text: {scenario['text'][:100]}{'...' if len(scenario['text']) > 100 else ''}")
        print(f"   Guardrail: {scenario['guardrail']}")
        
        try:
            result = await client.validate_text(
                text=scenario['text'],
                guardrail_name=scenario['guardrail']
            )
            
            print(f"   ✅ Status: {result['status']}")
            print(f"   🎯 Valid: {result['valid']}")
            print(f"   ⏱️  Execution Time: {result.get('execution_time_ms', 0):.2f}ms")
            
            if result['validations']:
                print("   📊 Validation Results:")
                for validation in result['validations']:
                    status_emoji = "✅" if validation['status'] == "pass" else "❌"
                    confidence = f" (confidence: {validation['confidence']:.3f})" if validation['confidence'] else ""
                    print(f"     {status_emoji} {validation['validator_name']}: {validation['status']}{confidence}")
                    print(f"        {validation['message']}")
            
            if result.get('processed_text') and result['processed_text'] != scenario['text']:
                print(f"   🔄 Processed Text: {result['processed_text'][:100]}{'...' if len(result['processed_text']) > 100 else ''}")
                
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")

async def demonstrate_batch_validation():
    """Demonstrate batch validation capabilities."""
    client = GuardrailsClient()
    
    print("\n4. Batch Validation Demo")
    print("-" * 30)
    
    texts = [
        "This is a normal message.",
        "You are an idiot!",
        "I love this product, it's amazing!",
        "My name is Alice and my phone is 555-1234.",
        "This is a very long message that might exceed length limits. " * 20
    ]
    
    print(f"Validating {len(texts)} texts...")
    
    tasks = []
    for i, text in enumerate(texts):
        task = client.validate_text(text, "default")
        tasks.append((i, task))
    
    results = []
    for i, task in tasks:
        try:
            result = await task
            results.append((i, result))
        except Exception as e:
            results.append((i, {"error": str(e)}))
    
    print("\nBatch Results:")
    for i, result in results:
        if "error" in result:
            print(f"  {i+1}. ❌ Error: {result['error']}")
        else:
            status_emoji = "✅" if result['valid'] else "❌"
            print(f"  {i+1}. {status_emoji} Valid: {result['valid']} ({result.get('execution_time_ms', 0):.1f}ms)")

async def demonstrate_different_guardrails():
    """Demonstrate different guardrail configurations."""
    client = GuardrailsClient()
    
    print("\n5. Different Guardrail Configurations")
    print("-" * 40)
    
    test_text = "This is a somewhat negative message that might be considered toxic by some standards."
    
    guardrails = ["default", "strict", "permissive", "content_moderation"]
    
    for guardrail in guardrails:
        print(f"\nTesting with '{guardrail}' guardrail:")
        try:
            result = await client.validate_text(test_text, guardrail)
            print(f"  Valid: {result['valid']}")
            print(f"  Validations: {len(result['validations'])}")
            for validation in result['validations']:
                print(f"    - {validation['validator_name']}: {validation['status']}")
        except Exception as e:
            print(f"  Error: {e}")

async def main():
    """Main demonstration function."""
    try:
        await demonstrate_validation_scenarios()
        await demonstrate_batch_validation()
        await demonstrate_different_guardrails()
        
        print("\n🎉 Demo completed successfully!")
        print("\nTo start the service, run:")
        print("  python fastapi_guardrails.py")
        print("\nOr with uvicorn:")
        print("  uvicorn fastapi_guardrails:app --host 0.0.0.0 --port 8000 --reload")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the FastAPI service is running on http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(main())

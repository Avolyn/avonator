"""
Example client for LlamaGuard-7b API
Shows how to integrate with existing GenAI solutions
"""

import httpx
import asyncio
from typing import List, Optional, Dict, Any


class LlamaGuardClient:
    """Simple client for LlamaGuard-7b API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def validate_text(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Validate a single text"""
        try:
            response = await self.client.post(
                f"{self.base_url}/validate",
                json={"text": text, "context": context}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "is_safe": False}
    
    async def validate_batch(self, texts: List[str], contexts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Validate multiple texts"""
        try:
            response = await self.client.post(
                f"{self.base_url}/validate/batch",
                json={"texts": texts, "contexts": contexts}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return [{"error": str(e), "is_safe": False} for _ in texts]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()


# Example integration functions for GenAI solutions
async def validate_user_input(text: str, context: str = None) -> bool:
    """Validate user input before processing"""
    client = LlamaGuardClient()
    try:
        result = await client.validate_text(text, context)
        return result.get("is_safe", False)
    finally:
        await client.close()


async def validate_ai_output(text: str, context: str = None) -> bool:
    """Validate AI output before sending to user"""
    client = LlamaGuardClient()
    try:
        result = await client.validate_text(text, context)
        return result.get("is_safe", False)
    finally:
        await client.close()


async def validate_conversation_turn(user_input: str, ai_output: str) -> Dict[str, bool]:
    """Validate both user input and AI output"""
    client = LlamaGuardClient()
    try:
        # Validate both in parallel
        user_task = client.validate_text(user_input, "user_input")
        ai_task = client.validate_text(ai_output, "ai_output")
        
        user_result, ai_result = await asyncio.gather(user_task, ai_task)
        
        return {
            "user_input_safe": user_result.get("is_safe", False),
            "ai_output_safe": ai_result.get("is_safe", False),
            "conversation_safe": user_result.get("is_safe", False) and ai_result.get("is_safe", False)
        }
    finally:
        await client.close()


# Example usage
async def main():
    """Example usage of the client"""
    client = LlamaGuardClient()
    
    try:
        # Health check
        health = await client.health_check()
        print(f"Service health: {health}")
        
        # Single text validation
        result = await client.validate_text("Hello, how are you?")
        print(f"Validation result: {result}")
        
        # Batch validation
        texts = [
            "This is a safe message",
            "This might be problematic content"
        ]
        results = await client.validate_batch(texts)
        print(f"Batch results: {results}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Load testing with Locust for FastAPI Guardrails Service
"""

from locust import HttpUser, task, between
import random
import json

class GuardrailsUser(HttpUser):
    """Locust user class for load testing the guardrails service."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        self.api_key = "test-api-key"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Sample texts for testing
        self.sample_texts = [
            "This is a normal test message for load testing.",
            "Hello, how are you today? I hope you're doing well.",
            "This is a longer message that contains more text for testing purposes.",
            "I would like to know more about your services and pricing.",
            "Thank you for your help and support with this matter.",
            "This is a test message with some special characters: @#$%^&*()",
            "I'm interested in learning more about your products and services.",
            "Can you please provide more information about this topic?",
            "This is another test message for the load testing scenario.",
            "I appreciate your time and assistance with this request."
        ]
        
        # Guardrail configurations to test
        self.guardrails = ["default", "strict", "permissive", "content_moderation"]
    
    @task(3)
    def validate_single_text(self):
        """Test single text validation endpoint."""
        text = random.choice(self.sample_texts)
        guardrail = random.choice(self.guardrails)
        
        payload = {
            "text": text,
            "guardrail_name": guardrail
        }
        
        with self.client.post(
            "/v1/guardrails/validate",
            headers=self.headers,
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(f"Validation failed: {data.get('message')}")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def validate_batch_texts(self):
        """Test batch validation endpoint."""
        # Select 3-5 random texts
        num_texts = random.randint(3, 5)
        texts = random.sample(self.sample_texts, num_texts)
        guardrail = random.choice(self.guardrails)
        
        payload = {
            "texts": texts,
            "guardrail_name": guardrail
        }
        
        with self.client.post(
            "/v1/guardrails/validate/batch",
            headers=self.headers,
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(f"Batch validation failed: {data.get('message')}")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        with self.client.get(
            "/v1/guardrails/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Service unhealthy: {data.get('status')}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_metrics(self):
        """Test metrics endpoint."""
        with self.client.get(
            "/metrics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                if "guardrails_requests_total" in response.text:
                    response.success()
                else:
                    response.failure("Metrics not found in response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_configs(self):
        """Test configs endpoint."""
        with self.client.get(
            "/v1/guardrails/configs",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "guardrails" in data and "available_models" in data:
                    response.success()
                else:
                    response.failure("Invalid configs response")
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"HTTP {response.status_code}")

class ToxicContentUser(HttpUser):
    """User class for testing with potentially toxic content."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Called when a user starts."""
        self.api_key = "test-api-key"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Sample texts that might trigger validation failures
        self.toxic_texts = [
            "This is a normal message.",
            "You are such an idiot!",
            "I hate this so much!",
            "This is absolutely terrible.",
            "You're stupid and worthless.",
            "I love this product!",
            "This is amazing and wonderful.",
            "Thank you for your help.",
            "I'm very disappointed with this.",
            "This is the worst thing ever."
        ]
    
    @task(5)
    def validate_toxic_content(self):
        """Test validation with potentially toxic content."""
        text = random.choice(self.toxic_texts)
        
        payload = {
            "text": text,
            "guardrail_name": "strict"  # Use strict guardrail
        }
        
        with self.client.post(
            "/v1/guardrails/validate",
            headers=self.headers,
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Both success and failure are valid responses
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")

class HighLoadUser(HttpUser):
    """User class for high-load testing."""
    
    wait_time = between(0.1, 0.5)  # Very short wait time for high load
    
    def on_start(self):
        """Called when a user starts."""
        self.api_key = "test-api-key"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Short texts for rapid testing
        self.short_texts = [
            "Test message 1",
            "Test message 2", 
            "Test message 3",
            "Test message 4",
            "Test message 5"
        ]
    
    @task(10)
    def rapid_validation(self):
        """Rapid validation requests for high load testing."""
        text = random.choice(self.short_texts)
        
        payload = {
            "text": text,
            "guardrail_name": "default"
        }
        
        with self.client.post(
            "/v1/guardrails/validate",
            headers=self.headers,
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code in [200, 429]:  # Accept both success and rate limiting
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

# Locust configuration
class WebsiteUser(HttpUser):
    """Main user class that combines different behaviors."""
    
    tasks = [GuardrailsUser, ToxicContentUser]
    wait_time = between(1, 3)

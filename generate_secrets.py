#!/usr/bin/env python3
"""
Generate secure secrets for GitHub repository
"""

import secrets
import string

def generate_secret(length=32):
    """Generate a secure random secret."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_key():
    """Generate a secure API key."""
    return f"gr_{generate_secret(40)}"

def generate_jwt_secret():
    """Generate a JWT secret."""
    return generate_secret(64)

def generate_grafana_secret():
    """Generate a Grafana secret key."""
    return generate_secret(32)

if __name__ == "__main__":
    print("🔐 Generated Secure Secrets for GitHub Repository")
    print("=" * 60)
    print()
    
    print("📋 Copy these values to your GitHub Secrets:")
    print()
    
    print(f"GUARDRAILS_API_KEY = {generate_api_key()}")
    print(f"JWT_SECRET = {generate_jwt_secret()}")
    print(f"GRAFANA_PASSWORD = {generate_secret(16)}")
    print(f"GRAFANA_SECRET_KEY = {generate_grafana_secret()}")
    print()
    
    print("🐳 Docker Hub Credentials:")
    print("(You need to provide these manually)")
    print("DOCKER_USERNAME = your-dockerhub-username")
    print("DOCKER_PASSWORD = your-dockerhub-password-or-token")
    print()
    
    print("📝 Instructions:")
    print("1. Go to your GitHub repository settings")
    print("2. Navigate to 'Secrets and variables' > 'Actions'")
    print("3. Click 'New repository secret' for each value above")
    print("4. Use the generated values as the secret values")
    print()
    
    print("⚠️  Important Security Notes:")
    print("- Never commit these secrets to your repository")
    print("- Use strong, unique passwords")
    print("- Rotate secrets regularly")
    print("- Consider using GitHub's encrypted secrets for sensitive data")

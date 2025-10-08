
1. **Create ECR Repositories**
```bash
aws ecr create-repository --repository-name guardrails-api
aws ecr create-repository --repository-name llm-chatbot
```

2. **Build and Push Images**
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push guardrails API
docker build -t guardrails-api ./guardrails_api
docker tag guardrails-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/guardrails-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/guardrails-api:latest
```

3. **Create ECS Task Definition**
```json
{
  "family": "guardrails-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "guardrails-api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/guardrails-api:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GUARDRAILS_API_KEY",
          "value": "your-production-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/guardrails-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"

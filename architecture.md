# Modular API Architecture for Guardrails Component

To ensure API plug-and-play functionality and easy replaceability, the guardrails component will be designed as a standalone microservice with a well-defined REST API. This service will act as a wrapper around the Guardrails AI framework, allowing for flexible integration with any LLM chatbot.

## 1. Core Principles

*   **Statelessness**: Each API request should contain all necessary information, making the service scalable and resilient.
*   **Modularity**: The internal implementation (Guardrails AI) can be swapped out without affecting the external API interface.
*   **Simplicity**: The API should be easy to understand and use for LLM chatbot developers.
*   **Configurability**: Guardrails (validators) should be easily configurable, ideally via a simple configuration file or environment variables.

## 2. API Endpoints

The primary functionality required is to validate LLM inputs and outputs. Therefore, a single, flexible endpoint is proposed.

### `POST /v1/guardrails/validate`

This endpoint will be used to send text (either LLM input or output) for validation against configured guardrails.

#### Request Body (JSON)

```json
{
    "text": "string",
    "context": {
        "user_id": "string",
        "session_id": "string",
        "metadata": {}
    },
    "guardrail_name": "string" 
}
```

*   `text` (required): The text content to be validated by the guardrails.
*   `context` (optional): A dictionary containing contextual information that might be useful for certain validators (e.g., user ID, session ID, or other metadata).
*   `guardrail_name` (optional): The specific guardrail configuration to use. If not provided, a default guardrail will be applied.

#### Response Body (JSON)

```json
{
    "status": "success" | "failure",
    "message": "string",
    "valid": true | false,
    "validations": [
        {
            "validator_name": "string",
            "status": "pass" | "fail",
            "message": "string",
            "on_fail_action": "string" 
        }
    ],
    "processed_text": "string" 
}
```

*   `status`: Overall status of the validation (`success` if the guardrail ran without errors, `failure` if an internal error occurred).
*   `message`: A general message about the validation result.
*   `valid`: `true` if all guardrails passed, `false` otherwise.
*   `validations`: An array of objects, each detailing the result of a specific validator applied.
    *   `validator_name`: The name of the validator.
    *   `status`: `pass` or `fail` for that specific validator.
    *   `message`: A message from the validator, especially if it failed.
    *   `on_fail_action`: The action configured for this validator on failure (e.g., `exception`, `filter`, `reask`).
*   `processed_text` (optional): If any guardrail modifies the text (e.g., redacts sensitive information), the modified text will be returned here.

## 3. Authentication

API key-based authentication will be implemented to secure the endpoint. A header like `X-API-Key` will be expected.

## 4. Error Handling

Standard HTTP status codes will be used (e.g., 200 OK, 400 Bad Request, 401 Unauthorized, 500 Internal Server Error). Detailed error messages will be provided in the response body.

## 5. Technology Stack

*   **Framework**: Flask (due to its lightweight nature and Guardrails AI's existing Flask server capability).
*   **Deployment**: Docker container for easy deployment and isolation.

## 6. Configurability and Replaceability

*   **Guardrail Definitions**: Guardrail configurations (which validators to use, their parameters, and `on_fail` actions) will be defined in a separate configuration file (e.g., `config.py` or `config.json`). This allows for easy modification without code changes.
*   **Plugin System**: The API interface is designed to be generic. If a different guardrail solution needs to be used in the future, a new microservice implementing the same `/v1/guardrails/validate` endpoint can replace the current one without requiring changes in the LLM chatbot's integration code. This adheres to the 


principle of a standardized API interface.

## 7. Guardrail Management

Guardrails will be managed through configuration files. Each named guardrail (e.g., `toxic_language_guard`, `pii_redaction_guard`) will correspond to a specific set of Guardrails AI validators and their associated `OnFailAction` settings. This allows the LLM chatbot to request different types of guardrails based on the context of the conversation or the nature of the LLM's output.

## 8. Future Enhancements

*   **Asynchronous Processing**: For long-running validations, consider asynchronous processing to avoid blocking the API.
*   **Batch Validation**: Add an endpoint for validating multiple texts in a single request.
*   **Detailed Reporting**: Enhance the `validations` response to include more granular details about why a validation failed (e.g., specific toxic words, redacted entities).


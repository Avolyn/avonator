## Guardrails AI Framework Research

Guardrails AI is a Python framework designed to add guardrails to large language models. It offers two primary functionalities:

1.  **Input/Output Guards**: This involves running checks on inputs and outputs of LLMs to detect and mitigate risks. It utilizes 'validators' from the Guardrails Hub, which can be combined into Input and Output Guards.
    *   **Installation**: `pip install guardrails-ai`
    *   **Configuration**: `guardrails configure`
    *   **Validator Installation**: `guardrails hub install hub://guardrails/validator_name`
    *   **Usage**: Create a `Guard` object and use `.use()` or `.use_many()` with validators. Then call `guard.validate()`.

2.  **Structured Data Generation**: Helps LLMs produce structured data based on defined schemas (e.g., Pydantic `BaseModel`). It achieves this through:
    *   **Function Calling**: For LLMs that support it.
    *   **Prompt Optimization**: For LLMs without function calling support, by adding the schema to the prompt.
    *   **Usage**: Create a Pydantic `BaseModel`, then `Guard.for_pydantic(output_class=Pet, prompt=prompt)` and call the guard with the LLM API.

### Guardrails Server

Guardrails can be deployed as a standalone Flask service, exposing a REST API. This is highly relevant for the 


API plug-and-play requirement.

**Guardrails Server Details:**
*   **Installation**: `pip install "guardrails-ai"`
*   **Configuration**: `guardrails configure`
*   **Guard Creation**: `guardrails create --validators=hub://guardrails/two_words --guard-name=two-word-guard`
*   **Start Dev Server**: `guardrails start --config=./config.py`
*   **Interaction**: Can be interacted with using the `guardrails` client (setting `gr.settings.use_server = True`) or directly via an OpenAI SDK by setting `openai.base_url` to the server endpoint (e.g., `http://localhost:8000/guards/two-word-guard/openai/v1/`).
*   **Production Deployment**: Recommended to use Docker with Gunicorn for improved performance and scalability.

This server functionality is key to creating a modular, API-driven guardrail solution that can be easily integrated and replaced. The ability to interact with it via a standard OpenAI SDK interface is particularly beneficial for plug-and-play with LLM chatbots.


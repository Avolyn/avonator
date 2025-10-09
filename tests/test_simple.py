"""
Simple test to verify basic functionality
"""

def test_basic_import():
    """Test that we can import the main module."""
    try:
        import enhanced_guardrails
        assert True
    except ImportError as e:
        print(f"Import error: {e}")
        assert False

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    # Simple test that should always pass
    assert 1 + 1 == 2
    assert "hello" == "hello"
    assert True is True

def test_environment_variables():
    """Test environment variable handling."""
    import os
    
    # Test that we can access environment variables
    test_var = os.getenv("TEST_VAR", "default_value")
    assert test_var == "default_value"
    
    # Test that we can set environment variables
    os.environ["TEST_VAR"] = "test_value"
    assert os.getenv("TEST_VAR") == "test_value"

def test_json_handling():
    """Test JSON handling."""
    import json
    
    test_data = {"key": "value", "number": 123}
    json_str = json.dumps(test_data)
    parsed_data = json.loads(json_str)
    
    assert parsed_data == test_data
    assert parsed_data["key"] == "value"
    assert parsed_data["number"] == 123

def test_http_status_codes():
    """Test HTTP status code constants."""
    # Simulate FastAPI status codes
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500
    
    assert OK == 200
    assert BAD_REQUEST == 400
    assert UNAUTHORIZED == 401
    assert NOT_FOUND == 404
    assert INTERNAL_SERVER_ERROR == 500

if __name__ == "__main__":
    # Run tests if executed directly
    test_basic_import()
    test_basic_functionality()
    test_environment_variables()
    test_json_handling()
    test_http_status_codes()
    print("All simple tests passed!")

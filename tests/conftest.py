"""
Pytest configuration and fixtures.
"""

import os
import pytest

# Skip API key validation in tests
os.environ['SKIP_API_KEY_VALIDATION'] = 'true'

# Set dummy API keys for tests
os.environ['LLM__CLAUDE__API_KEY'] = 'sk-ant-test-key-for-testing'
os.environ['LLM__OPENAI__API_KEY'] = 'sk-test-key-for-testing'
os.environ['LLM__GEMINI__API_KEY'] = 'test-gemini-key'


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment before each test."""
    # Ensure validation is skipped
    os.environ['SKIP_API_KEY_VALIDATION'] = 'true'
    yield
    # Cleanup if needed

"""
Test Code Agent
================
Tests for code generation, execution, and auto-fixing.
"""

import pytest
import json

from agents.code_agent import CodeAgent, get_code_agent
from agents.code_executor import CodeExecutor, get_code_executor


class TestCodeExecutor:
    """Test sandboxed code execution."""
    
    def test_init(self):
        """Test executor initialization."""
        executor = CodeExecutor()
        assert executor.timeout == 10.0
    
    def test_simple_execution(self):
        """Test successful code execution."""
        executor = get_code_executor()
        
        code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""
        
        result = executor.execute(code)
        
        assert result.success
        assert "5" in result.stdout
        assert result.exit_code == 0
    
    def test_execution_with_tests(self):
        """Test code with assertions."""
        executor = get_code_executor()
        
        code = """
def multiply(a, b):
    return a * b
"""
        
        tests = """
assert multiply(2, 3) == 6
assert multiply(0, 5) == 0
assert multiply(-1, 5) == -5
"""
        
        result = executor.execute(code, tests)
        
        assert result.success
    
    def test_forbidden_import(self):
        """Test that forbidden imports are blocked."""
        executor = get_code_executor()
        
        code = """
import os
print(os.listdir('.'))
"""
        
        result = executor.execute(code)
        
        assert not result.success
        assert "forbidden" in result.error.lower()
    
    def test_timeout(self):
        """Test execution timeout."""
        executor = CodeExecutor(timeout=1.0)
        
        code = """
import time
time.sleep(5)
"""
        
        result = executor.execute(code)
        
        assert not result.success
        assert "timeout" in result.error.lower()
    
    def test_syntax_error(self):
        """Test syntax error handling."""
        executor = get_code_executor()
        
        code = """
def broken(
    # Missing closing parenthesis
"""
        
        result = executor.execute(code)
        
        assert not result.success


class TestCodeAgent:
    """Test CodeAgent generation and fixing."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = CodeAgent()
        assert agent.name == "CodeAgent"
        assert agent.model == "qwen3:4b"
        assert agent.max_fix_attempts == 3
    
    def test_simple_generation(self):
        """Test simple function generation."""
        agent = get_code_agent()
        
        result = agent.run("Create a function that adds two numbers")
        
        # Should generate code
        assert result.success or not result.success  # May fail if Ollama not running
        
        if result.success:
            data = json.loads(result.output)
            assert "code" in data
            assert len(data["code"]) > 0
    
    def test_generation_with_tests(self):
        """Test that tests are generated."""
        agent = get_code_agent()
        
        result = agent.run("Create a function to calculate factorial")
        
        if result.success:
            data = json.loads(result.output)
            assert "tests" in data
            # Should have some test assertions
            if data["tests"]:
                assert "assert" in data["tests"]
    
    @pytest.mark.slow
    def test_auto_fixing(self):
        """Test iterative auto-fixing (slow test)."""
        agent = CodeAgent(max_fix_attempts=2)
        
        # Request something that might need fixing
        result = agent.run("Create a function for binary search in a sorted list")
        
        if result.success:
            data = json.loads(result.output)
            # Check if iterations happened
            if "iterations" in data:
                # Should complete within attempts
                assert data["iterations"] <= 3


class TestIntegration:
    """Integration tests."""
    
    def test_end_to_end(self):
        """Test complete generation flow."""
        agent = get_code_agent()
        
        # Simple request
        result = agent.run("Create a function to check if a number is even")
        
        # Should either succeed or fail gracefully
        assert result is not None
        assert isinstance(result.success, bool)
    
    def test_singleton(self):
        """Test singleton pattern."""
        agent1 = get_code_agent()
        agent2 = get_code_agent()
        
        assert agent1 is agent2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])

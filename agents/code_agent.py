"""
Code Agent
===========
Intelligent code generation agent with testing and auto-fixing.

Features:
- Generate code from natural language
- Auto-generate tests
- Execute and validate
- Iterative error fixing (up to 3 attempts)
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
import requests

from agents.base_agent import BaseAgent, AgentResult, AgentType
from agents.code_executor import get_code_executor, ExecutionResult

logger = logging.getLogger(__name__)


class CodeAgent(BaseAgent):
    """
    Code generation agent with testing and auto-fixing.
    
    Uses thinking model (qwen3:4b) for intelligent code generation.
    """
    
    def __init__(
        self,
        name: str = "CodeAgent",
        max_fix_attempts: int = 3,
    ):
        """
        Initialize Code Agent.
        
        Args:
            name: Agent name
            max_fix_attempts: Maximum auto-fix iterations
        """
        super().__init__(
            name=name,
            agent_type=AgentType.CODE,
            description="Generate, test, and fix code",
            timeout=60.0,  # Allow time for multiple iterations
        )
        
        self.model = "qwen3:4b"  # Thinking model for code
        self.max_fix_attempts = max_fix_attempts
        self.executor = get_code_executor()
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Generate and test code.
        
        Args:
            task: Code generation request
            context: Optional context
            
        Returns:
            AgentResult with generated code
        """
        context = context or {}
        steps = []
        
        try:
            steps.append(f"Generating code with {self.model}")
            
            # Step 1: Generate initial code
            code, tests = self._generate_code(task, steps)
            
            if not code:
                return AgentResult(
                    success=False,
                    output="",
                    error="Failed to generate code",
                    steps_taken=steps,
                )
            
            # Step 2: Test and fix iteratively
            final_code, execution_result = self._test_and_fix(
                task, code, tests, steps
            )
            
            # Step 3: Build result
            if execution_result.success:
                output = json.dumps({
                    "code": final_code,
                    "tests": tests,
                    "execution_time": execution_result.execution_time,
                    "iterations": len([s for s in steps if "Fixing" in s]) + 1,
                }, indent=2)
                
                return AgentResult(
                    success=True,
                    output=output,
                    steps_taken=steps,
                    artifacts_created=["generated_code.py"],
                )
            else:
                # Failed after all attempts
                error_msg = self.executor.format_error_for_llm(execution_result)
                
                return AgentResult(
                    success=False,
                    output=json.dumps({"code": final_code, "error": error_msg}),
                    error=f"Code execution failed after {self.max_fix_attempts} attempts",
                    steps_taken=steps,
                )
            
        except Exception as e:
            logger.error(f"CodeAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )
    
    def _generate_code(
        self,
        task: str,
        steps: List[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Generate code and tests using LLM.
        
        Returns:
            (code, tests) or (None, None) on failure
        """
        from core.constants import OLLAMA_BASE_URL
        
        prompt = f"""Generate Python code for this task:

Task: {task}

Generate ONLY Python code with:
1. The main function/class implementation
2. Basic test assertions (at least 3)

Format:
```python
# Implementation
def function_name(...):
    ...

# Tests
assert function_name(...) == expected
assert ...
```

Write clean, documented code. Include type hints. No explanations."""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 600},
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}")
            
            generated = response.json().get("response", "")
            
            # Extract code blocks
            code_match = re.search(r'```python\s*(.*?)\s*```', generated, re.DOTALL)
            
            if code_match:
                full_code = code_match.group(1).strip()
            else:
                # Try without markdown
                full_code = generated.strip()
            
            # Split into impl and tests
            code, tests = self._split_code_and_tests(full_code)
            
            steps.append(f"Generated {len(code)} chars of code")
            if tests:
                test_count = tests.count('assert')
                steps.append(f"Generated {test_count} test assertions")
            
            return code, tests
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return None, None
    
    def _split_code_and_tests(self, full_code: str) -> tuple[str, str]:
        """
        Split generated code into implementation and tests.
        
        Returns:
            (implementation, tests)
        """
        lines = full_code.split('\n')
        
        # Find where tests start (lines with "# Test" or "assert")
        test_start_idx = None
        
        for i, line in enumerate(lines):
            if line.strip().startswith('# Test') or line.strip().startswith('assert'):
                test_start_idx = i
                break
        
        if test_start_idx is not None:
            impl = '\n'.join(lines[:test_start_idx]).strip()
            tests = '\n'.join(lines[test_start_idx:]).strip()
            return impl, tests
        else:
            # No tests found, assume all is implementation
            return full_code, ""
    
    def _test_and_fix(
        self,
        task: str,
        code: str,
        tests: str,
        steps: List[str]
    ) -> tuple[str, ExecutionResult]:
        """
        Test code and fix errors iteratively.
        
        Returns:
            (final_code, last_execution_result)
        """
        current_code = code
        
        for attempt in range(self.max_fix_attempts):
            steps.append(f"Testing code (attempt {attempt + 1}/{self.max_fix_attempts})")
            
            # Execute code
            result = self.executor.execute(current_code, tests)
            
            if result.success:
                steps.append("✓ Code passed all tests")
                return current_code, result
            
            # Failed - try to fix
            if attempt < self.max_fix_attempts - 1:
                steps.append("✗ Tests failed, fixing...")
                
                error_msg = self.executor.format_error_for_llm(result)
                fixed_code = self._fix_code(task, current_code, error_msg, steps)
                
                if fixed_code:
                    current_code = fixed_code
                else:
                    # Couldn't generate fix, return current state
                    break
        
        # Failed after all attempts
        return current_code, result
    
    def _fix_code(
        self,
        task: str,
        code: str,
        error: str,
        steps: List[str]
    ) -> Optional[str]:
        """
        Fix code based on error message.
        
        Returns:
            Fixed code or None
        """
        from core.constants import OLLAMA_BASE_URL
        
        prompt = f"""Fix this Python code:

Original task: {task}

Current code:
```python
{code}
```

Error:
{error}

Generate the corrected code. Output ONLY the fixed Python code, no explanations.
```python
...
```"""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500},
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                return None
            
            fixed = response.json().get("response", "")
            
            # Extract code
            code_match = re.search(r'```python\s*(.*?)\s*```', fixed, re.DOTALL)
            
            if code_match:
                fixed_code = code_match.group(1).strip()
                steps.append(f"Generated fix ({len(fixed_code)} chars)")
                return fixed_code
            else:
                return None
            
        except Exception as e:
            logger.error(f"Code fixing failed: {e}")
            return None


# =============================================================================
# SINGLETON
# =============================================================================

_code_agent = None


def get_code_agent() -> CodeAgent:
    """Get or create code agent singleton."""
    global _code_agent
    
    if _code_agent is None:
        _code_agent = CodeAgent()
    
    return _code_agent

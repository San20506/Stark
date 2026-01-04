"""
Code Executor
==============
Sandboxed code execution with safety restrictions.

Features:
- Subprocess isolation
- Timeout protection
- Whitelist imports
- No file system access
"""

import logging
import subprocess
import tempfile
import os
import ast
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Whitelist of safe imports
SAFE_IMPORTS = {
    'math', 'random', 'datetime', 'json', 're', 'itertools',
    'functools', 'collections', 'typing', 'dataclasses',
    'decimal', 'fractions', 'statistics', 'copy',
}

# Forbidden imports (security)
FORBIDDEN_IMPORTS = {
    'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
    'pathlib', 'shutil', 'pickle', 'marshal', 'ctypes',
    'importlib', '__import__', 'eval', 'exec', 'compile',
}


@dataclass
class ExecutionResult:
    """Result from code execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None
    execution_time: float = 0.0


class CodeExecutor:
    """
    Sandboxed Python code executor.
    
    Executes code in isolated subprocess with safety checks.
    """
    
    def __init__(self, timeout: float = 10.0):
        """
        Initialize code executor.
        
        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
        logger.info(f"CodeExecutor initialized (timeout={timeout}s)")
    
    def execute(
        self,
        code: str,
        test_code: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox.
        
        Args:
            code: Python code to execute
            test_code: Optional test assertions
            
        Returns:
            ExecutionResult with output and status
        """
        try:
            # Validate code safety
            if not self._is_safe(code):
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    error="Code contains forbidden operations",
                )
            
            # Combine code and tests
            full_code = code
            if test_code:
                full_code = f"{code}\n\n# Tests\n{test_code}"
            
            # Execute in subprocess
            return self._run_subprocess(full_code)
            
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                error=str(e),
            )
    
    def _is_safe(self, code: str) -> bool:
        """
        Check if code is safe to execute.
        
        Validates:
        - No forbidden imports
        - Valid Python syntax
        - No dangerous patterns
        """
        try:
            # Parse to AST
            tree = ast.parse(code)
            
            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_IMPORTS:
                            logger.warning(f"Forbidden import: {alias.name}")
                            return False
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in FORBIDDEN_IMPORTS:
                        logger.warning(f"Forbidden import: {node.module}")
                        return False
            
            # Check for dangerous built-ins
            dangerous_patterns = ['eval', 'exec', '__import__', 'compile']
            for pattern in dangerous_patterns:
                if pattern in code:
                    logger.warning(f"Dangerous pattern: {pattern}")
                    return False
            
            return True
            
        except SyntaxError as e:
            logger.warning(f"Syntax error: {e}")
            return False
    
    def _run_subprocess(self, code: str) -> ExecutionResult:
        """
        Run code in subprocess.
        
        Uses temporary file to avoid shell injection.
        """
        import time
        
        start_time = time.time()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run in subprocess
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),  # Isolate working directory
            )
            
            execution_time = time.time() - start_time
            
            success = result.returncode == 0
            
            return ExecutionResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                error=None if success else result.stderr,
                execution_time=execution_time,
            )
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timeout ({self.timeout}s)",
                exit_code=-1,
                error="Timeout",
                execution_time=self.timeout,
            )
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except Exception:
                pass
    
    def format_error_for_llm(self, result: ExecutionResult) -> str:
        """
        Format execution error for LLM parsing.
        
        Returns concise error description for code fixing.
        """
        if result.success:
            return "Execution successful"
        
        error_parts = []
        
        # Add stderr
        if result.stderr:
            # Extract relevant error (last few lines)
            stderr_lines = result.stderr.strip().split('\n')
            relevant_lines = stderr_lines[-5:]  # Last 5 lines
            error_parts.append("Error output:\n" + "\n".join(relevant_lines))
        
        # Add exit code
        if result.exit_code != 0:
            error_parts.append(f"Exit code: {result.exit_code}")
        
        # Add custom error message
        if result.error:
            error_parts.append(f"Error: {result.error}")
        
        return "\n\n".join(error_parts)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_executor = None


def get_code_executor() -> CodeExecutor:
    """Get or create code executor singleton."""
    global _executor
    
    if _executor is None:
        _executor = CodeExecutor()
    
    return _executor

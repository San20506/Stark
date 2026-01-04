"""
ALFRED Skill Validator
Safety checks for generated skills.
"""

import ast
import logging
from typing import Tuple, List

logger = logging.getLogger("Alfred.SkillValidator")

class SkillValidator:
    """Validates generated skills for safety."""
    
    # Dangerous imports that should be blocked
    BLOCKED_IMPORTS = {
        "os", "sys", "subprocess", "shutil", "pathlib",
        "socket", "urllib", "http", "ftplib",
        "pickle", "marshal", "shelve",
        "__builtin__", "builtins"
    }
    
    # Dangerous function calls
    BLOCKED_FUNCTIONS = {
        "eval", "exec", "compile", "__import__",
        "open",  # File operations should be explicit
        "input", "raw_input"  # No interactive input
    }
    
    # Allowed imports (whitelist approach for critical operations)
    ALLOWED_IMPORTS = {
        "requests", "json", "datetime", "time", "re",
        "math", "random", "typing", "dataclasses",
        "collections", "itertools", "functools"
    }
    
    def __init__(self):
        logger.info("✅ SkillValidator initialized")
    
    def validate(self, code: str) -> Tuple[bool, str]:
        """
        Validate skill code for safety.
        Returns: (is_valid, error_message)
        """
        # Check 1: Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Check 2: Scan for dangerous imports
        valid, msg = self._check_imports(tree)
        if not valid:
            return False, msg
        
        # Check 3: Scan for dangerous function calls
        valid, msg = self._check_function_calls(tree)
        if not valid:
            return False, msg
        
        # Check 4: Verify skill structure
        valid, msg = self._check_skill_structure(tree)
        if not valid:
            return False, msg
        
        return True, "Validation passed"
    
    def _check_imports(self, tree: ast.AST) -> Tuple[bool, str]:
        """Check for dangerous imports."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.BLOCKED_IMPORTS:
                        return False, f"Blocked import: {module}"
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BLOCKED_IMPORTS:
                        return False, f"Blocked import: {module}"
        
        return True, ""
    
    def _check_function_calls(self, tree: ast.AST) -> Tuple[bool, str]:
        """Check for dangerous function calls."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in self.BLOCKED_FUNCTIONS:
                    return False, f"Blocked function: {func_name}"
        
        return True, ""
    
    def _check_skill_structure(self, tree: ast.AST) -> Tuple[bool, str]:
        """Verify skill has required structure."""
        has_meta = False
        has_run = False
        
        for node in ast.walk(tree):
            # Check for SKILL_META
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SKILL_META":
                        has_meta = True
            
            # Check for run() function
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                has_run = True
        
        if not has_meta:
            return False, "Missing SKILL_META dictionary"
        if not has_run:
            return False, "Missing run() function"
        
        return True, ""
    
    def sandbox_test(self, code: str) -> Tuple[bool, str]:
        """
        Test skill in sandboxed environment.
        Returns: (success, result_or_error)
        """
        try:
            # Create restricted globals with necessary builtins
            safe_globals = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                    "isinstance": isinstance,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    "setattr": setattr,
                    "type": type,
                    "Exception": Exception,
                    "ValueError": ValueError,
                    "TypeError": TypeError,
                    "KeyError": KeyError,
                    "IndexError": IndexError,
                    "__import__": __import__,  # Needed for imports
                },
                "__name__": "__main__",
            }
            
            # Execute code
            exec(code, safe_globals)
            
            # Check if run() exists
            if "run" not in safe_globals:
                return False, "run() function not found after execution"
            
            return True, "Sandbox test passed"
            
        except Exception as e:
            return False, f"Sandbox execution failed: {e}"

# Global instance
skill_validator = SkillValidator()

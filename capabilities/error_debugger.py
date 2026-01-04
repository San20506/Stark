"""
STARK Error Debugger
====================
Analyze errors, tracebacks, and bugs to provide explanations and fixes.

Module 7 of 9 - Capabilities
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """Result of error analysis."""
    error_type: ErrorType
    error_name: str
    message: str
    root_cause: str
    explanation: str
    fixes: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.8
    traceback_info: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "error_name": self.error_name,
            "message": self.message,
            "root_cause": self.root_cause,
            "explanation": self.explanation,
            "fixes": self.fixes,
            "confidence": self.confidence,
        }


class ErrorDebugger:
    """
    Analyze and debug errors with clear explanations and fixes.
    
    Features:
    - Python traceback parsing
    - Error type classification
    - Root cause identification
    - Fix suggestions with explanations
    - Self-diagnosis capability
    
    Usage:
        debugger = ErrorDebugger()
        analysis = debugger.analyze("Traceback (most recent call last)...")
        print(analysis.explanation)
        print(analysis.fixes)
    """
    
    # Common Python errors and their patterns
    ERROR_PATTERNS = {
        "IndexError": {
            "pattern": r"IndexError: (list |string )?index out of range",
            "type": ErrorType.RUNTIME,
            "cause": "Attempting to access an index that doesn't exist",
            "fix_template": "Check the length of your collection before accessing: `if index < len(collection):`",
        },
        "KeyError": {
            "pattern": r"KeyError: ['\"]?(.+?)['\"]?$",
            "type": ErrorType.RUNTIME,
            "cause": "Accessing a dictionary key that doesn't exist",
            "fix_template": "Use `.get('key', default)` or check `if key in dict:` first",
        },
        "TypeError": {
            "pattern": r"TypeError: (.+)",
            "type": ErrorType.RUNTIME,
            "cause": "Operation on incompatible types",
            "fix_template": "Check the types of your variables with `type(var)`",
        },
        "AttributeError": {
            "pattern": r"AttributeError: ['\"]?(\w+)['\"]? object has no attribute ['\"]?(\w+)['\"]?",
            "type": ErrorType.RUNTIME,
            "cause": "Accessing an attribute that doesn't exist on the object",
            "fix_template": "Verify the object type and check for `None` values",
        },
        "ValueError": {
            "pattern": r"ValueError: (.+)",
            "type": ErrorType.RUNTIME,
            "cause": "Function received an argument with the right type but wrong value",
            "fix_template": "Validate input values before passing to functions",
        },
        "NameError": {
            "pattern": r"NameError: name ['\"]?(\w+)['\"]? is not defined",
            "type": ErrorType.RUNTIME,
            "cause": "Using a variable or function that hasn't been defined",
            "fix_template": "Check spelling and ensure the variable is defined in scope",
        },
        "ImportError": {
            "pattern": r"(ImportError|ModuleNotFoundError): (.+)",
            "type": ErrorType.DEPENDENCY,
            "cause": "Module or package not installed or not found",
            "fix_template": "Install with `pip install package_name` or check PYTHONPATH",
        },
        "SyntaxError": {
            "pattern": r"SyntaxError: (.+)",
            "type": ErrorType.SYNTAX,
            "cause": "Invalid Python syntax",
            "fix_template": "Check for missing colons, brackets, quotes, or indentation",
        },
        "IndentationError": {
            "pattern": r"IndentationError: (.+)",
            "type": ErrorType.SYNTAX,
            "cause": "Inconsistent indentation",
            "fix_template": "Use consistent spaces (4 recommended) or tabs, not both",
        },
        "FileNotFoundError": {
            "pattern": r"FileNotFoundError: .+['\"](.+)['\"]",
            "type": ErrorType.CONFIGURATION,
            "cause": "File or directory doesn't exist at specified path",
            "fix_template": "Check the file path and use `os.path.exists()` to verify",
        },
        "ZeroDivisionError": {
            "pattern": r"ZeroDivisionError: (.+)",
            "type": ErrorType.LOGIC,
            "cause": "Attempting to divide by zero",
            "fix_template": "Add a check: `if denominator != 0:` before division",
        },
        "RecursionError": {
            "pattern": r"RecursionError: (.+)",
            "type": ErrorType.LOGIC,
            "cause": "Infinite recursion or recursion depth exceeded",
            "fix_template": "Add base case or convert to iteration",
        },
    }
    
    def __init__(self):
        """Initialize error debugger."""
        self._analysis_count = 0
        self._error_history: List[ErrorAnalysis] = []
        logger.info("ErrorDebugger initialized")
    
    def analyze(self, error_text: str) -> ErrorAnalysis:
        """
        Analyze an error message or traceback.
        
        Args:
            error_text: Error message, traceback, or description
            
        Returns:
            ErrorAnalysis with explanation and fixes
        """
        self._analysis_count += 1
        
        # Parse traceback if present
        traceback_info = self._parse_traceback(error_text)
        
        # Identify error type
        error_name, error_info = self._identify_error(error_text)
        
        # Extract message
        message = self._extract_message(error_text, error_name)
        
        # Generate explanation
        explanation = self._generate_explanation(error_name, message, traceback_info)
        
        # Generate fixes
        fixes = self._generate_fixes(error_name, error_info, message)
        
        analysis = ErrorAnalysis(
            error_type=error_info.get("type", ErrorType.UNKNOWN),
            error_name=error_name,
            message=message,
            root_cause=error_info.get("cause", "Unknown cause"),
            explanation=explanation,
            fixes=fixes,
            traceback_info=traceback_info,
        )
        
        self._error_history.append(analysis)
        return analysis
    
    def _parse_traceback(self, text: str) -> Optional[Dict]:
        """Parse Python traceback to extract useful info."""
        if "Traceback (most recent call last)" not in text:
            return None
        
        info = {
            "frames": [],
            "error_line": None,
            "file": None,
            "line_number": None,
        }
        
        # Extract file/line info
        frame_pattern = r'File "(.+)", line (\d+), in (.+)'
        for match in re.finditer(frame_pattern, text):
            info["frames"].append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "function": match.group(3),
            })
        
        if info["frames"]:
            last_frame = info["frames"][-1]
            info["file"] = last_frame["file"]
            info["line_number"] = last_frame["line"]
        
        # Extract the error line (last line usually)
        lines = text.strip().split("\n")
        if lines:
            info["error_line"] = lines[-1]
        
        return info
    
    def _identify_error(self, text: str) -> Tuple[str, Dict]:
        """Identify the error type from text."""
        for error_name, info in self.ERROR_PATTERNS.items():
            if re.search(info["pattern"], text, re.MULTILINE):
                return error_name, info
        
        # Try to extract error name directly
        error_match = re.search(r'(\w+Error|\w+Exception): ', text)
        if error_match:
            return error_match.group(1), {"type": ErrorType.UNKNOWN, "cause": "Unknown"}
        
        return "Unknown", {"type": ErrorType.UNKNOWN, "cause": "Could not identify error type"}
    
    def _extract_message(self, text: str, error_name: str) -> str:
        """Extract the error message."""
        pattern = rf'{error_name}: (.+?)(?:\n|$)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return text[:200]  # Return first 200 chars as fallback
    
    def _generate_explanation(
        self,
        error_name: str,
        message: str,
        traceback_info: Optional[Dict],
    ) -> str:
        """Generate a clear explanation of the error."""
        parts = []
        
        # Error summary
        parts.append(f"**{error_name}**: {message}")
        parts.append("")
        
        # Plain language explanation
        if error_name in self.ERROR_PATTERNS:
            cause = self.ERROR_PATTERNS[error_name]["cause"]
            parts.append(f"**What happened**: {cause}")
        
        # Location info
        if traceback_info and traceback_info.get("file"):
            parts.append("")
            parts.append(f"**Location**: `{traceback_info['file']}` line {traceback_info['line_number']}")
        
        return "\n".join(parts)
    
    def _generate_fixes(
        self,
        error_name: str,
        error_info: Dict,
        message: str,
    ) -> List[Dict[str, str]]:
        """Generate fix suggestions."""
        fixes = []
        
        if error_name in self.ERROR_PATTERNS:
            fixes.append({
                "description": self.ERROR_PATTERNS[error_name]["fix_template"],
                "confidence": "high",
            })
        
        # Add context-specific fixes based on message
        if "None" in message or "NoneType" in message:
            fixes.append({
                "description": "Add a null check: `if value is not None:`",
                "confidence": "medium",
            })
        
        if "index" in message.lower():
            fixes.append({
                "description": "Use `try/except IndexError` for safe access",
                "confidence": "medium",
            })
        
        # Default fix
        if not fixes:
            fixes.append({
                "description": "Review the error message and check the relevant code",
                "confidence": "low",
            })
        
        return fixes
    
    def analyze_self_error(self, exception: Exception) -> ErrorAnalysis:
        """
        Analyze a STARK internal error.
        
        Args:
            exception: The caught exception
            
        Returns:
            Analysis of the internal error
        """
        import traceback
        
        tb_text = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        analysis = self.analyze(tb_text)
        
        # Mark as internal
        analysis.root_cause = f"[INTERNAL] {analysis.root_cause}"
        
        logger.warning(f"Self-error analyzed: {analysis.error_name}")
        return analysis
    
    def get_stats(self) -> Dict[str, Any]:
        """Get debugger statistics."""
        error_counts = {}
        for analysis in self._error_history:
            name = analysis.error_name
            error_counts[name] = error_counts.get(name, 0) + 1
        
        return {
            "total_analyses": self._analysis_count,
            "error_counts": error_counts,
            "recent_errors": [a.error_name for a in self._error_history[-10:]],
        }


# =============================================================================
# FACTORY
# =============================================================================

_debugger_instance: Optional[ErrorDebugger] = None


def get_error_debugger() -> ErrorDebugger:
    """Get or create the global error debugger."""
    global _debugger_instance
    
    if _debugger_instance is None:
        _debugger_instance = ErrorDebugger()
    
    return _debugger_instance

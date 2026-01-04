"""
STARK Safety Filter
===================
Input/output validation and content filtering for safe AI operations.

Prevents:
- Harmful instructions
- Malicious code execution
- Dangerous system operations
- Privacy violations
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for operations."""
    SAFE = "safe"           # Auto-approve
    LOW = "low"             # Auto-approve with logging
    MEDIUM = "medium"       # Notify user
    HIGH = "high"           # Require explicit approval
    CRITICAL = "critical"   # Block unless override


@dataclass
class SafetyCheck:
    """Result of a safety check."""
    is_safe: bool
    risk_level: RiskLevel
    reasons: List[str]
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class SafetyFilter:
    """
    Safety filter for validating user inputs and agent actions.
    
    Implements:
    - Pattern-based detection of harmful content
    - Risk level assessment
    - Suggestion generation
    """
    
    # Dangerous patterns (regex)
    DANGEROUS_PATTERNS = {
        # System destruction
        r'\brm\s+-rf\s+/': RiskLevel.CRITICAL,
        r'\bdd\s+if=/dev/zero': RiskLevel.CRITICAL,
        r'\bmkfs\b': RiskLevel.CRITICAL,
        r'\bformat\s+[c-z]:': RiskLevel.CRITICAL,
        
        # Privilege escalation
        r'\bsudo\s+rm': RiskLevel.HIGH,
        r'\bsudo\s+chmod\s+777': RiskLevel.HIGH,
        r'\bchmod\s+-R\s+777': RiskLevel.HIGH,
        
        # Network attacks
        r'\bnmap\s+.*-sS': RiskLevel.HIGH,
        r'\bmetasploit': RiskLevel.HIGH,
        r'\bsqlmap': RiskLevel.HIGH,
        
        # File deletion (mass)
        r'\brm\s+-r\s+\*': RiskLevel.MEDIUM,
        r'\bdel\s+/s\s+/q': RiskLevel.MEDIUM,
        
        # System modification
        r'\bcrontab\s+-r': RiskLevel.MEDIUM,
        r'\bsystemctl\s+disable': RiskLevel.MEDIUM,
    }
    
    # Sensitive patterns to flag
    SENSITIVE_PATTERNS = {
        r'password\s*[:=]': 'Contains password',
        r'api[_-]?key\s*[:=]': 'Contains API key',
        r'secret\s*[:=]': 'Contains secret',
        r'token\s*[:=]': 'Contains token',
    }
    
    def __init__(self):
        """Initialize safety filter."""
        self._checks_performed = 0
        self._blocked_count = 0
        logger.info("SafetyFilter initialized")
    
    def check_input(self, text: str) -> SafetyCheck:
        """
        Check user input for safety issues.
        
        Args:
            text: User input text
            
        Returns:
            SafetyCheck with risk assessment
        """
        self._checks_performed += 1
        
        reasons = []
        risk_level = RiskLevel.SAFE
        
        # Check for dangerous patterns
        for pattern, pattern_risk in self.DANGEROUS_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                reasons.append(f"Dangerous pattern detected: {pattern}")
                risk_level = max(risk_level, pattern_risk, key=lambda x: list(RiskLevel).index(x))
        
        # Check for sensitive data
        for pattern, description in self.SENSITIVE_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                reasons.append(description)
                risk_level = max(risk_level, RiskLevel.LOW, key=lambda x: list(RiskLevel).index(x))
        
        # Block critical operations
        is_safe = risk_level not in [RiskLevel.CRITICAL]
        
        if not is_safe:
            self._blocked_count += 1
            logger.warning(f"Blocked critical operation: {reasons}")
        
        return SafetyCheck(
            is_safe=is_safe,
            risk_level=risk_level,
            reasons=reasons,
        )
    
    def check_output(self, text: str) -> SafetyCheck:
        """
        Check AI output for safety issues.
        
        Args:
            text: AI-generated output
            
        Returns:
            SafetyCheck with risk assessment
        """
        reasons = []
        risk_level = RiskLevel.SAFE
        
        # Check if output contains sensitive data
        for pattern, description in self.SENSITIVE_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                reasons.append(f"Output may contain {description.lower()}")
                risk_level = RiskLevel.LOW
        
        return SafetyCheck(
            is_safe=True,  # Don't block output, just warn
            risk_level=risk_level,
            reasons=reasons,
        )
    
    def get_stats(self) -> Dict:
        """Get filter statistics."""
        return {
            "checks_performed": self._checks_performed,
            "blocked_count": self._blocked_count,
            "block_rate": self._blocked_count / max(1, self._checks_performed),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_safety_filter_instance: Optional[SafetyFilter] = None


def get_safety_filter() -> SafetyFilter:
    """Get or create the global safety filter."""
    global _safety_filter_instance
    
    if _safety_filter_instance is None:
        _safety_filter_instance = SafetyFilter()
    
    return _safety_filter_instance

"""
STARK Action Validator
=======================
Validates and approves actions before execution.

Implements tiered approval system:
- SAFE: Auto-execute
- LOW: Auto-execute with logging
- MEDIUM: Notify user
- HIGH: Require explicit approval
- CRITICAL: Block unless override
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from core.safety_filter import RiskLevel, SafetyFilter, get_safety_filter

logger = logging.getLogger(__name__)


@dataclass
class ActionRequest:
    """Request to perform an action."""
    action_type: str                    # e.g., "file_write", "command_exec"
    description: str                    # Human-readable description
    parameters: Dict[str, Any]          # Action parameters
    risk_level: RiskLevel = RiskLevel.SAFE
    reason: str = ""                    # Why this risk level


@dataclass
class ActionApproval:
    """Result of action approval check."""
    approved: bool
    risk_level: RiskLevel
    reason: str
    requires_user_approval: bool = False
    user_prompt: str = ""


class ActionValidator:
    """
    Validates actions before execution.
    
    Uses safety filter + action-specific rules to determine
    if an action should be approved, blocked, or require user confirmation.
    """
    
    # Risk levels for different action types
    ACTION_RISK_LEVELS = {
        # File operations
        "file_read": RiskLevel.SAFE,
        "file_write": RiskLevel.LOW,
        "file_delete": RiskLevel.HIGH,
        "file_move": RiskLevel.MEDIUM,
        
        # System operations
        "command_exec": RiskLevel.HIGH,
        "package_install": RiskLevel.MEDIUM,
        "system_config": RiskLevel.HIGH,
        
        # Network operations
        "web_request": RiskLevel.LOW,
        "web_scrape": RiskLevel.LOW,
        "api_call": RiskLevel.MEDIUM,
    }
    
    def __init__(self, auto_approve_threshold: RiskLevel = RiskLevel.LOW):
        """
        Initialize action validator.
        
        Args:
            auto_approve_threshold: Max risk level to auto-approve
        """
        self.auto_approve_threshold = auto_approve_threshold
        self.safety_filter = get_safety_filter()
        
        self._validations_performed = 0
        self._approvals = 0
        self._rejections = 0
        self._user_approvals_required = 0
        
        logger.info(f"ActionValidator initialized (threshold={auto_approve_threshold.value})")
    
    def validate_action(self, request: ActionRequest) -> ActionApproval:
        """
        Validate an action request.
        
        Args:
            request: Action to validate
            
        Returns:
            ActionApproval with decision
        """
        self._validations_performed += 1
        
        # Determine base risk level
        base_risk = self.ACTION_RISK_LEVELS.get(
            request.action_type,
            RiskLevel.MEDIUM  # Default to medium for unknown actions
        )
        
        # Use provided risk level if higher
        risk_level = max(
            base_risk,
            request.risk_level,
            key=lambda x: list(RiskLevel).index(x)
        )
        
        # Check description with safety filter
        safety_check = self.safety_filter.check_input(request.description)
        if not safety_check.is_safe:
            self._rejections += 1
            return ActionApproval(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Blocked by safety filter: {', '.join(safety_check.reasons)}",
            )
        
       # Update risk level from safety check
        risk_level = max(
            risk_level,
            safety_check.risk_level,
            key=lambda x: list(RiskLevel).index(x)
        )
        
        # Determine approval
        if risk_level.value in [RiskLevel.SAFE.value, RiskLevel.LOW.value]:
            # Auto-approve
            if list(RiskLevel).index(risk_level) <= list(RiskLevel).index(self.auto_approve_threshold):
                self._approvals += 1
                return ActionApproval(
                    approved=True,
                    risk_level=risk_level,
                    reason="Auto-approved",
                )
        
        if risk_level == RiskLevel.CRITICAL:
            # Block
            self._rejections += 1
            return ActionApproval(
                approved=False,
                risk_level=risk_level,
                reason="Critical risk - operation blocked",
            )
        
        # Require user approval for MEDIUM/HIGH
        self._user_approvals_required += 1
        return ActionApproval(
            approved=False,
            risk_level=risk_level,
            reason=f"User approval required for {risk_level.value} risk operation",
            requires_user_approval=True,
            user_prompt=self._generate_approval_prompt(request, risk_level),
        )
    
    def _generate_approval_prompt(
        self,
        request: ActionRequest,
        risk_level: RiskLevel
    ) -> str:
        """Generate user approval prompt."""
        prompt = f"""
⚠️  ACTION APPROVAL REQUIRED

Risk Level: {risk_level.value.upper()}
Action: {request.action_type}
Description: {request.description}

Parameters:
"""
        for key, value in request.parameters.items():
            prompt += f"  • {key}: {value}\n"
        
        prompt += "\nApprove this action? (yes/no): "
        return prompt
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            "validations": self._validations_performed,
            "approvals": self._approvals,
            "rejections": self._rejections,
            "user_approvals_required": self._user_approvals_required,
            "approval_rate": self._approvals / max(1, self._validations_performed),
        }


# =============================================================================
# DECORATOR FOR SAFE ACTIONS
# =============================================================================

def safe_action(
    action_type: str,
    risk_level: RiskLevel = RiskLevel.SAFE,
    validator: Optional[ActionValidator] = None
):
    """
    Decorator to mark a function as requiring safety validation.
    
    Usage:
        @safe_action("file_delete", risk_level=RiskLevel.HIGH)
        def delete_file(path: str):
            os.remove(path)
    """
    if validator is None:
        validator = ActionValidator()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Create action request
            request = ActionRequest(
                action_type=action_type,
                description=f"{func.__name__} called with args={args}, kwargs={kwargs}",
                parameters={"args": args, "kwargs": kwargs},
                risk_level=risk_level,
            )
            
            # Validate
            approval = validator.validate_action(request)
            
            if not approval.approved:
                if approval.requires_user_approval:
                    # In production, this would prompt user
                    logger.warning(f"Action requires user approval: {request.description}")
                    raise PermissionError(approval.user_prompt)
                else:
                    raise PermissionError(f"Action blocked: {approval.reason}")
            
            # Execute
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# =============================================================================
# SINGLETON
# =============================================================================

_action_validator_instance: Optional[ActionValidator] = None


def get_action_validator() -> ActionValidator:
    """Get or create the global action validator."""
    global _action_validator_instance
    
    if _action_validator_instance is None:
        _action_validator_instance = ActionValidator()
    
    return _action_validator_instance

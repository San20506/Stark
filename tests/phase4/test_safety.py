#!/usr/bin/env python3
"""
Safety System Demo
==================
Test the safety filter and action validator.
"""

from core.safety_filter import get_safety_filter, RiskLevel
from core.action_validator import get_action_validator, ActionRequest

print("=" * 60)
print("STARK Safety & Guardrails Demo")
print("=" * 60)
print()

# Get instances
safety_filter = get_safety_filter()
validator = get_action_validator()

# Test 1: Safe input
print("🔒 Test 1: Safe Input")
check = safety_filter.check_input("Read the README file")
print(f"  Input: \"Read the README file\"")
print(f"  Safe: {check.is_safe}")
print(f"  Risk: {check.risk_level.value}")
print(f"  Reasons: {check.reasons if check.reasons else 'None'}")
print()

# Test 2: Dangerous input
print("⚠️ Test 2: Dangerous Input")
check = safety_filter.check_input("sudo rm -rf /")
print(f"  Input: \"sudo rm -rf /\"")
print(f"  Safe: {check.is_safe}")
print(f"  Risk: {check.risk_level.value}")
print(f"  Reasons: {check.reasons}")
print()

# Test 3: Sensitive data
print("🔑 Test 3: Sensitive Data")
check = safety_filter.check_input("My password is abc123")
print(f"  Input: \"My password is abc123\"")
print(f"  Safe: {check.is_safe}")
print(f"  Risk: {check.risk_level.value}")
print(f"  Reasons: {check.reasons}")
print()

# Test 4: Safe action validation
print("✅ Test 4: Safe Action (file read)")
request = ActionRequest(
    action_type="file_read",
    description="Read config file",
    parameters={"path": "/home/user/config.json"},
)
approval = validator.validate_action(request)
print(f"  Action: file_read")
print(f"  Approved: {approval.approved}")
print(f"  Risk: {approval.risk_level.value}")
print(f"  Reason: {approval.reason}")
print()

# Test 5: High-risk action
print("🚨 Test 5: High-Risk Action (file delete)")
request = ActionRequest(
    action_type="file_delete",
    description="Delete system file",
    parameters={"path": "/etc/passwd"},
)
approval = validator.validate_action(request)
print(f"  Action: file_delete")
print(f"  Approved: {approval.approved}")
print(f"  Risk: {approval.risk_level.value}")
print(f"  Requires approval: {approval.requires_user_approval}")
if approval.user_prompt:
    print(f"  User prompt:\n{approval.user_prompt}")
print()

# Test 6: Critical blocked action
print("🛑 Test 6: Critical Action (should block)")
request = ActionRequest(
    action_type="command_exec",
    description="rm -rf /",
    parameters={"command": "rm -rf /"},
)
approval = validator.validate_action(request)
print(f"  Action: command_exec")
print(f"  Approved: {approval.approved}")
print(f"  Risk: {approval.risk_level.value}")
print(f"  Reason: {approval.reason}")
print()

# Show stats
print("📊 Statistics:")
filter_stats = safety_filter.get_stats()
validator_stats = validator.get_stats()

print(f"  Safety Filter:")
print(f"    Checks: {filter_stats['checks_performed']}")
print(f"    Blocked: {filter_stats['blocked_count']}")
print(f"    Block rate: {filter_stats['block_rate']:.1%}")
print()

print(f"  Action Validator:")
print(f"    Validations: {validator_stats['validations']}")
print(f"    Auto-approved: {validator_stats['approvals']}")
print(f"    Rejected: {validator_stats['rejections']}")
print(f"    User approval needed: {validator_stats['user_approvals_required']}")
print()

print("✅ Safety system working!")

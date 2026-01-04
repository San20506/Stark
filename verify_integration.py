#!/usr/bin/env python3
"""
Verify Integration Structure
============================
Quick check that all integration components are properly connected.
"""

import sys
sys.path.insert(0, '/home/sandy/Projects/Projects/Stark')

print("=" * 70)
print("STARK Integration Verification")
print("=" * 70)
print()

# Test 1: Import checks
print("[1] Checking imports...")
try:
    from agents.autonomous_orchestrator import AutonomousOrchestrator, get_autonomous_orchestrator
    print("    ✓ AutonomousOrchestrator imported")
except Exception as e:
    print(f"    ✗ AutonomousOrchestrator: {e}")

try:
    from agents.tool_executor import ToolExecutor
    print("    ✓ ToolExecutor imported")
except Exception as e:
    print(f"    ✗ ToolExecutor: {e}")

try:
    from agents.router_agent import RouterAgent, RoutePath
    print("    ✓ RouterAgent imported")
except Exception as e:
    print(f"    ✗ RouterAgent: {e}")

try:
    from agents.code_agent import CodeAgent
    print("    ✓ CodeAgent imported")
except Exception as e:
    print(f"    ✗ CodeAgent: {e}")

try:
    from agents.web_agent import WebAgent
    print("    ✓ WebAgent imported")
except Exception as e:
    print(f"    ✗ WebAgent: {e}")

try:
    from agents.file_agent import FileAgent
    print("    ✓ FileAgent imported")
except Exception as e:
    print(f"    ✗ FileAgent: {e}")

try:
    from automation.app_launcher import get_app_launcher, AppLauncher
    print("    ✓ Automation module imported")
except Exception as e:
    print(f"    ✗ Automation: {e}")

print()

# Test 2: Component structure
print("[2] Checking component connections...")

try:
    orchestrator = AutonomousOrchestrator()
    
    # Check that all agents are registered
    agents = ['RouterAgent', 'RetrieverAgent', 'FastAnswerAgent', 
              'PlannerAgent', 'ArbiterAgent', 'WebAgent']
    
    for agent_name in agents:
        agent = orchestrator.orchestrator.get_agent(agent_name)
        if agent:
            print(f"    ✓ {agent_name} registered")
        else:
            print(f"    ✗ {agent_name} NOT registered")
    
    # Check tool executor
    if hasattr(orchestrator, 'tool_executor'):
        print("    ✓ ToolExecutor attribute exists")
    else:
        print("    ✗ ToolExecutor attribute missing")
        
except Exception as e:
    print(f"    ✗ Orchestrator creation failed: {e}")

print()

# Test 3: Main integration point
print("[3] Checking main.py integration...")
try:
    from core.main import STARK
    
    # Check if predict method references autonomous orchestrator
    import inspect
    source = inspect.getsource(STARK.predict)
    
    if "get_autonomous_orchestrator" in source:
        print("    ✓ main.py predict() integrates autonomous orchestrator")
    else:
        print("    ✗ main.py predict() does NOT integrate autonomous orchestrator")
        
    if "complex_tasks" in source:
        print("    ✓ Complex task routing logic found")
    else:
        print("    ✗ Complex task routing logic NOT found")
        
except Exception as e:
    print(f"    ✗ Main integration check failed: {e}")

print()

# Test 4: ToolExecutor methods
print("[4] Checking ToolExecutor capabilities...")
try:
    from agents.tool_executor import ToolExecutor
    from agents.base_agent import AgentOrchestrator
    
    orchestrator = AgentOrchestrator()
    executor = ToolExecutor(orchestrator)
    
    methods = ['execute_plan', '_execute_file_tool', '_execute_code_tool', 
               '_execute_web_tool', '_execute_automation_tool']
    
    for method in methods:
        if hasattr(executor, method):
            print(f"    ✓ {method} exists")
        else:
            print(f"    ✗ {method} missing")
            
except Exception as e:
    print(f"    ✗ ToolExecutor check failed: {e}")

print()
print("=" * 70)
print("Verification complete!")
print("=" * 70)

#!/usr/bin/env python3
"""
Agent Framework Demo
====================
Quick test of the multi-agent system.
"""

from agents.base_agent import get_orchestrator, AgentType
from agents.file_agent import FileAgent

# Initialize orchestrator
orchestrator = get_orchestrator()

# Create and register FileAgent
file_agent = FileAgent(
    name="FileOps",
    allowed_directories=["/home/sandy/Projects/Projects/Stark"],
)
orchestrator.register_agent(file_agent)

print("=" * 60)
print("STARK Multi-Agent Framework Demo")
print("=" * 60)
print()

# List agents
print("📋 Registered Agents:")
for agent_info in orchestrator.list_agents():
    print(f"  • {agent_info['name']} ({agent_info['type']}): {agent_info['description']}")
print()

# Test 1: Read a file
print("🔍 Test 1: Read file")
result = orchestrator.call_agent(
    "FileOps",
    "read /home/sandy/Projects/Projects/Stark/core/constants.py",
    context={"operation": "read", "path": "/home/sandy/Projects/Projects/Stark/core/constants.py"}
)
print(f"  Success: {result.success}")
print(f"  Output length: {len(result.output)} chars")
print(f"  Steps: {result.steps_taken}")
print(f"  Time: {result.execution_time_ms:.0f}ms")
print()

# Test 2: List directory
print("📂 Test 2: List directory")
result = orchestrator.call_agent(
    "FileOps",
    "list /home/sandy/Projects/Projects/Stark/agents",
    context={"operation": "list", "path": "/home/sandy/Projects/Projects/Stark/agents"}
)
print(f"  Success: {result.success}")
print(f"  Output:\n{result.output}")
print()

# Test 3: Search for Python files
print("🔎 Test 3: Search for files")
result = orchestrator.call_agent(
    "FileOps",
    "search *.py in /home/sandy/Projects/Projects/Stark/agents",
    context={
        "operation": "search",
        "path": "/home/sandy/Projects/Projects/Stark/agents",
        "pattern": "*.py"
    }
)
print(f"  Success: {result.success}")
print(f"  Found:\n{result.output}")
print()

# Show stats
print("📊 Orchestrator Stats:")
stats = orchestrator.get_stats()
print(f"  Total agents: {stats['total_agents']}")
print(f"  Total executions: {stats['total_executions']}")
print()

for agent_name, agent_stats in stats['agents'].items():
    print(f"  {agent_name}:")
    print(f"    Executions: {agent_stats['executions']}")
    print(f"    Success rate: {agent_stats['success_rate']:.1%}")
    print(f"    Avg time: {agent_stats['avg_time_ms']:.0f}ms")
print()

print("✅ Agent framework working!")

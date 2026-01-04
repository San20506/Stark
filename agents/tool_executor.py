"""
Tool Executor for Deep Path
============================
Executes plans by delegating to appropriate agents/tools.
"""

import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tool calls from planner."""
    
    def __init__(self, orchestrator):
        """
        Initialize tool executor.
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    def execute_plan(self, query: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plan by calling appropriate tools.
        
        Args:
            query: Original user query
            plan: Plan dict from PlannerAgent
            
        Returns:
            Execution results dict
        """
        steps = plan.get("steps", [])
        requires_tools = plan.get("requires_tools", [])
        results = []
        
        logger.info(f"Executing plan with {len(steps)} steps, tools: {requires_tools}")
        
        # Check if this is a system control action - use ActionExecutor directly
        if "automation" in requires_tools or "system" in requires_tools:
            result = self._execute_with_action_executor(query)
            if result:
                return result
        
        # Execute based on required tools
        for tool in requires_tools:
            if tool == "file":
                result = self._execute_file_tool(query, steps)
                if result:
                    results.append(result)
            
            elif tool == "code":
                result = self._execute_code_tool(query, steps)
                if result:
                    results.append(result)
            
            elif tool == "web":
                result = self._execute_web_tool(query, steps)
                if result:
                    results.append(result)
        
        # If no specific tools, just summarize the plan
        if not results:
            return {
                "success": True,
                "output": f"Created plan with {len(steps)} steps: {', '.join(steps[:3])}",
                "steps_executed": 0,
            }
        
        # Combine results
        combined_output = "\n\n".join([r["output"] for r in results if r.get("output")])
        
        return {
            "success": any(r.get("success") for r in results),
            "output": combined_output,
            "steps_executed": len(results),
        }
    
    def _execute_with_action_executor(self, query: str) -> Optional[Dict]:
        """Execute using ActionExecutor for system control actions."""
        try:
            from agents.action_executor import get_action_executor
            from core.intent_classifier import get_intent_classifier
            
            # Classify intent
            classifier = get_intent_classifier()
            intent = classifier.classify(query)
            
            if intent.is_actionable:
                executor = get_action_executor()
                result = executor.execute(intent)
                
                return {
                    "success": result.success,
                    "output": result.message,
                    "steps_executed": 1 if result.success else 0,
                    "action_taken": result.action_taken,
                }
            
            return None
        except Exception as e:
            logger.error(f"ActionExecutor failed: {e}")
            return None
    
    def _execute_file_tool(self, query: str, steps: List[str]) -> Optional[Dict]:
        """Execute FileAgent."""
        try:
            from agents.file_agent import FileAgent
            agent = self.orchestrator.get_agent("FileAgent")
            if not agent:
                agent = FileAgent()
                self.orchestrator.register_agent(agent)
            
            result = agent.run(query)
            return {
                "success": result.success,
                "output": result.output or result.error,
                "tool": "file"
            }
        except Exception as e:
            logger.error(f"File tool failed: {e}")
            return None
    
    def _execute_code_tool(self, query: str, steps: List[str]) -> Optional[Dict]:
        """Execute CodeAgent."""
        try:
            from agents.code_agent import get_code_agent
            agent = get_code_agent()
            
            result = agent.run(query)
            if result.success:
                data = json.loads(result.output)
                return {
                    "success": True,
                    "output": f"Generated code:\n{data['code']}\n\nTests passed!",
                    "tool": "code"
                }
            else:
                return {
                    "success": False,
                    "output": f"Code generation failed: {result.error}",
                    "tool": "code"
                }
        except Exception as e:
            logger.error(f"Code tool failed: {e}")
            return None
    
    def _execute_web_tool(self, query: str, steps: List[str]) -> Optional[Dict]:
        """Execute WebAgent."""
        try:
            agent = self.orchestrator.get_agent("WebAgent")
            if not agent:
                logger.warning("WebAgent not registered")
                return None
            
            result = agent.run(query)
            return {
                "success": result.success,
                "output": result.output[:500] if result.output else result.error,  # Limit output
                "tool": "web"
            }
        except Exception as e:
            logger.error(f"Web tool failed: {e}")
            return None
    
    def _execute_automation_tool(self, query: str, steps: List[str]) -> Optional[Dict]:
        """Execute automation tools."""
        try:
            from automation.app_launcher import get_app_launcher
            
            launcher = get_app_launcher()
            
            # Simple pattern matching for common automation tasks
            query_lower = query.lower()
            
            if "open" in query_lower or "launch" in query_lower:
                # Extract app name (simple heuristic)
                for app in ["calendar", "chrome", "firefox", "terminal", "code", "editor", "files", "vscode"]:
                    if app in query_lower:
                        pid = launcher.launch(app)
                        if pid:
                            return {
                                "success": True,
                                "output": f"Launched {app} (PID: {pid})",
                                "tool": "automation"
                            }
                        else:
                            return {
                                "success": False,
                                "output": f"Failed to launch {app}",
                                "tool": "automation"
                            }
                
                return {
                    "success": False,
                    "output": "Could not determine which application to launch",
                    "tool": "automation"
                }
            
            elif "list" in query_lower and "running" in query_lower:
                # List running processes
                import psutil
                procs = []
                for p in psutil.process_iter(['name']):
                    try:
                        procs.append(p.info['name'])
                    except:
                        pass
                unique_apps = list(set(procs))[:15]  # First 15 unique apps
                return {
                    "success": True,
                    "output": f"Running applications: {', '.join(unique_apps)}",
                    "tool": "automation"
                }
            
            elif "kill" in query_lower or "close" in query_lower:
                for app in ["chrome", "firefox", "terminal", "code"]:
                    if app in query_lower:
                        count = launcher.kill_by_name(app)
                        return {
                            "success": count > 0,
                            "output": f"Closed {count} {app} process(es)",
                            "tool": "automation"
                        }
            
            return {
                "success": False,
                "output": "Automation action not recognized. Try: open [app], list running, or close [app]",
                "tool": "automation"
            }
                
        except Exception as e:
            logger.error(f"Automation tool failed: {e}")
            return {
                "success": False,
                "output": f"Automation failed: {e}",
                "tool": "automation"
            }

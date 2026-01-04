"""
Action Executor
================
Executes classified intents as real system actions.

This is the core of STARK's agentic capabilities.
"""

import logging
import subprocess
import os
from typing import Optional
from dataclasses import dataclass

from core.intent_classifier import Intent, IntentType
from automation.app_discovery import get_app_discovery

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    message: str
    action_taken: str
    details: Optional[dict] = None


class ActionExecutor:
    """
    Executes intents as real system actions.
    
    Capabilities:
    - Open/close applications
    - Search the web
    - Execute safe commands
    """
    
    def __init__(self):
        """Initialize action executor."""
        self._app_discovery = get_app_discovery()
        logger.info("ActionExecutor initialized")
    
    def execute(self, intent: Intent) -> ActionResult:
        """
        Execute an intent.
        
        Args:
            intent: Classified intent from IntentClassifier
            
        Returns:
            ActionResult with success status and message
        """
        logger.info(f"Executing intent: {intent.type.value} (target: {intent.target})")
        
        try:
            if intent.type == IntentType.OPEN_APP:
                return self._open_app(intent.target)
            
            elif intent.type == IntentType.CLOSE_APP:
                return self._close_app(intent.target)
            
            elif intent.type == IntentType.LIST_APPS:
                return self._list_apps()
            
            elif intent.type == IntentType.SEARCH_WEB:
                return self._search_web(intent.target)
            
            elif intent.type == IntentType.SYSTEM_INFO:
                return self._get_system_info()
            
            else:
                return ActionResult(
                    success=False,
                    message=f"Action type '{intent.type.value}' not yet implemented",
                    action_taken="none",
                )
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return ActionResult(
                success=False,
                message=f"Failed to execute action: {e}",
                action_taken="error",
            )
    
    def _open_app(self, app_name: Optional[str]) -> ActionResult:
        """Open an application."""
        if not app_name:
            return ActionResult(
                success=False,
                message="No application name specified",
                action_taken="none",
            )
        
        # Find the app
        app_info = self._app_discovery.find(app_name)
        
        if not app_info:
            # Try direct execution as fallback
            return self._try_direct_launch(app_name)
        
        # Launch the app
        try:
            # Parse exec command
            exec_parts = app_info.exec_path.split()
            
            # Launch in background
            process = subprocess.Popen(
                exec_parts,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            
            logger.info(f"Launched {app_info.name} (PID: {process.pid})")
            
            return ActionResult(
                success=True,
                message=f"✓ Opened {app_info.name}",
                action_taken=f"launched:{app_info.name}",
                details={"pid": process.pid, "exec": app_info.exec_path},
            )
            
        except FileNotFoundError:
            return ActionResult(
                success=False,
                message=f"Application '{app_info.name}' not found at {app_info.exec_path}",
                action_taken="not_found",
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to launch {app_info.name}: {e}",
                action_taken="error",
            )
    
    def _try_direct_launch(self, app_name: str) -> ActionResult:
        """Try to launch app directly by name."""
        try:
            process = subprocess.Popen(
                [app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            
            return ActionResult(
                success=True,
                message=f"✓ Opened {app_name}",
                action_taken=f"launched:{app_name}",
                details={"pid": process.pid},
            )
        except FileNotFoundError:
            return ActionResult(
                success=False,
                message=f"Application '{app_name}' not found. Try running 'refresh apps' to update the app list.",
                action_taken="not_found",
            )
    
    def _close_app(self, app_name: Optional[str]) -> ActionResult:
        """Close an application."""
        if not app_name:
            return ActionResult(
                success=False,
                message="No application name specified",
                action_taken="none",
            )
        
        import psutil
        
        closed_count = 0
        app_lower = app_name.lower()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                
                if app_lower in proc_name or app_lower in cmdline:
                    proc.terminate()
                    closed_count += 1
                    logger.info(f"Terminated {proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if closed_count > 0:
            return ActionResult(
                success=True,
                message=f"✓ Closed {closed_count} {app_name} process(es)",
                action_taken=f"closed:{app_name}",
                details={"count": closed_count},
            )
        else:
            return ActionResult(
                success=False,
                message=f"No running processes found for '{app_name}'",
                action_taken="not_found",
            )
    
    def _list_apps(self) -> ActionResult:
        """List running applications."""
        import psutil
        
        apps = set()
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and not name.startswith(('.', '_')):
                    apps.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        sorted_apps = sorted(list(apps))[:20]  # Limit to 20
        
        return ActionResult(
            success=True,
            message=f"Running applications:\n" + "\n".join(f"• {app}" for app in sorted_apps),
            action_taken="listed_apps",
            details={"count": len(apps), "shown": len(sorted_apps)},
        )
    
    def _search_web(self, query: Optional[str]) -> ActionResult:
        """Open web browser with search query."""
        if not query:
            return ActionResult(
                success=False,
                message="No search query specified",
                action_taken="none",
            )
        
        # URL encode the query
        from urllib.parse import quote_plus
        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        
        # Try to open in default browser
        try:
            subprocess.Popen(
                ['xdg-open', search_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            return ActionResult(
                success=True,
                message=f"✓ Searching for: {query}",
                action_taken=f"search:{query}",
                details={"url": search_url},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to open browser: {e}",
                action_taken="error",
            )
    
    def _get_system_info(self) -> ActionResult:
        """Get basic system information."""
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        info_lines = [
            f"CPU Usage: {cpu_percent:.1f}%",
            f"Memory: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)",
            f"Disk: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)",
        ]
        
        return ActionResult(
            success=True,
            message="System Information:\n" + "\n".join(f"• {line}" for line in info_lines),
            action_taken="system_info",
            details={"cpu": cpu_percent, "memory_percent": memory.percent, "disk_percent": disk.percent},
        )


# =============================================================================
# SINGLETON
# =============================================================================

_executor: Optional[ActionExecutor] = None


def get_action_executor() -> ActionExecutor:
    """Get or create action executor singleton."""
    global _executor
    if _executor is None:
        _executor = ActionExecutor()
    return _executor

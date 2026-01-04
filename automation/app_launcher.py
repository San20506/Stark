"""
STARK Desktop Automation - Application Launcher
================================================
Launch and manage applications on Linux.

Capabilities:
- Launch applications
- Check if app is running
- Kill applications
- Get app PIDs
"""

import logging
import subprocess
import psutil
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AppProcess:
    """Information about a running application."""
    pid: int
    name: str
    cmdline: List[str]
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


class AppLauncher:
    """
    Launch and manage applications.
    
    Uses subprocess for launching and psutil for process management.
    """
    
    # Common application commands
    APP_COMMANDS = {
        'chrome': 'google-chrome',
        'firefox': 'firefox',
        'vscode': 'code',
        'terminal': 'gnome-terminal',
        'files': 'nautilus',
        'text-editor': 'gedit',
    }
    
    def __init__(self):
        """Initialize app launcher."""
        logger.info("AppLauncher initialized")
    
    def launch(self, app_name: str, args: List[str] = None) -> Optional[int]:
        """
        Launch an application.
        
        Args:
            app_name: Application name or command
            args: Command-line arguments
            
        Returns:
            Process ID if successful, None otherwise
        """
        args = args or []
        
        # Resolve app name to command
        command = self.APP_COMMANDS.get(app_name.lower(), app_name)
        
        try:
            # Launch in background
            process = subprocess.Popen(
                [command] + args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )
            
            logger.info(f"Launched {command} (PID: {process.pid})")
            return process.pid
            
        except FileNotFoundError:
            logger.error(f"Application not found: {command}")
            return None
        except Exception as e:
            logger.error(f"Failed to launch {command}: {e}")
            return None
    
    def is_running(self, app_name: str) -> bool:
        """
        Check if an application is running.
        
        Args:
            app_name: Application name to search for
            
        Returns:
            True if at least one instance is running
        """
        processes = self.find_processes(app_name)
        return len(processes) > 0
    
    def find_processes(self, app_name: str) -> List[AppProcess]:
        """
        Find all processes matching an app name.
        
        Args:
            app_name: Application name (case-insensitive)
            
        Returns:
            List of AppProcess objects
        """
        app_name_lower = app_name.lower()
        matches = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                proc_name = info['name'].lower()
                
                # Match by process name
                if app_name_lower in proc_name:
                    matches.append(AppProcess(
                        pid=info['pid'],
                        name=info['name'],
                        cmdline=info['cmdline'] or [],
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_mb=(info['memory_info'].rss / 1024 / 1024) if info['memory_info'] else 0.0,
                    ))
                # Also check full command line
                elif info['cmdline']:
                    cmdline_str = ' '.join(info['cmdline']).lower()
                    if app_name_lower in cmdline_str:
                        matches.append(AppProcess(
                            pid=info['pid'],
                            name=info['name'],
                            cmdline=info['cmdline'],
                            cpu_percent=info['cpu_percent'] or 0.0,
                            memory_mb=(info['memory_info'].rss / 1024 / 1024) if info['memory_info'] else 0.0,
                        ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return matches
    
    def kill(self, pid: int, force: bool = False) -> bool:
        """
        Kill a process by PID.
        
        Args:
            pid: Process ID
            force: Use SIGKILL (True) or SIGTERM (False)
            
        Returns:
            True if successful
        """
        try:
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()  # SIGKILL
            else:
                proc.terminate()  # SIGTERM
            
            logger.info(f"Killed process {pid} (force={force})")
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found")
            return False
        except psutil.AccessDenied:
            logger.error(f"Access denied to kill process {pid}")
            return False
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return False
    
    def kill_by_name(self, app_name: str, force: bool = False) -> int:
        """
        Kill all processes matching an app name.
        
        Args:
            app_name: Application name
            force: Use SIGKILL
            
        Returns:
            Number of processes killed
        """
        processes = self.find_processes(app_name)
        killed = 0
        
        for proc in processes:
            if self.kill(proc.pid, force):
                killed += 1
        
        return killed
    
    def get_pid(self, app_name: str) -> Optional[int]:
        """
        Get PID of the first matching process.
        
        Args:
            app_name: Application name
            
        Returns:
            PID or None
        """
        processes = self.find_processes(app_name)
        if processes:
            return processes[0].pid
        return None


# =============================================================================
# SINGLETON
# =============================================================================

_app_launcher_instance: Optional[AppLauncher] = None


def get_app_launcher() -> AppLauncher:
    """Get or create the global app launcher."""
    global _app_launcher_instance
    
    if _app_launcher_instance is None:
        _app_launcher_instance = AppLauncher()
    
    return _app_launcher_instance

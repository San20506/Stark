"""
File Agent
==========
Agent specialized in file system operations.

Capabilities:
- Read files
- Write files (with safety checks)
- List directories
- Search for files
- File metadata operations
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent, AgentResult, AgentType

logger = logging.getLogger(__name__)


class FileAgent(BaseAgent):
    """
    Agent for file system operations.
    
    Handles file reading, writing, listing, and searching with
    built-in safety checks.
    """
    
    def __init__(
        self,
        name: str = "FileAgent",
        allowed_directories: Optional[List[str]] = None,
        max_file_size_mb: float = 10.0,
    ):
        """
        Initialize File Agent.
        
        Args:
            name: Agent name
            allowed_directories: Whitelist of directories (None = all)
            max_file_size_mb: Max file size to read
        """
        super().__init__(
            name=name,
            agent_type=AgentType.FILE,
            description="File system operations (read, write, list, search)",
        )
        
        self.allowed_directories = allowed_directories
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute file operation.
        
        Task format examples:
        - "read /path/to/file.txt"
        - "list /path/to/directory"
        - "search *.py in /path"
        - "write /path output='content'"
        
        Args:
            task: Task description
            context: Optional context with:
                - operation: 'read'|'write'|'list'|'search'
                - path: file/directory path
                - content: content to write (for write op)
                - pattern: search pattern (for search op)
        
        Returns:
            AgentResult with file operation results
        """
        context = context or {}
        steps = []
        
        try:
            # Parse operation from task or context
            operation = context.get('operation')
            path = context.get('path')
            
            if not operation or not path:
                # Try to parse from task string
                operation, path = self._parse_task(task)
            
            if not operation:
                return AgentResult(
                    success=False,
                    output="",
                    error="Could not determine file operation",
                    steps_taken=steps,
                )
            
            # Validate path
            if not self._is_path_allowed(path):
                return AgentResult(
                    success=False,
                    output="",
                    error=f"Path not allowed: {path}",
                    steps_taken=steps,
                )
            
            # Execute operation
            if operation == 'read':
                result = self._read_file(path, steps)
            elif operation == 'list':
                result = self._list_directory(path, steps)
            elif operation == 'search':
                pattern = context.get('pattern', '*.py')
                result = self._search_files(path, pattern, steps)
            elif operation == 'write':
                content = context.get('content', '')
                result = self._write_file(path, content, steps)
            else:
                result = AgentResult(
                    success=False,
                    output="",
                    error=f"Unknown operation: {operation}",
                    steps_taken=steps,
                )
            
            result.steps_taken = steps
            return result
            
        except Exception as e:
            logger.error(f"FileAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )
    
    def _parse_task(self, task: str) -> tuple:
        """Parse operation and path from task string."""
        task_lower = task.lower().strip()
        
        # Simple parsing
        if task_lower.startswith('read '):
            return 'read', task[5:].strip()
        elif task_lower.startswith('list '):
            return 'list', task[5:].strip()
        elif task_lower.startswith('search '):
            # "search pattern in /path"
            parts = task[7:].split(' in ')
            if len(parts) == 2:
                return 'search', parts[1].strip()
        elif task_lower.startswith('write '):
            parts = task[6:].split(' ', 1)
            if parts:
                return 'write', parts[0].strip()
        
        return None, None
    
    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed."""
        if self.allowed_directories is None:
            return True  # All paths allowed
        
        abs_path = os.path.abspath(path)
        
        for allowed_dir in self.allowed_directories:
            allowed_abs = os.path.abspath(allowed_dir)
            if abs_path.startswith(allowed_abs):
                return True
        
        return False
    
    def _read_file(self, path: str, steps: List[str]) -> AgentResult:
        """Read a file."""
        steps.append(f"Reading file: {path}")
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            return AgentResult(success=False, output="", error="File not found")
        
        if not path_obj.is_file():
            return AgentResult(success=False, output="", error="Not a file")
        
        # Check size
        size = path_obj.stat().st_size
        if size > self.max_file_size_bytes:
            return AgentResult(
                success=False,
                output="",
                error=f"File too large: {size / 1024 / 1024:.1f}MB"
            )
        
        # Read file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            steps.append(f"Read {len(content)} characters")
            
            return AgentResult(
                success=True,
                output=content,
            )
        except UnicodeDecodeError:
            # Try binary
            with open(path, 'rb') as f:
                content = f.read()
            return AgentResult(
                success=True,
                output=f"<binary file, {len(content)} bytes>",
            )
    
    def _list_directory(self, path: str, steps: List[str]) -> AgentResult:
        """List directory contents."""
        steps.append(f"Listing directory: {path}")
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            return AgentResult(success=False, output="", error="Directory not found")
        
        if not path_obj.is_dir():
            return AgentResult(success=False, output="", error="Not a directory")
        
        # List contents
        items = []
        for item in sorted(path_obj.iterdir()):
            item_type = "DIR" if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else 0
            items.append(f"{item_type:4} {size:>10} {item.name}")
        
        output = "\n".join(items)
        steps.append(f"Found {len(items)} items")
        
        return AgentResult(
            success=True,
            output=output,
        )
    
    def _search_files(
        self,
        path: str,
        pattern: str,
        steps: List[str]
    ) -> AgentResult:
        """Search for files matching pattern."""
        steps.append(f"Searching for '{pattern}' in {path}")
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            return AgentResult(success=False, output="", error="Path not found")
        
        # Search recursively
        matches = list(path_obj.rglob(pattern))
        
        output = "\n".join([str(m) for m in matches[:100]])  # Limit to 100
        steps.append(f"Found {len(matches)} matches")
        
        return AgentResult(
            success=True,
            output=output,
        )
    
    def _write_file(self, path: str, content: str, steps: List[str]) -> AgentResult:
        """Write content to file."""
        steps.append(f"Writing to file: {path}")
        
        path_obj = Path(path)
        
        # Create parent directories
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        steps.append(f"Wrote {len(content)} characters")
        
        return AgentResult(
            success=True,
            output=f"File written: {path}",
            artifacts_created=[path],
        )

"""
ALFRED MCP Tool Registry
Model Context Protocol-inspired tool discovery and execution.
"""

import datetime
import math
import subprocess
import webbrowser
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import re

logger = logging.getLogger("Alfred.Tools")

# ============================================================================
# LEARNING MEMORY - Store successful patterns
# ============================================================================

class LearningMemory:
    """Store and recall successful query→approach patterns."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            home = Path.home()
            alfred_dir = home / ".alfred"
            alfred_dir.mkdir(exist_ok=True)
            storage_path = alfred_dir / "learned_patterns.json"
        
        self.storage_path = storage_path
        self.patterns: Dict[str, Any] = {}
        self._load()
        logger.info(f"✅ LearningMemory initialized ({len(self.patterns)} patterns)")
    
    def _load(self):
        """Load patterns from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.patterns = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load learning memory: {e}")
                self.patterns = {}
    
    def _save(self):
        """Save patterns to disk."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save learning memory: {e}")
    
    def store(self, key: str, value: str):
        """Store a key-value pair."""
        self.patterns[key.lower()] = value
        self._save()
        logger.info(f"📝 Stored: {key[:30]}...")
    
    def recall(self, key: str) -> Optional[str]:
        """Recall a value by key."""
        result = self.patterns.get(key.lower())
        if result:
            logger.info(f"🔍 Recalled: {key[:30]}...")
        return result
    
    def search_similar(self, query: str, threshold: float = 0.6) -> Optional[str]:
        """Find similar patterns (simple substring matching for now)."""
        query_lower = query.lower()
        for key, value in self.patterns.items():
            if query_lower in key or key in query_lower:
                logger.info(f"🔍 Found similar pattern: {key[:30]}...")
                return value
        return None

# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """MCP-style tool registry for ALFRED."""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.learning_memory = LearningMemory()
        self._register_core_tools()
        logger.info(f"✅ Tool Registry initialized ({len(self.tools)} tools)")
    
    def _register_core_tools(self):
        """Register all core tools."""
        
        # Datetime tool
        self.register("datetime", 
            description="Get current time, date, timezone. Args: format (optional)",
            handler=self._tool_datetime
        )
        
        # Calculator tool
        self.register("calc",
            description="Math calculations. Args: expression (e.g., '25 * 47')",
            handler=self._tool_calc
        )
        
        # Browser tool
        self.register("browser",
            description="Open URLs in browser. Args: url",
            handler=self._tool_browser
        )
        
        # Memory tool
        self.register("memory",
            description="Store/recall info. Args: store:key:value OR recall:key",
            handler=self._tool_memory
        )
        
        # Clipboard tool
        self.register("clipboard",
            description="Copy/paste text. Args: copy:text OR paste",
            handler=self._tool_clipboard
        )
        
        # File tool
        self.register("file",
            description="File operations. Args: read:path OR write:path:content OR list:directory",
            handler=self._tool_file
        )
        
        # Notify tool
        self.register("notify",
            description="System notification. Args: title:message",
            handler=self._tool_notify
        )
        
        # Screenshot tool
        self.register("screenshot",
            description="Capture screen. Args: filename (optional)",
            handler=self._tool_screenshot
        )
    
    def register(self, name: str, description: str, handler: Callable):
        """Register a new tool."""
        self.tools[name] = {
            "description": description,
            "handler": handler
        }
    
    def get_manifest(self) -> str:
        """Generate tool manifest for LLM system prompt."""
        manifest = "AVAILABLE TOOLS:\n"
        for name, info in self.tools.items():
            manifest += f"- <tool:{name} args=\"...\"/> → {info['description']}\n"
        manifest += "\nTo use a tool, output: <tool:name args=\"value\"/>\n"
        manifest += "If you need a tool not listed: <request_tool>description</request_tool>\n"
        return manifest
    
    def execute(self, tool_call: str) -> Optional[str]:
        """Execute a tool from LLM output. Returns result or None."""
        # Parse: <tool:name args="value"/>
        match = re.search(r'<tool:(\w+)(?:\s+args=["\']([^"\']*)["\'])?\s*/>', tool_call)
        if not match:
            return None
        
        name = match.group(1)
        args = match.group(2) or ""
        
        if name not in self.tools:
            return f"Error: Tool '{name}' not found"
        
        try:
            result = self.tools[name]["handler"](args)
            logger.info(f"🔧 Tool {name}: {result[:100] if result else 'OK'}")
            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return f"Error: {e}"
    
    def extract_and_execute_all(self, text: str) -> str:
        """Find all tool calls in text and execute them."""
        results = []
        pattern = r'<tool:\w+(?:\s+args=["\'][^"\']*["\'])?\s*/>'
        
        for match in re.finditer(pattern, text):
            result = self.execute(match.group())
            if result:
                results.append(result)
        
        return "\n".join(results) if results else ""
    
    # ============================================================================
    # TOOL IMPLEMENTATIONS
    # ============================================================================
    
    def _tool_datetime(self, args: str) -> str:
        """Get current date/time."""
        now = datetime.datetime.now()
        
        if "date" in args.lower():
            return now.strftime("%A, %B %d, %Y")
        elif "time" in args.lower():
            return now.strftime("%I:%M %p")
        else:
            return now.strftime("%I:%M %p on %A, %B %d, %Y")
    
    def _tool_calc(self, args: str) -> str:
        """Safe math evaluation."""
        # Sanitize: only allow safe math operations
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in args):
            return "Error: Invalid characters in expression"
        
        try:
            result = eval(args)  # Safe because we sanitized
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"
    
    def _tool_browser(self, args: str) -> str:
        """Open URL in browser."""
        url = args.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        webbrowser.open(url)
        return f"Opened {url}"
    
    def _tool_memory(self, args: str) -> str:
        """Store or recall information from learning memory."""
        if not args:
            return "Error: Memory tool requires args (store:key:value OR recall:key)"
        
        if args.startswith("store:"):
            # Format: store:key:value
            parts = args[6:].split(":", 1)
            if len(parts) < 2:
                return "Error: Store format is store:key:value"
            key, value = parts
            self.learning_memory.store(key.strip(), value.strip())
            return f"Stored: {key.strip()}"
        
        elif args.startswith("recall:"):
            # Format: recall:key
            key = args[7:].strip()
            result = self.learning_memory.recall(key)
            if result:
                return result
            # Try similar search
            result = self.learning_memory.search_similar(key)
            if result:
                return result
            return f"No memory found for: {key}"
        
        else:
            return "Error: Use 'store:key:value' or 'recall:key'"
    
    def _tool_clipboard(self, args: str) -> str:
        """Clipboard operations."""
        try:
            import pyperclip
        except ImportError:
            return "Error: pyperclip not installed (pip install pyperclip)"
        
        if args.startswith("copy:"):
            text = args[5:]
            pyperclip.copy(text)
            return f"Copied to clipboard: {text[:50]}..."
        elif args == "paste":
            content = pyperclip.paste()
            return content if content else "Clipboard is empty"
        else:
            return "Error: Use 'copy:text' or 'paste'"
    
    def _tool_file(self, args: str) -> str:
        """File operations."""
        if args.startswith("read:"):
            path = Path(args[5:].strip())
            try:
                content = path.read_text(encoding='utf-8')
                return content[:500] + ("..." if len(content) > 500 else "")
            except Exception as e:
                return f"Error reading file: {e}"
        
        elif args.startswith("write:"):
            parts = args[6:].split(":", 1)
            if len(parts) < 2:
                return "Error: Format is write:path:content"
            path, content = parts
            try:
                Path(path.strip()).write_text(content, encoding='utf-8')
                return f"Wrote to {path.strip()}"
            except Exception as e:
                return f"Error writing file: {e}"
        
        elif args.startswith("list:"):
            directory = Path(args[5:].strip())
            try:
                files = list(directory.iterdir())
                result = "\\n".join([f.name for f in files[:20]])
                if len(files) > 20:
                    result += f"\\n... and {len(files) - 20} more"
                return result
            except Exception as e:
                return f"Error listing directory: {e}"
        
        else:
            return "Error: Use 'read:path', 'write:path:content', or 'list:directory'"
    
    def _tool_notify(self, args: str) -> str:
        """System notification."""
        try:
            from plyer import notification
        except ImportError:
            return "Error: plyer not installed (pip install plyer)"
        
        if ":" not in args:
            return "Error: Format is 'title:message'"
        
        title, message = args.split(":", 1)
        try:
            notification.notify(
                title=title.strip(),
                message=message.strip(),
                app_name="ALFRED",
                timeout=5
            )
            return f"Notification sent: {title}"
        except Exception as e:
            return f"Error sending notification: {e}"
    
    def _tool_screenshot(self, args: str) -> str:
        """Capture screenshot."""
        try:
            import pyautogui
        except ImportError:
            return "Error: pyautogui not installed (pip install pyautogui)"
        
        filename = args.strip() if args.strip() else "screenshot.png"
        if not filename.endswith(".png"):
            filename += ".png"
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            return f"Screenshot saved as {filename}"
        except Exception as e:
            return f"Error taking screenshot: {e}"


# Global instance
tool_registry = ToolRegistry()

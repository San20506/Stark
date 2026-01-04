#!/usr/bin/env python3
"""
ALFRED - Autonomous System Manager Voice Assistant

Microservices Architecture:
- Wake Word (openwakeword): Local CPU detection
- Ear (faster-whisper): Speech-to-text on CPU
- Brain (ollama): Local LLM inference
- Mouth (piper-tts, pyttsx3, edge-tts): 3-tier TTS fallback
- Audio I/O (sounddevice): Non-blocking callbacks
- System Manager: Process, file, app, and drive management

Features:
- Full system-level management capabilities
- App launching (any installed application)
- File organization and management
- Drive/folder sorting and organization
- Process monitoring and control
- Network diagnostics
- Voice-controlled via natural language
- Barge-in interruption support
- Voice activity detection (RMS amplitude-based)
- Linear retry strategy for device errors
- System safety guardrails for dangerous operations
"""

import time
import sys
import threading
import queue
import re
import webbrowser
import logging
import os
import subprocess
import json
import psutil
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import platform

import numpy as np
import sounddevice as sd

# Conversation Database
try:
    from conversation_db import ConversationDatabase
except ImportError:
    ConversationDatabase = None
    print("WARNING: conversation_db not found. Persistent storage disabled.", file=sys.stderr)

# Semantic Memory
try:
    from semantic_memory import SemanticMemory
except ImportError:
    SemanticMemory = None
    print("WARNING: semantic_memory not found. Semantic search disabled.", file=sys.stderr)

# Personality Adaptation
try:
    from personality_adapter import PersonalityAdapter
except ImportError:
    PersonalityAdapter = None
    print("WARNING: personality_adapter not found. Personality adaptation disabled.", file=sys.stderr)

# STT: faster-whisper
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    print("WARNING: faster-whisper not installed. STT disabled.", file=sys.stderr)

# Wake word: openwakeword
try:
    import openwakeword
except ImportError:
    openwakeword = None
    print("WARNING: openwakeword not installed. Wake-word detection disabled.", file=sys.stderr)

# LLM: ollama
try:
    import ollama
except ImportError:
    ollama = None
    print("WARNING: ollama not installed. LLM disabled.", file=sys.stderr)

# TTS: pyttsx3 (primary offline option)
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    print("WARNING: pyttsx3 not installed. pyttsx3 TTS disabled.", file=sys.stderr)

# TTS: piper-tts (high-quality offline)
try:
    from piper.voice import PiperVoice
    import io
    import wave
except ImportError:
    PiperVoice = None
    print("WARNING: piper-tts not installed. Piper TTS disabled.", file=sys.stderr)

# TTS: edge-tts (cloud fallback)
try:
    import asyncio
    import edge_tts
except ImportError:
    edge_tts = None
    print("WARNING: edge-tts not installed. Edge-TTS fallback disabled.", file=sys.stderr)

# Web Search
try:
    from web_search import WebSearcher
except ImportError:
    WebSearcher = None
    print("WARNING: web_search dependencies missing. Internet search disabled.", file=sys.stderr)

# Audio Processing (VAD + Noise Reduction)
try:
    from audio_processor import AudioPreprocessor
except ImportError:
    AudioPreprocessor = None
    print("WARNING: audio_processor not available. Using fallback RMS VAD.", file=sys.stderr)

# MCP Tools (Native capabilities)
try:
    from tools import tool_registry
except ImportError:
    tool_registry = None
    print("WARNING: tools.py not available. Native tools disabled.", file=sys.stderr)

# Reasoning Engine (ToT, Tool Suggestion, Error Recovery)
try:
    from reasoning import ToolSuggester, ReasoningChain, error_recovery
except ImportError:
    ToolSuggester = None
    ReasoningChain = None
    error_recovery = None
    print("WARNING: reasoning.py not available. Advanced reasoning disabled.", file=sys.stderr)

# Skill Request Handler (Ask for what you don't have)
try:
    from skill_request import detect_missing_capability, init_skill_request_handler
    from skill_generator import skill_generator
    from skill_loader import skill_loader
except ImportError:
    detect_missing_capability = None
    init_skill_request_handler = None
    skill_generator = None
    skill_loader = None
    print("WARNING: skill modules not available.", file=sys.stderr)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Production level
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Alfred")


# ============================================================================
# CONFIGURATION CONSTANTS (Tunable)
# ============================================================================

# Audio Settings
SAMPLE_RATE = 16000  # Whisper prefers 16kHz
CHANNELS = 1  # Mono
FRAME_DURATION = 0.1  # 100ms chunks
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DURATION)
RMS_THRESHOLD = 0.008  # VAD trigger (slightly more sensitive)
SILENCE_TIMEOUT = 1.0  # End utterance after 1s silence
PRE_ROLL_SECONDS = 0.5  # Capture 500ms before speech detected

# Model Selection
WHISPER_MODEL = "small.en"  # Upgraded for better accuracy (was base.en)
LLM_MODEL = "llama3.2:3b"  # Fast, snappy responses (alternative: "phi4-mini" if you have 18GB+ RAM)
WAKEWORD_NAME = "alfred"  # Wake word (alfred, alexa, jarvis, hey google, etc.)

# TTS Configuration
PIPER_VOICE_MODEL = "en-us-lessac-medium.onnx"  # Medium quality/speed balance
PIPER_VOICE_QUALITY = "medium"  # low, medium, high

# TTS Fallback Timeouts
EDGE_TTS_TIMEOUT = 2.0  # Seconds before fallback
PYTTSX3_TIMEOUT = 5.0  # Seconds before timeout

# System Personality with MCP Tools and ToT Reasoning
SYSTEM_PROMPT = """You are Alfred, a dry-witted, highly efficient, and slightly sarcastic British butler AI.
You are helpful but brief. Keep responses under 50 words when possible.

AVAILABLE TOOLS:
- <tool:datetime args="time|date"/> → Get current time or date
- <tool:calc args="expression"/> → Math calculations (e.g., "25 * 47")
- <tool:browser args="url"/> → Open URL in browser
- <tool:memory args="store:key:value"/> → Remember information
- <tool:memory args="recall:key"/> → Recall stored information
- <tool:clipboard args="copy:text"/> → Copy text to clipboard
- <tool:clipboard args="paste"/> → Get clipboard content
- <tool:file args="read:path"/> → Read file content
- <tool:file args="write:path:content"/> → Write to file
- <tool:file args="list:directory"/> → List directory contents
- <tool:notify args="title:message"/> → System notification
- <tool:screenshot args="filename"/> → Capture screen
- <cmd>command</cmd> → System commands (browser, app names)
- <search>query</search> → Web search for real-time info

TREE OF THOUGHT REASONING:
For complex requests:
1. Consider 2-3 possible approaches
2. Choose the most direct solution
3. If a tool can answer instantly, USE IT (don't search for "what time is it")
4. If you fail, try an alternative approach

USE NATIVE TOOLS FIRST. Only use <search> for external knowledge you don't have.
If you need a capability not available: <request_tool>description</request_tool>
"""

# Conversation Memory
MAX_CONVERSATION_HISTORY = 10  # Number of exchanges to remember

# Persistent Storage
ENABLE_PERSISTENT_STORAGE = True  # Set to False to use RAM-only mode
CONVERSATION_DB_PATH = None  # None = use default ~/.alfred/conversations.db

# Semantic Memory
ENABLE_SEMANTIC_MEMORY = True  # Set to False to disable semantic search
SEMANTIC_TOP_K = 3  # Number of relevant past exchanges to retrieve

# Personality Adaptation
ENABLE_PERSONALITY_ADAPTATION = True  # Set to False for static personality
ADAPTATION_UPDATE_FREQUENCY = 5  # Update adaptive prompt every N exchanges

# Device retry strategy (linear, not exponential)
DEVICE_RETRY_INTERVAL = 1.0  # seconds
DEVICE_RETRY_ATTEMPTS = 5


# ============================================================================
# SYSTEM MANAGEMENT - APP LAUNCHER & FILE ORGANIZER
# ============================================================================

class AppLauncher:
    """Launch any installed application on the system."""
    
    def __init__(self):
        self.cache_apps = {}
        self.system_type = platform.system()
        
    def find_installed_apps(self) -> Dict[str, str]:
        """Find installed applications on the system."""
        if self.cache_apps:
            return self.cache_apps
        
        apps = {}
        
        try:
            if self.system_type == "Windows":
                apps = self._find_windows_apps()
            elif self.system_type == "Darwin":
                apps = self._find_macos_apps()
            elif self.system_type == "Linux":
                apps = self._find_linux_apps()
        except Exception as e:
            logger.exception(f"Error finding apps: {e}")
        
        self.cache_apps = apps
        return apps
    
    def _find_windows_apps(self) -> Dict[str, str]:
        """Find Windows applications."""
        apps = {}
        try:
            import winreg
            
            # Check Start Menu
            start_menu_path = Path(os.environ.get('APPDATA')) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if start_menu_path.exists():
                for item in start_menu_path.rglob("*.lnk"):
                    app_name = item.stem
                    apps[app_name.lower()] = str(item)
            
            # Check Program Files
            program_files = Path(os.environ.get('ProgramFiles', 'C:\\Program Files'))
            if program_files.exists():
                for exe in program_files.rglob("*.exe"):
                    app_name = exe.stem
                    if len(app_name) > 3:  # Filter out short names
                        apps[app_name.lower()] = str(exe)
            
            program_files_x86 = Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'))
            if program_files_x86.exists():
                for exe in program_files_x86.rglob("*.exe"):
                    app_name = exe.stem
                    if len(app_name) > 3:
                        apps[app_name.lower()] = str(exe)
        
        except Exception as e:
            logger.warning(f"Could not scan Windows apps: {e}")
        
        return apps
    
    def _find_macos_apps(self) -> Dict[str, str]:
        """Find macOS applications."""
        apps = {}
        try:
            for app_path in Path("/Applications").glob("*.app"):
                app_name = app_path.stem
                apps[app_name.lower()] = str(app_path)
        except Exception as e:
            logger.warning(f"Could not scan macOS apps: {e}")
        return apps
    
    def _find_linux_apps(self) -> Dict[str, str]:
        """Find Linux applications."""
        apps = {}
        try:
            result = subprocess.run(
                ["which", "-a", "python", "python3", "node", "git", "vim", "code"],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if line:
                    app_name = Path(line).stem
                    apps[app_name.lower()] = line
        except Exception as e:
            logger.warning(f"Could not scan Linux apps: {e}")
        return apps
    
    def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application by name."""
        apps = self.find_installed_apps()
        app_name_lower = app_name.lower().strip()
        
        # Exact match
        if app_name_lower in apps:
            app_path = apps[app_name_lower]
            return self._execute_app(app_path)
        
        # Fuzzy match (contains)
        matches = [app for app in apps.keys() if app_name_lower in app]
        if matches:
            best_match = matches[0]
            app_path = apps[best_match]
            return self._execute_app(app_path)
        
        return {
            "success": False,
            "error": f"Application '{app_name}' not found",
            "suggestions": [app for app in apps.keys() if app_name_lower[0] == app[0]][:5]
        }
    
    def _execute_app(self, app_path: str) -> Dict[str, Any]:
        """Execute application safely."""
        try:
            if self.system_type == "Windows":
                if app_path.endswith(".lnk"):
                    os.startfile(app_path)
                else:
                    subprocess.Popen(app_path)
            elif self.system_type == "Darwin":
                subprocess.Popen(["open", app_path])
            elif self.system_type == "Linux":
                subprocess.Popen([app_path])
            
            return {
                "success": True,
                "message": f"Launched application: {Path(app_path).stem}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to launch: {str(e)}"
            }
    
    def list_apps(self, prefix: str = None) -> List[str]:
        """List available applications."""
        apps = self.find_installed_apps()
        if prefix:
            return [app for app in apps.keys() if app.startswith(prefix.lower())]
        return list(apps.keys())[:20]  # Limit output


class FileOrganizer:
    """Organize and manage files and folders (non-system)."""
    
    SYSTEM_PATHS = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "/System",
        "/Library",
        "/usr",
        "/etc",
        "/root"
    ]
    
    def __init__(self):
        self.system_type = platform.system()
    
    def is_system_path(self, path: str) -> bool:
        """Check if path is a protected system path."""
        path_lower = Path(path).absolute().as_posix().lower()
        for sys_path in self.SYSTEM_PATHS:
            if path_lower.startswith(sys_path.lower()):
                return True
        return False
    
    def list_files_by_type(self, directory: str) -> Dict[str, List[Dict]]:
        """List files organized by type."""
        if self.is_system_path(directory):
            return {"error": "Cannot organize system paths"}
        
        try:
            files_by_type = {}
            for item in Path(directory).iterdir():
                try:
                    if item.is_file():
                        ext = item.suffix.lower() or "no_extension"
                        if ext not in files_by_type:
                            files_by_type[ext] = []
                        files_by_type[ext].append({
                            "name": item.name,
                            "size_mb": round(item.stat().st_size / (1024**2), 2),
                            "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                        })
                except (PermissionError, OSError):
                    pass
            
            return files_by_type
        except Exception as e:
            return {"error": str(e)}
    
    def organize_files(self, directory: str, strategy: str = "extension") -> Dict[str, Any]:
        """Organize files into subdirectories."""
        if self.is_system_path(directory):
            return {"error": "Cannot organize system paths"}
        
        try:
            moved = 0
            created_dirs = []
            
            for item in Path(directory).iterdir():
                if item.is_file():
                    if strategy == "extension":
                        category = item.suffix.lower()[1:] or "other"
                    elif strategy == "size":
                        size_mb = item.stat().st_size / (1024**2)
                        if size_mb < 1:
                            category = "small"
                        elif size_mb < 100:
                            category = "medium"
                        else:
                            category = "large"
                    elif strategy == "date":
                        mod_date = datetime.fromtimestamp(item.stat().st_mtime)
                        category = mod_date.strftime("%Y-%m")
                    else:
                        continue
                    
                    dest_dir = Path(directory) / category
                    if not dest_dir.exists():
                        dest_dir.mkdir(exist_ok=True)
                        created_dirs.append(category)
                    
                    item.rename(dest_dir / item.name)
                    moved += 1
            
            return {
                "success": True,
                "files_moved": moved,
                "directories_created": created_dirs,
                "strategy": strategy
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_folder_size(self, path: str) -> Dict[str, Any]:
        """Get total size of folder recursively."""
        if self.is_system_path(path):
            return {"error": "Cannot access system paths"}
        
        try:
            total_size = 0
            file_count = 0
            for item in Path(path).rglob("*"):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (PermissionError, OSError):
                        pass
            
            return {
                "path": path,
                "total_size_mb": round(total_size / (1024**2), 2),
                "file_count": file_count
            }
        except Exception as e:
            return {"error": str(e)}
    
    def find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        """Find duplicate files by name."""
        if self.is_system_path(directory):
            return {"error": "Cannot access system paths"}
        
        try:
            file_names = {}
            for item in Path(directory).rglob("*"):
                if item.is_file():
                    name = item.name
                    if name not in file_names:
                        file_names[name] = []
                    file_names[name].append(str(item))
            
            duplicates = {name: paths for name, paths in file_names.items() if len(paths) > 1}
            return duplicates
        except Exception as e:
            return {"error": str(e)}
    
    def clean_empty_folders(self, directory: str) -> Dict[str, Any]:
        """Remove empty subdirectories."""
        if self.is_system_path(directory):
            return {"error": "Cannot modify system paths"}
        
        try:
            removed = 0
            for item in Path(directory).rglob("*"):
                if item.is_dir() and not list(item.iterdir()):
                    item.rmdir()
                    removed += 1
            
            return {"success": True, "folders_removed": removed}
        except Exception as e:
            return {"success": False, "error": str(e)}


class SystemCommandExecutor:
    """Execute system-level operations safely."""
    
    def __init__(self):
        self.safe_mode = True
        self.blocked_patterns = ['rm -rf /', 'format c:', 'del c:\\', 'shutdown', 'reboot']
        self.app_launcher = AppLauncher()
        self.file_organizer = FileOrganizer()
    
    def is_dangerous(self, cmd: str) -> bool:
        """Check if command is potentially dangerous."""
        return any(pattern in cmd.lower() for pattern in self.blocked_patterns)
    
    def execute(self, command: str, require_confirmation: bool = True) -> Dict[str, Any]:
        """Execute shell command safely."""
        try:
            if self.is_dangerous(command) and require_confirmation:
                return {
                    "success": False,
                    "output": f"DANGEROUS OPERATION BLOCKED: {command}",
                    "error": "This operation requires explicit confirmation",
                    "requires_confirmation": True
                }
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command execution timed out (>10s)",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Gather comprehensive system information."""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "virtual_memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent_used": psutil.virtual_memory().percent
            },
            "disk_usage": {
                "total_gb": round(shutil.disk_usage('/').total / (1024**3), 2),
                "free_gb": round(shutil.disk_usage('/').free / (1024**3), 2),
                "percent_used": shutil.disk_usage('/').used / shutil.disk_usage('/').total * 100
            },
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat()
        }
    
    def list_processes(self, filter_name: str = None) -> List[Dict[str, Any]]:
        """List running processes, optionally filtered."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'memory_percent']):
            try:
                if filter_name and filter_name.lower() not in proc.info['name'].lower():
                    continue
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "status": proc.info['status'],
                    "memory_mb": round(proc.memory_info().rss / (1024**2), 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    def kill_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Terminate a process by PID."""
        try:
            p = psutil.Process(pid)
            if force:
                p.kill()
                return {"success": True, "message": f"Process {pid} killed"}
            else:
                p.terminate()
                return {"success": True, "message": f"Process {pid} terminated"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_disk_usage(self, path: str = ".") -> Dict[str, Any]:
        """Get disk usage for a path."""
        try:
            stat = shutil.disk_usage(path)
            return {
                "path": path,
                "total_gb": round(stat.total / (1024**3), 2),
                "used_gb": round(stat.used / (1024**3), 2),
                "free_gb": round(stat.free / (1024**3), 2),
                "percent_used": round((stat.used / stat.total) * 100, 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def list_files(self, directory: str = ".", pattern: str = None) -> List[Dict[str, Any]]:
        """List files in directory."""
        try:
            files = []
            for item in Path(directory).iterdir():
                if pattern and pattern.lower() not in item.name.lower():
                    continue
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size_mb": round(item.stat().st_size / (1024**2), 2) if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            return sorted(files, key=lambda x: x['name'])
        except Exception as e:
            return []
    
    def search_files(self, directory: str, pattern: str) -> List[str]:
        """Search for files matching pattern."""
        try:
            results = []
            for path in Path(directory).rglob(pattern):
                results.append(str(path))
            return results[:20]
        except Exception as e:
            return []
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        try:
            interfaces = {}
            for interface_name, interface_addrs in psutil.net_if_addrs().items():
                interfaces[interface_name] = []
                for addr in interface_addrs:
                    interfaces[interface_name].append({
                        "family": addr.family.name,
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
            return interfaces
        except Exception as e:
            return {"error": str(e)}
    
    def check_port_open(self, host: str, port: int) -> Dict[str, Any]:
        """Check if a network port is open."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            is_open = result == 0
            return {"host": host, "port": port, "open": is_open}
        except Exception as e:
            return {"error": str(e)}



# ============================================================================
# UTILITIES
# ============================================================================

def rms(samples: np.ndarray) -> float:
    """Calculate RMS (Root Mean Square) amplitude for VAD."""
    if samples.size == 0:
        return 0.0
    try:
        normalized = samples.astype("float32") / np.iinfo(samples.dtype).max
        return float(np.sqrt(np.mean(np.square(normalized))))
    except Exception:
        return 0.0


def pack_int16(frames: List[np.ndarray]) -> np.ndarray:
    """Concatenate audio frames into single int16 array."""
    if not frames:
        return np.empty((0,), dtype=np.int16)
    return np.concatenate(frames)


# ============================================================================
# COMMAND PARSER & ROUTER
# ============================================================================

class CommandParser:
    """Parse natural language commands and route to appropriate handlers."""
    
    def __init__(self, executor: SystemCommandExecutor):
        self.executor = executor
        self.llm_client = None
    
    def set_llm_client(self, client):
        """Set the LLM client for intent understanding."""
        self.llm_client = client
    
    def parse_and_execute(self, user_input: str) -> str:
        """Parse user input and execute appropriate system command."""
        user_input = user_input.strip()
        
        # Intent matching with fallback to LLM
        intents = self._match_intents(user_input)
        
        if intents:
            return self._execute_intent(intents[0], user_input)
        else:
            # Fall back to LLM for complex commands
            return self._execute_with_llm(user_input)
    
    def _match_intents(self, text: str) -> List[str]:
        """Match user input against known intents."""
        text_lower = text.lower()
        
        intent_patterns = {
            "open_app": [r"open|launch|start|run\s+(?!.*command)", r"\bapp\b", r"spotify|chrome|firefox|notepad|vscode|discord|telegram"],
            "list_apps": [r"list.*app|available.*app|what.*app"],
            "system_info": [r"system info|system status|what.*running|cpu|memory|disk"],
            "list_processes": [r"list process|show process|running process|what.*running"],
            "organize_files": [r"organize|sort|arrange|clean.*folder"],
            "list_files": [r"list files?|show files?|directory|contents"],
            "disk_usage": [r"disk usage|storage|disk space|free space|folder size"],
            "find_files": [r"find|search.*file|locate"],
            "file_type": [r"by type|group by|organize by type"],
            "network": [r"network|ip address|interface|connection"],
            "memory_check": [r"memory usage|ram|memory"],
            "open_browser": [r"open.*browser|google|search|browse"],
            "help": [r"what can you do|help|commands|capabilities"]
        }
        
        matched = []
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matched.append(intent)
                    break
        
        return matched
    
    def _execute_intent(self, intent: str, user_input: str) -> str:
        """Execute based on matched intent."""
        
        if intent == "open_app":
            # Extract app name
            match = re.search(r'(?:open|launch|start|run)\s+([a-z0-9\s]+)(?:\s|$)', user_input, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip()
                result = self.executor.app_launcher.launch_app(app_name)
                if result['success']:
                    return f"Launching {app_name}..."
                else:
                    suggestions = result.get('suggestions', [])
                    if suggestions:
                        return f"App '{app_name}' not found. Did you mean: {', '.join(suggestions[:3])}?"
                    return f"Could not find app '{app_name}'"
            return "Please specify which app to open"
        
        elif intent == "list_apps":
            apps = self.executor.app_launcher.list_apps()
            return f"Available apps: {', '.join(apps[:10])}"
        
        elif intent == "system_info":
            info = self.executor.get_system_info()
            return self._format_system_info(info)
        
        elif intent == "list_processes":
            processes = self.executor.list_processes()
            top_5 = sorted(processes, key=lambda x: x['memory_mb'], reverse=True)[:5]
            return self._format_processes(top_5)
        
        elif intent == "organize_files":
            match = re.search(r'(?:organize|sort|arrange)\s+([^\s]+)', user_input, re.IGNORECASE)
            if match:
                directory = match.group(1)
                result = self.executor.file_organizer.organize_files(directory)
                if result.get('success'):
                    return f"Organized {result['files_moved']} files into {len(result['directories_created'])} categories"
                return result.get('error', 'Organization failed')
            return "Please specify a directory to organize"
        
        elif intent == "list_files":
            match = re.search(r'in\s+([^\s]+)|of\s+([^\s]+)', user_input)
            directory = (match.group(1) or match.group(2)) if match else "."
            files = self.executor.list_files(directory)
            return self._format_files(files)
        
        elif intent == "disk_usage":
            usage = self.executor.get_disk_usage()
            return f"Disk usage: {usage['percent_used']:.1f}% used. Total: {usage['total_gb']}GB, Free: {usage['free_gb']}GB"
        
        elif intent == "find_files":
            match = re.search(r'(?:find|search|locate)\s+([^\s]+)', user_input, re.IGNORECASE)
            if match:
                pattern = match.group(1)
                results = self.executor.search_files(".", pattern)
                if results:
                    return f"Found {len(results)} files matching '{pattern}': {', '.join([Path(r).name for r in results[:5]])}"
            return "No matching files found"
        
        elif intent == "file_type":
            match = re.search(r'in\s+([^\s]+)', user_input)
            directory = match.group(1) if match else "."
            files_by_type = self.executor.file_organizer.list_files_by_type(directory)
            if "error" not in files_by_type:
                summary = ", ".join([f"{k}: {len(v)} files" for k, v in list(files_by_type.items())[:5]])
                return f"Files in {directory}: {summary}"
            return files_by_type.get('error', 'Could not list files')
        
        elif intent == "network":
            info = self.executor.get_network_info()
            return self._format_network_info(info)
        
        elif intent == "memory_check":
            vm = psutil.virtual_memory()
            return f"Memory: {vm.percent}% used. Available: {round(vm.available/(1024**3), 2)}GB of {round(vm.total/(1024**3), 2)}GB"
        
        elif intent == "open_browser":
            match = re.search(r'(?:open|browse|search|google)\s+(.+)', user_input, re.IGNORECASE)
            if match:
                query = match.group(1)
                webbrowser.open(f"https://www.google.com/search?q={query}")
                return f"Opening search for: {query}"
            return "Please specify what to search"
        
        elif intent == "help":
            return self._get_help_text()
        
        return "Intent recognized but not yet implemented"
    
    def _execute_with_llm(self, user_input: str) -> str:
        """Use LLM to interpret complex commands."""
        if not self.llm_client:
            return "I need LLM client to understand that command"
        
        try:
            prompt = f"""User command: "{user_input}"

Interpret as ONE of: system_query, app_launch, file_operation, process_control, or other.
Respond naturally as Alfred, the system manager."""
            
            response = self.llm_client.chat(prompt)
            return response[:200]  # Limit response length
        except Exception as e:
            logger.exception(f"LLM error: {e}")
            return "I'm afraid my neural pathways are scrambled"
    
    def _format_system_info(self, info: Dict) -> str:
        """Format system info for voice output."""
        return f"""System Status:
{info['platform']} {info['platform_version']}, {info['cpu_count']} cores.
CPU: {info['cpu_percent']}%. 
Memory: {info['virtual_memory']['percent_used']}% used.
Disk: {info['disk_usage']['percent_used']:.1f}% used."""
    
    def _format_processes(self, processes: List[Dict]) -> str:
        """Format process list for voice output."""
        if not processes:
            return "No processes found"
        output = "Top processes: "
        for p in processes[:3]:
            output += f"{p['name']} ({p['memory_mb']}MB), "
        return output.rstrip(", ")
    
    def _format_files(self, files: List[Dict]) -> str:
        """Format file list for voice output."""
        if not files:
            return "Directory is empty"
        output = f"Found {len(files)} items: "
        for f in files[:5]:
            output += f"{f['name']}, "
        return output.rstrip(", ")
    
    def _format_network_info(self, info: Dict) -> str:
        """Format network info for voice output."""
        if not info or "error" in info:
            return "Unable to retrieve network information"
        output = "Network interfaces: "
        for interface, addrs in list(info.items())[:2]:
            for addr in addrs[:1]:
                output += f"{interface} {addr.get('address')}, "
        return output.rstrip(", ")
    
    def _get_help_text(self) -> str:
        """Return help text with available commands."""
        return """I can help you with:
System monitoring: CPU, memory, disk, network status
Process management: list, kill, monitor processes  
File operations: list, search, read, organize, delete
Application control: launch any installed app
Device management: drives, file organization, cleanup
And much more! Just ask what you need."""
class WakeWordDetector:
    """Wrapper for openwakeword with graceful degradation."""

    def __init__(self):
        """Initialize wake word detector with ONNX framework."""
        self.available = False
        self.model = None
        self.oww = None
        
        # Try to import openwakeword
        try:
            import openwakeword
        except ImportError:
            logger.warning("openwakeword not available; wake-word detection will be best-effort via STT.")
            return
        
        # Initialize with ONNX
        try:
            self.oww = openwakeword # Store the module
            # openwakeword API varies; attempt common patterns
            # Use ONNX framework since tflite-runtime isn't available on Windows
            if hasattr(openwakeword, "Model"):
                self.model = openwakeword.Model(inference_framework='onnx')
                logger.info(f"✅ Wake word detector initialized with ONNX")
            else:
                # Fallback to direct class if Model is not a class
                self.model = openwakeword
            self.available = True
        except ImportError:
            logger.warning("⚠️ Wake word disabled: 'openwakeword' not installed.")
            logger.info("   Use manual activation (press Enter) instead.")
            self.model = None
            self.oww = None
            self.available = False
        except Exception as e:
            logger.warning(f"⚠️ Wake word disabled due to error: {e}")
            logger.info("   Use manual activation (press Enter) instead.")
            logger.exception(f"Failed to initialize openwakeword detector: {e}")
            self.model = None
            self.oww = None
            self.available = False

    def detect(self, pcm16: np.ndarray) -> bool:
        """Feed 16-bit mono PCM audio and return True if wake word detected."""
        if not self.available:
            return False
        try:
            # Try common API patterns
            if hasattr(self.model, "process"):
                return bool(self.model.process(pcm16.tobytes()))
            elif hasattr(self.model, "predict"):
                result = self.model.predict(pcm16)
                # result might be dict or float
                if isinstance(result, dict):
                    return bool(result.get(WAKEWORD_NAME, 0) > 0.5)
                return bool(result > 0.5)
            elif hasattr(self.model, "detect"):
                return bool(self.model.detect(pcm16))
            else:
                return False
        except Exception:
            return False


# ============================================================================
# TEXT-TO-SPEECH ENGINE (3-Tier Fallback: Piper → pyttsx3 → edge-tts)
# ============================================================================

class TTSEngine:
    """TTS with barge-in support and automatic fallback."""

    def __init__(self):
        self.piper_voice = None
        self.pyttsx3_engine = None
        self.edge_available = edge_tts is not None
        self.piper_available = False

        self.lock = threading.Lock()
        self.tts_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Initialize Piper (PRIMARY - best quality)
        if PiperVoice is not None:
            try:
                # Try to load Piper voice model
                self.piper_voice = PiperVoice.load(PIPER_VOICE_MODEL)
                self.piper_available = True
                logger.info(f"✅ Piper TTS initialized ({PIPER_VOICE_MODEL}).")
            except Exception as e:
                logger.debug(f"Piper initialization failed: {e}. Will fallback to pyttsx3.")
                self.piper_available = False

        # Initialize pyttsx3 (FALLBACK 1 - cross-platform)
        if pyttsx3 is not None:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                self.pyttsx3_engine.setProperty("rate", 150)
                if not self.piper_available:
                    logger.info("✅ pyttsx3 TTS initialized (primary fallback).")
                else:
                    logger.debug("pyttsx3 available as fallback.")
            except Exception as e:
                logger.warning(f"pyttsx3 initialization failed: {e}")
                self.pyttsx3_engine = None

        if not (self.piper_available or self.pyttsx3_engine or self.edge_available):
            logger.error("❌ No TTS backend available! Install piper-tts, pyttsx3, or edge-tts.")

    def stop(self):
        """Interrupt current speech (barge-in support)."""
        self.stop_event.set()
        try:
            if self.pyttsx3_engine is not None:
                self.pyttsx3_engine.stop()
        except Exception:
            pass

    def speak(self, text: str, on_complete=None):
        """Speak text asynchronously with barge-in support."""
        # Stop any existing speech
        if self.tts_thread and self.tts_thread.is_alive():
            logger.debug("🔇 Barge-in: stopping current speech.")
            self.stop()
            time.sleep(0.1)

        self.stop_event.clear()

        if self.piper_available:
            self.tts_thread = threading.Thread(
                target=self._speak_piper, args=(text, on_complete), daemon=True
            )
        elif self.pyttsx3_engine is not None:
            self.tts_thread = threading.Thread(
                target=self._speak_pyttsx3, args=(text, on_complete), daemon=True
            )
        elif self.edge_available:
            self.tts_thread = threading.Thread(
                target=self._speak_edge, args=(text, on_complete), daemon=True
            )
        else:
            logger.error("No TTS backend available.")
            if on_complete:
                on_complete()
            return

        self.tts_thread.start()

    def _speak_piper(self, text: str, on_complete=None):
        """Piper TTS synthesis (primary, offline, high quality)."""
        if self.piper_voice is None:
            logger.error("Piper voice not loaded.")
            if on_complete:
                on_complete()
            return

        try:
            logger.debug(f"🎤 Speaking (Piper): {text[:50]}...")
            audio_bytes = b""
            for chunk in self.piper_voice.synthesize_stream_raw(text):
                if self.stop_event.is_set():
                    logger.debug("🔇 Piper speech interrupted.")
                    break
                audio_bytes += chunk

            if audio_bytes and not self.stop_event.is_set():
                # Play audio via sounddevice
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float = audio_data.astype(np.float32) / 32768.0
                sd.play(audio_float, samplerate=22050, blocking=True)

        except Exception as e:
            logger.exception(f"Piper TTS error: {e}. Falling back to pyttsx3.")
            if self.pyttsx3_engine is not None:
                self._speak_pyttsx3(text, on_complete)
                return
        finally:
            if on_complete:
                on_complete()

    def _speak_pyttsx3(self, text: str, on_complete=None):
        """pyttsx3 TTS fallback (offline, cross-platform, robotic)."""
        if self.pyttsx3_engine is None:
            logger.error("pyttsx3 engine not available.")
            if on_complete:
                on_complete()
            return

        try:
            logger.info(f"🔊 Speaking (pyttsx3): {text[:80]}...")
            with self.lock:
                self.pyttsx3_engine.say(text)
                self.pyttsx3_engine.runAndWait()
            logger.info("✅ Speech complete.")
        except Exception as e:
            logger.exception(f"pyttsx3 error: {e}")
        finally:
            if on_complete:
                on_complete()

    def _speak_edge(self, text: str, on_complete=None):
        """Edge-TTS cloud fallback (requires internet, best quality)."""
        if edge_tts is None:
            logger.error("edge-tts not available.")
            if on_complete:
                on_complete()
            return

        async def run():
            try:
                logger.debug(f"🎤 Speaking (Edge-TTS): {text[:50]}...")
                communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
                await communicate.save("alfred_tts_out.mp3")
                # Note: Simplified playback; could enhance with actual audio output
                logger.info("✅ Edge-TTS synthesis complete (saved to file).")
            except Exception as e:
                logger.exception(f"Edge-TTS error: {e}")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run())
        except Exception as e:
            logger.exception(f"Edge-TTS async error: {e}")
        finally:
            if on_complete:
                on_complete()


# ============================================================================
# LLM CLIENT (Ollama)
# ============================================================================

class OllamaClient:
    """Wrapper for Ollama LLM inference."""

    def __init__(self):
        self.available = False
        self.client = None

        if ollama is None:
            logger.warning("Ollama not available; LLM features disabled.")
            return

        try:
            self.client = ollama
            self.available = True
            logger.info(f"✅ Ollama client ready (model: {LLM_MODEL}).")
        except Exception as e:
            logger.exception(f"Failed to initialize Ollama client: {e}")
            self.available = False

    def chat(self, prompt: str, system_prompt: str = SYSTEM_PROMPT, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Send chat prompt to Ollama and return response with conversation context."""
        if not self.available:
            logger.warning("Ollama not available. Returning placeholder.")
            return "I'm afraid my neural pathways are currently offline. Please try again when Ollama is running."

        try:
            # Start with system prompt
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history for context (last 5 exchanges)
            if conversation_history:
                for exchange in conversation_history[-5:]:
                    messages.append({"role": "user", "content": exchange.get("user", "")})
                    messages.append({"role": "assistant", "content": exchange.get("assistant", "")})
            
            # Add current user prompt
            messages.append({"role": "user", "content": prompt})

            response = ollama.chat(model=LLM_MODEL, messages=messages, stream=False)

            # Parse response (handles both dict and object return types)
            # Try object attribute access first (newer library versions)
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            
            # Try dictionary access
            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
                if not content:
                    content = response.get("content", "")
                return content
            
            # Try item access on object
            try:
                return response['message']['content']
            except (TypeError, KeyError, IndexError):
                pass
                
            # Fallback
            return str(response)

        except Exception as e:
            logger.exception(f"Ollama chat failed: {e}")
            return f"I apologize, but my circuits are momentarily scrambled. Error: {str(e)[:50]}"


# ============================================================================
# COMMAND EXECUTION (Function Calling)
# ============================================================================

def execute_command(text: str) -> bool:
    """Parse and execute <cmd> and <url> tags from LLM output."""
    try:
        cmds = re.findall(r"<cmd>(.*?)</cmd>", text, flags=re.IGNORECASE)
        urls = re.findall(r"<url>(.*?)</url>", text, flags=re.IGNORECASE)

        if not cmds:
            return False

        for i, cmd in enumerate(cmds):
            cmd_clean = cmd.strip().lower()

            if cmd_clean == "browser":
                url = urls[i] if i < len(urls) else None
                if not url:
                    # Search for http(s) in text
                    m = re.search(r"(https?://[^\s]+)", text)
                    if m:
                        url = m.group(1)

                if url:
                    logger.info(f"🌐 Opening browser: {url}")
                    webbrowser.open(url)
                else:
                    logger.warning("Browser command received but no URL found.")

            elif cmd_clean == "search":
                query = urls[i] if i < len(urls) else "search"
                logger.info(f"🔍 Searching: {query}")
                webbrowser.open(f"https://www.google.com/search?q={query}")

            else:
                logger.warning(f"Unknown command tag: {cmd_clean}")

        return True

    except Exception as e:
        logger.exception(f"Command execution error: {e}")
        return False


# ============================================================================
# ASSISTANT STATE & MAIN PROCESSOR
# ============================================================================

@dataclass
class AssistantState:
    """Global state for the assistant."""

    listening: bool = False
    speaking: bool = False
    last_transcription: str = ""
    wake_event: threading.Event = threading.Event()
    stop_event: threading.Event = threading.Event()
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


class Alfred:
    """Main voice assistant orchestrator with system management."""

    def __init__(self):
        self.audio_q = queue.Queue(maxsize=100)
        self.state = AssistantState()
        self.detector = WakeWordDetector()
        self.tts = TTSEngine()
        self.ollama = OllamaClient()
        self.executor = SystemCommandExecutor()
        self.parser = CommandParser(self.executor)
        self.parser.set_llm_client(self.ollama)
        
        self.web_searcher = WebSearcher() if WebSearcher else None
        if self.web_searcher:
            logger.info("✅ Web Search module initialized.")
        
        # Initialize audio preprocessor (VAD + Noise Reduction)
        # Lower threshold = more sensitive to quiet speech
        self.audio_preprocessor = AudioPreprocessor(vad_threshold=0.3) if AudioPreprocessor else None
        if self.audio_preprocessor:
            logger.info("✅ Audio Preprocessor initialized (Silero VAD + Noise Reduction, threshold=0.3).")
        
        # Initialize reasoning engine (ToT + Tool Suggestion)
        self.tool_suggester = None
        self.reasoning_chain = None
        if ToolSuggester and ReasoningChain and tool_registry:
            try:
                self.tool_suggester = ToolSuggester(
                    tool_registry=tool_registry,
                    learning_memory=tool_registry.learning_memory if tool_registry else None
                )
                self.reasoning_chain = ReasoningChain(self.tool_suggester)
                logger.info("✅ Reasoning engine initialized (ToT + Tool Suggestion)")
            except Exception as e:
                logger.warning(f"Failed to initialize reasoning engine: {e}")
        
        self.db = None
        self.current_conversation_id = None

        # Initialize persistent storage
        if ENABLE_PERSISTENT_STORAGE and ConversationDatabase:
            try:
                self.db = ConversationDatabase(CONVERSATION_DB_PATH)
                # Load or create conversation
                active_conv = self.db.get_active_conversation()
                if active_conv:
                    # Continue previous conversation
                    self.current_conversation_id = active_conv
                    # Load recent history
                    loaded_history = self.db.load_recent_exchanges(active_conv, MAX_CONVERSATION_HISTORY)
                    if loaded_history:
                        self.state.conversation_history = loaded_history
                        logger.info(f"📚 Loaded {len(loaded_history)} exchanges from previous session")
                else:
                    # Start new conversation
                    self.current_conversation_id = self.db.start_conversation()
                    logger.info(f"Started new conversation ID: {self.current_conversation_id}")
            except Exception as e:
                logger.exception(f"Failed to initialize persistent storage: {e}")
                logger.warning("Continuing with RAM-only storage")
                self.db = None
        elif ENABLE_PERSISTENT_STORAGE:
            logger.warning("ConversationDatabase not available. Using RAM-only storage.")
        
        # Initialize semantic memory
        self.semantic_memory = None
        if ENABLE_SEMANTIC_MEMORY and SemanticMemory:
            try:
                self.semantic_memory = SemanticMemory()
                stats = self.semantic_memory.get_stats()
                logger.info(f"✅ Semantic memory initialized: {stats['total_embeddings']} embeddings")
            except Exception as e:
                logger.exception(f"Failed to initialize semantic memory: {e}")
                self.semantic_memory = None
        elif ENABLE_SEMANTIC_MEMORY:
            logger.warning("SemanticMemory not available. Semantic search disabled.")
        
        # Initialize personality adaptation
        self.personality_adapter = None
        self.adaptive_prompt = SYSTEM_PROMPT  # Start with default
        if ENABLE_PERSONALITY_ADAPTATION and PersonalityAdapter and self.db:
            try:
                self.personality_adapter = PersonalityAdapter(self.db)
                stats = self.personality_adapter.get_stats()
                logger.info(f"✅ Personality adaptation enabled (interactions: {stats['interaction_count']})")
            except Exception as e:
                logger.exception(f"Failed to initialize personality adaptation: {e}")
                self.personality_adapter = None
        elif ENABLE_PERSONALITY_ADAPTATION:
            logger.warning("PersonalityAdapter not available. Using static personality.")

        # Load Whisper model
        if WhisperModel is not None:
            try:
                self.whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
                logger.info(f"✅ Whisper model loaded ({WHISPER_MODEL}).")
            except Exception as e:
                logger.exception(f"Failed to load Whisper model: {e}")
                self.whisper_model = None
        else:
            logger.warning("faster-whisper not available; STT disabled.")

        self._stop = threading.Event()
        self.processing_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.listener_stream = None

    def start(self):
        """Start the voice assistant."""
        logger.info("=" * 70)
        logger.info("🤖 ALFRED Voice Assistant Starting...")
        logger.info("=" * 70)

        self._start_audio_listener()
        self.processing_thread.start()

        logger.info(f"🎤 Listening for '{WAKEWORD_NAME.upper()}'...")
        logger.info("(Press Ctrl+C to exit)")

        try:
            while not self._stop.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down...")
            self.stop()

    def stop(self):
        """Stop the voice assistant gracefully."""
        logger.info("Stopping Alfred...")
        self._stop.set()
        if self.listener_stream:
            try:
                self.listener_stream.stop()
                self.listener_stream.close()
            except Exception:
                pass
        self.tts.stop()
        
        # Close database connection
        if self.db:
            try:
                self.db.close()
                logger.info("Database closed")
            except Exception as e:
                logger.exception(f"Error closing database: {e}")
        
        time.sleep(0.2)

    def _start_audio_listener(self):
        """Start audio input stream with device retry logic."""
        def callback(indata, frames, time_info, status):
            if status:
                logger.debug(f"Audio status: {status}")
            try:
                # Convert float32 -1..1 to int16
                arr = (indata[:, 0] * 32767).astype(np.int16)
                try:
                    self.audio_q.put_nowait(arr)
                except queue.Full:
                    logger.debug("Audio queue full; dropping frame.")
            except Exception:
                logger.exception("Error in audio callback.")

        # Linear retry: 1s intervals, 5 attempts
        for attempt in range(1, DEVICE_RETRY_ATTEMPTS + 1):
            try:
                self.listener_stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    blocksize=FRAME_SAMPLES,
                    dtype="float32",
                    channels=CHANNELS,
                    callback=callback,
                )
                self.listener_stream.start()
                logger.info("✅ Audio input stream started.")
                return
            except Exception as e:
                logger.exception(f"Attempt {attempt}/{DEVICE_RETRY_ATTEMPTS} failed: {e}")
                if attempt < DEVICE_RETRY_ATTEMPTS:
                    logger.info(f"⏳ Retrying in {DEVICE_RETRY_INTERVAL}s...")
                    time.sleep(DEVICE_RETRY_INTERVAL)
                else:
                    logger.critical("❌ All audio device attempts failed. Exiting.")
                    self._stop.set()
                    raise

    def _processor_loop(self):
        """Main processing loop: VAD → Wake Word → STT → LLM → TTS."""
        logger.info("🧠 Processor loop started.")

        ring_buffer: List[np.ndarray] = []
        speech_buffer: List[np.ndarray] = []
        silence_start: Optional[float] = None
        in_speech = False
        pre_roll_samples = int(PRE_ROLL_SECONDS * SAMPLE_RATE)

        while not self._stop.is_set():
            try:
                # Get next audio frame
                try:
                    frame = self.audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Maintain ring buffer for pre-roll
                ring_buffer.append(frame)
                total_rb = sum(len(f) for f in ring_buffer)
                while total_rb > pre_roll_samples and ring_buffer:
                    removed = ring_buffer.pop(0)
                    total_rb -= len(removed)

                # Use Silero VAD if available, fallback to RMS
                if self.audio_preprocessor:
                    is_voice = self.audio_preprocessor.is_speech(frame)
                else:
                    # Fallback to RMS-based detection
                    amp = rms(frame)
                    is_voice = amp >= RMS_THRESHOLD
                
                # Debug: Log VAD status occasionally (every 50 frames = 5 seconds)
                if hasattr(self, '_vad_frame_counter'):
                    self._vad_frame_counter += 1
                else:
                    self._vad_frame_counter = 0
                
                if self._vad_frame_counter % 50 == 0:
                    logger.debug(f"VAD status: is_voice={is_voice}, in_speech={in_speech}")

                # Try wake-word detection
                wake_detected = False
                if self.detector.available:
                    try:
                        wake_detected = self.detector.detect(frame)
                    except Exception:
                        wake_detected = False

                if wake_detected:
                    logger.info(f"🎤 {WAKEWORD_NAME.upper()} detected!")
                    speech_buffer = ring_buffer.copy()
                    in_speech = True
                    silence_start = None
                    continue

                # VAD: Start speech on voice detection
                if not in_speech and is_voice:
                    in_speech = True
                    silence_start = None
                    speech_buffer = ring_buffer.copy()
                    speech_buffer.append(frame)
                    logger.debug(f"🎤 Speech detected (VAD triggered)")
                    continue

                if in_speech:
                    speech_buffer.append(frame)

                    if not is_voice:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > SILENCE_TIMEOUT:
                            # End of utterance
                            utterance = pack_int16(speech_buffer)
                            logger.info(f"📝 Utterance captured ({len(utterance)} samples)")

                            # Process in background thread
                            threading.Thread(
                                target=self._handle_utterance, args=(utterance,), daemon=True
                            ).start()

                            # Reset state
                            speech_buffer = []
                            ring_buffer = []
                            in_speech = False
                            silence_start = None
                    else:
                        silence_start = None

            except Exception:
                logger.exception("Error in processor loop.")
                time.sleep(0.1)

    def _handle_utterance(self, pcm16: np.ndarray):
        """Process captured audio utterance: STT → LLM → TTS."""
        # Barge-in: interrupt if speaking
        if self.tts.tts_thread and self.tts.tts_thread.is_alive():
            logger.info("🔇 Barge-in: user started speaking. Stopping TTS.")
            self.tts.stop()
            time.sleep(0.05)

        # Convert to float32 for Whisper
        audio_float = pcm16.astype(np.float32) / 32767.0
        
        # Apply noise reduction if available
        if self.audio_preprocessor:
            try:
                logger.debug("🔇 Applying noise reduction...")
                pcm16_clean = self.audio_preprocessor.preprocess(pcm16)
                audio_float = pcm16_clean.astype(np.float32) / 32767.0
            except Exception as e:
                logger.warning(f"Noise reduction failed: {e}")

        # Transcribe
        transcript = ""
        if self.whisper_model is not None:
            try:
                segments, info = self.whisper_model.transcribe(
                    audio_float, 
                    beam_size=5, 
                    language="en",
                    vad_filter=True  # Enable built-in VAD filtering
                )
                parts = []
                for seg in segments:
                    if hasattr(seg, "text"):
                        parts.append(seg.text)
                    elif isinstance(seg, dict) and "text" in seg:
                        parts.append(seg["text"])
                    else:
                        parts.append(str(seg))
                transcript = " ".join(parts).strip()
                logger.info(f"📢 Transcribed: {transcript}")
            except Exception as e:
                logger.exception(f"Whisper transcription failed: {e}")
                transcript = ""
        else:
            logger.warning("Whisper model not available.")

        if not transcript:
            logger.info("⚠️ No transcription result.")
            return

        self.state.last_transcription = transcript

        # Remove wake word from transcript if present
        transcript_clean = re.sub(
            rf"\b{WAKEWORD_NAME}\b[:,]?\s*", "", transcript, flags=re.IGNORECASE
        )

        # Get semantically relevant context from past conversations
        relevant_exchanges = []
        if self.semantic_memory and ENABLE_SEMANTIC_MEMORY:
            try:
                relevant_exchanges = self.semantic_memory.get_relevant_context(
                    transcript_clean,
                    exclude_recent_n=5,  # Avoid duplicating recent context
                    top_k=SEMANTIC_TOP_K
                )
                if relevant_exchanges:
                    logger.info(f"🔍 Found {len(relevant_exchanges)} semantically relevant exchanges")
                    for i, ex in enumerate(relevant_exchanges, 1):
                        logger.debug(f"   {i}. User: {ex['user'][:50]}... (similarity: {ex.get('similarity', 0)})")
            except Exception as e:
                logger.exception(f"Semantic search failed: {e}")
        
        # Combine semantic (relevant) and temporal (recent) context
        # Semantic first for older but relevant info, then recent for freshness
        combined_history = relevant_exchanges + self.state.conversation_history

        # ---------------------------------------------------------------------
        # REASONING: Generate approach hints (ToT)
        # ---------------------------------------------------------------------
        approach_hint = ""
        if self.reasoning_chain:
            try:
                approaches = self.reasoning_chain.generate_approaches(transcript_clean, n=2)
                if approaches:
                    approach_hint = self.reasoning_chain.format_approach_hint(approaches)
                    logger.info(f"🧠 Generated {len(approaches)} approaches")
            except Exception as e:
                logger.debug(f"Approach generation failed: {e}")

        # ---------------------------------------------------------------------
        # CHECK FOR MISSING CAPABILITY
        # ---------------------------------------------------------------------
        suggested_tools = []
        if self.tool_suggester:
            suggested_tools = self.tool_suggester.suggest(transcript_clean)
        
        # If no tools suggested and query seems like a capability request
        if detect_missing_capability and not suggested_tools:
            missing_msg = detect_missing_capability(
                transcript_clean, 
                tool_registry, 
                self.tool_suggester
            )
            if missing_msg:
                logger.info("❓ Missing capability detected")
                # Respond with the "I don't know how but I can learn" message
                response = missing_msg
                # Speak and return early
                logger.info(f"🎤 Alfred: {response[:80]}...")
                self.tts.speak(response)
                
                # Store exchange
                self.state.conversation_history.append({
                    "user": transcript_clean,
                    "assistant": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Store pending skill request for follow-up
                self.state.pending_skill_request = transcript_clean
                return

        # ---------------------------------------------------------------------
        # CHECK IF USER IS RESPONDING TO LEARN REQUEST
        # ---------------------------------------------------------------------
        if hasattr(self.state, 'pending_skill_request') and self.state.pending_skill_request:
            user_lower = transcript_clean.lower()
            if any(word in user_lower for word in ["yes", "learn", "try", "sure", "go ahead", "please"]):
                # User wants us to learn the skill
                pending_query = self.state.pending_skill_request
                self.state.pending_skill_request = None
                
                # Generate skill name from query
                skill_name = "_".join([w.lower() for w in pending_query.split()[:3] if len(w) > 2])
                skill_name = skill_name.replace("?", "").replace("!", "")[:20]
                
                logger.info(f"🎓 Learning new skill: {skill_name}")
                self.tts.speak("Let me try to learn that for you...")
                
                if skill_generator:
                    success, message = skill_generator.generate_skill(
                        user_request=pending_query,
                        skill_name=skill_name,
                        tool_registry=tool_registry
                    )
                    
                    if success:
                        response = f"I've learned a new skill: {skill_name}! Try asking again."
                    else:
                        response = f"I couldn't learn that automatically. {message}"
                else:
                    response = "Skill learning isn't available right now."
                
                self.tts.speak(response)
                self.state.conversation_history.append({
                    "user": transcript_clean,
                    "assistant": response,
                    "timestamp": datetime.now().isoformat()
                })
                return
            elif any(word in user_lower for word in ["no", "skip", "nevermind", "cancel"]):
                # User doesn't want to learn
                self.state.pending_skill_request = None
                response = "No problem! Is there anything else I can help with?"
                self.tts.speak(response)
                return

        llm_prompt = transcript_clean
        if approach_hint:
            llm_prompt = f"{approach_hint}\n\nUser query: {transcript_clean}"
        
        logger.info(f"💭 Prompting LLM: {transcript_clean[:60]}...")
        response = self.ollama.chat(
            prompt=llm_prompt, 
            system_prompt=self.adaptive_prompt,  # Use adaptive prompt
            conversation_history=combined_history  # Use combined context
        )

        # ---------------------------------------------------------------------
        # MCP Tool Execution Loop
        # ---------------------------------------------------------------------
        if tool_registry and "<tool:" in response:
            try:
                tool_results = tool_registry.extract_and_execute_all(response)
                if tool_results:
                    logger.info(f"🔧 Tool results: {tool_results[:100]}...")
                    # Re-prompt LLM with tool results
                    response = self.ollama.chat(
                        prompt=f"Tool returned: {tool_results}\n\nProvide a brief response to the user.",
                        system_prompt=self.adaptive_prompt,
                        conversation_history=combined_history
                    )
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")

        # ---------------------------------------------------------------------
        # Web Search Loop
        # ---------------------------------------------------------------------
        if self.web_searcher and "<search>" in response:
            try:
                match = re.search(r"<search>(.*?)</search>", response, re.IGNORECASE | re.DOTALL)
                if match:
                    query_text = match.group(1).strip()
                    logger.info(f"🔎 LLM requested search for: '{query_text}'")
                    
                    # Optional: Speak "One moment..." if TTS is free
                    # self.tts.speak("Checking on that...") 

                    # Perform search
                    search_context = self.web_searcher.get_web_context(query_text)
                    
                    # Re-prompt LLM with injected context
                    refined_prompt = f"""[System: The user asked "{transcript_clean}". 
Here is the web search data you requested for "{query_text}":
{search_context[:5000]} 

Instructions: Answer the user's question using this data. Do not output <search> tags again.]"""
                    
                    logger.info("💭 Re-prompting LLM with search results...")
                    
                    # We send this as a new prompt, but logically it replaces the previous turn
                    response = self.ollama.chat(
                        prompt=refined_prompt,
                        system_prompt=self.adaptive_prompt,
                        conversation_history=combined_history
                    )
            except Exception as e:
                logger.error(f"Web search loop failed: {e}")
                response = "I attempted to search for that, but my connection failed. " + response.replace(match.group(0), "")
        # ---------------------------------------------------------------------

        # Store this exchange in conversation history
        self.state.conversation_history.append({
            "user": transcript_clean,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save to database for persistent storage
        if self.db and self.current_conversation_id:
            try:
                self.db.save_exchange(
                    self.current_conversation_id,
                    transcript_clean,
                    response
                )
            except Exception as e:
                logger.exception(f"Failed to save exchange to database: {e}")
        
        # Add to semantic memory for intelligent retrieval
        if self.semantic_memory and ENABLE_SEMANTIC_MEMORY:
            try:
                self.semantic_memory.add_exchange(
                    transcript_clean,
                    response,
                    metadata={"timestamp": datetime.now().isoformat()}
                )
                logger.debug("Added exchange to semantic memory")
            except Exception as e:
                logger.exception(f"Failed to add to semantic memory: {e}")
        
        # ---------------------------------------------------------------------
        # AUTO-LEARNING LOOP (NEW)
        # ---------------------------------------------------------------------
        # If the response used tools successfully, store the pattern
        if tool_registry and ("<tool:" in response or "<search>" in response):
            try:
                # Extract what tools were used
                tools_used = re.findall(r'<tool:(\w+)', response)
                if tools_used:
                    pattern_key = f"query_type:{transcript_clean[:30].lower()}"
                    pattern_value = f"tools_used:{','.join(tools_used)}"
                    tool_registry.learning_memory.store(pattern_key, pattern_value)
                    logger.debug(f"📚 Learned pattern: {tools_used}")
            except Exception as e:
                logger.debug(f"Learning storage failed: {e}")

        # Learn from this interaction and adapt personality
        if self.personality_adapter and ENABLE_PERSONALITY_ADAPTATION:
            try:
                self.personality_adapter.analyze_interaction(transcript_clean, response)
                
                # Every N exchanges, update adaptive prompt
                exchange_count = len(self.state.conversation_history)
                if exchange_count % ADAPTATION_UPDATE_FREQUENCY == 0:
                    self.adaptive_prompt = self.personality_adapter.generate_adaptive_prompt(SYSTEM_PROMPT)
                    stats = self.personality_adapter.get_stats()
                    logger.info(f"🎭 Personality adapted: formality={stats['formality']}, verbosity={stats['verbosity']}, humor={stats['humor']}")
            except Exception as e:
                logger.exception(f"Failed to adapt personality: {e}")
        
        # Prune history to keep only last MAX_CONVERSATION_HISTORY exchanges
        if len(self.state.conversation_history) > MAX_CONVERSATION_HISTORY:
            self.state.conversation_history = self.state.conversation_history[-MAX_CONVERSATION_HISTORY:]
            logger.debug(f"🧠 Pruned conversation history to last {MAX_CONVERSATION_HISTORY} exchanges")

        # Execute any commands in response
        execute_command(response)

        # Speak response (with barge-in support)
        self.state.speaking = True

        def on_complete():
            self.state.speaking = False

        logger.info(f"🎤 Alfred: {response[:80]}...")
        self.tts.speak(response, on_complete=on_complete)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    try:
        alfred = Alfred()
        alfred.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

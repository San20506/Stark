"""
App Discovery
==============
Scan system for installed applications and cache locations.

Enables STARK to discover and launch any app on the system.
"""

import logging
import os
import json
import re
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AppInfo:
    """Information about an installed application."""
    name: str
    exec_path: str
    icon: Optional[str] = None
    comment: Optional[str] = None
    categories: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class AppDiscovery:
    """
    Discover and cache installed applications.
    
    Scans .desktop files in standard Linux locations.
    """
    
    # Standard locations for .desktop files
    DESKTOP_DIRS = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
        "/snap/current/share/applications",
    ]
    
    CACHE_FILE = os.path.expanduser("~/.cache/stark/app_cache.json")
    
    def __init__(self, auto_scan: bool = True):
        """
        Initialize app discovery.
        
        Args:
            auto_scan: Automatically scan for apps on init
        """
        self._apps: Dict[str, AppInfo] = {}
        self._loaded = False
        
        if auto_scan:
            self._load_or_scan()
    
    def _load_or_scan(self):
        """Load from cache or scan if cache doesn't exist."""
        if self._load_cache():
            logger.info(f"Loaded {len(self._apps)} apps from cache")
        else:
            self.scan()
    
    def scan(self) -> int:
        """
        Scan system for installed applications.
        
        Returns:
            Number of apps found
        """
        self._apps.clear()
        
        for desktop_dir in self.DESKTOP_DIRS:
            if os.path.isdir(desktop_dir):
                self._scan_directory(desktop_dir)
        
        # Save to cache
        self._save_cache()
        
        logger.info(f"Discovered {len(self._apps)} applications")
        return len(self._apps)
    
    def _scan_directory(self, directory: str):
        """Scan a directory for .desktop files."""
        try:
            for filename in os.listdir(directory):
                if filename.endswith('.desktop'):
                    filepath = os.path.join(directory, filename)
                    self._parse_desktop_file(filepath)
        except PermissionError:
            logger.debug(f"Permission denied: {directory}")
        except Exception as e:
            logger.debug(f"Error scanning {directory}: {e}")
    
    def _parse_desktop_file(self, filepath: str):
        """Parse a .desktop file and extract app info."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if it's a valid application
            if '[Desktop Entry]' not in content:
                return
            if 'Type=Application' not in content:
                return
            # Note: We include NoDisplay=true apps as they might still be launchable
            
            # Extract fields
            name = self._extract_field(content, 'Name')
            exec_cmd = self._extract_field(content, 'Exec')
            icon = self._extract_field(content, 'Icon')
            comment = self._extract_field(content, 'Comment')
            categories = self._extract_field(content, 'Categories')
            
            if not name or not exec_cmd:
                return
            
            # Clean exec command (remove %u, %f, etc.)
            exec_cmd = re.sub(r'\s*%[a-zA-Z]', '', exec_cmd).strip()
            
            # Create key (lowercase, no spaces)
            key = name.lower().replace(' ', '-')
            
            # Also add common aliases
            aliases = self._generate_aliases(name)
            
            app_info = AppInfo(
                name=name,
                exec_path=exec_cmd,
                icon=icon,
                comment=comment,
                categories=categories.split(';') if categories else None,
            )
            
            # Store under main key and aliases
            self._apps[key] = app_info
            for alias in aliases:
                if alias not in self._apps:
                    self._apps[alias] = app_info
                    
        except Exception as e:
            logger.debug(f"Error parsing {filepath}: {e}")
    
    def _extract_field(self, content: str, field: str) -> Optional[str]:
        """Extract a field value from .desktop file content."""
        pattern = rf'^{field}=(.+)$'
        match = re.search(pattern, content, re.MULTILINE)
        return match.group(1).strip() if match else None
    
    def _generate_aliases(self, name: str) -> List[str]:
        """Generate common aliases for an app name."""
        aliases = []
        name_lower = name.lower()
        
        # Add lowercase version
        aliases.append(name_lower)
        
        # Add without spaces
        aliases.append(name_lower.replace(' ', ''))
        
        # Add first word
        first_word = name_lower.split()[0] if ' ' in name_lower else None
        if first_word:
            aliases.append(first_word)
        
        # Common abbreviations
        if 'google chrome' in name_lower:
            aliases.extend(['chrome', 'google-chrome'])
        if 'visual studio code' in name_lower:
            aliases.extend(['vscode', 'code', 'vs-code'])
        if 'firefox' in name_lower:
            aliases.append('firefox')
        if 'terminal' in name_lower:
            aliases.append('terminal')
        if 'file' in name_lower and 'manager' in name_lower:
            aliases.extend(['files', 'nautilus'])
        
        return aliases
    
    def find(self, app_name: str) -> Optional[AppInfo]:
        """
        Find an application by name.
        
        Args:
            app_name: Application name or alias
            
        Returns:
            AppInfo or None if not found
        """
        if not self._loaded and not self._apps:
            self._load_or_scan()
        
        key = app_name.lower().replace(' ', '-')
        
        # Exact match
        if key in self._apps:
            return self._apps[key]
        
        # Partial match
        for app_key, app_info in self._apps.items():
            if key in app_key or key in app_info.name.lower():
                return app_info
        
        return None
    
    def list_apps(self) -> List[str]:
        """List all discovered app names."""
        if not self._apps:
            self._load_or_scan()
        
        # Return unique names
        seen = set()
        names = []
        for app_info in self._apps.values():
            if app_info.name not in seen:
                seen.add(app_info.name)
                names.append(app_info.name)
        return sorted(names)
    
    def _save_cache(self):
        """Save app cache to disk."""
        try:
            cache_dir = os.path.dirname(self.CACHE_FILE)
            os.makedirs(cache_dir, exist_ok=True)
            
            # Convert to JSON-serializable format
            cache_data = {k: v.to_dict() for k, v in self._apps.items()}
            
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Saved app cache to {self.CACHE_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save app cache: {e}")
    
    def _load_cache(self) -> bool:
        """Load app cache from disk."""
        try:
            if not os.path.exists(self.CACHE_FILE):
                return False
            
            with open(self.CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            self._apps = {
                k: AppInfo(**v) for k, v in cache_data.items()
            }
            self._loaded = True
            return True
        except Exception as e:
            logger.debug(f"Failed to load app cache: {e}")
            return False
    
    def refresh(self) -> int:
        """Force rescan of installed apps."""
        return self.scan()


# =============================================================================
# SINGLETON
# =============================================================================

_discovery: Optional[AppDiscovery] = None


def get_app_discovery() -> AppDiscovery:
    """Get or create app discovery singleton."""
    global _discovery
    if _discovery is None:
        _discovery = AppDiscovery()
    return _discovery

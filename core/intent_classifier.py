"""
Intent Classifier
==================
Classifies user queries into actionable intents.

Enables STARK to detect what action the user wants to perform.
"""

import logging
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of actionable intents."""
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SEARCH_WEB = "search_web"
    WRITE_CODE = "write_code"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_COMMAND = "execute_command"
    LIST_APPS = "list_apps"
    SYSTEM_INFO = "system_info"
    CONVERSATION = "conversation"  # No action, just chat


@dataclass
class Intent:
    """Classified intent from user query."""
    type: IntentType
    target: Optional[str] = None  # e.g., "firefox" for OPEN_APP
    query: str = ""  # Original query
    confidence: float = 0.0
    
    @property
    def is_actionable(self) -> bool:
        """Check if this intent requires execution."""
        return self.type != IntentType.CONVERSATION


class IntentClassifier:
    """
    Classifies user queries into actionable intents.
    
    Uses keyword matching with regex for fast, reliable classification.
    """
    
    # Intent patterns: (regex_pattern, IntentType, target_extraction_pattern)
    INTENT_PATTERNS: List[Tuple[str, IntentType, Optional[str]]] = [
        # OPEN_APP patterns
        (r'\b(open|launch|start|run|fire up)\b.*\b(\w+)\s*$', IntentType.OPEN_APP, r'(\w+)\s*$'),
        (r'\bcan you (open|launch|start)\b.*\b(\w+)', IntentType.OPEN_APP, r'(\w+)\s*[\?\.]?\s*$'),
        (r'\b(open|launch)\s+(\w+)', IntentType.OPEN_APP, r'(open|launch)\s+(\w+)'),
        
        # CLOSE_APP patterns
        (r'\b(close|kill|quit|exit|stop|terminate)\b.*\b(\w+)', IntentType.CLOSE_APP, r'(\w+)\s*$'),
        
        # SEARCH_WEB patterns
        (r'\b(search|google|look up|find online)\b', IntentType.SEARCH_WEB, None),
        (r'\bsearch for\b\s+(.+)', IntentType.SEARCH_WEB, r'search for\s+(.+)'),
        
        # WRITE_CODE patterns
        (r'\b(write|create|generate|make)\b.*(code|function|script|program)', IntentType.WRITE_CODE, None),
        (r'\bcode\b.*(to|that|for)', IntentType.WRITE_CODE, None),
        
        # READ_FILE patterns
        (r'\b(read|show|display|cat|view)\b.*\b(file|content)', IntentType.READ_FILE, None),
        
        # LIST_APPS patterns
        (r'\b(list|show)\b.*(apps?|applications?|running|processes)', IntentType.LIST_APPS, None),
        
        # SYSTEM_INFO patterns
        (r'\b(system|cpu|memory|disk|battery)\b.*(info|status|usage)', IntentType.SYSTEM_INFO, None),
    ]
    
    # App name aliases
    APP_ALIASES = {
        'browser': 'firefox',
        'chrome': 'google-chrome',
        'code': 'code',
        'vscode': 'code',
        'vs code': 'code',
        'editor': 'gedit',
        'text editor': 'gedit',
        'terminal': 'gnome-terminal',
        'files': 'nautilus',
        'file manager': 'nautilus',
        'calculator': 'gnome-calculator',
        'settings': 'gnome-control-center',
        'music': 'rhythmbox',
        'video': 'totem',
        'photos': 'eog',
        'calendar': 'gnome-calendar',
    }
    
    def __init__(self):
        """Initialize intent classifier."""
        logger.info("IntentClassifier initialized")
    
    def classify(self, query: str) -> Intent:
        """
        Classify a user query into an intent.
        
        Args:
            query: User's natural language query
            
        Returns:
            Intent object with type, target, and confidence
        """
        query_lower = query.lower().strip()
        
        # Try each pattern
        for pattern, intent_type, target_pattern in self.INTENT_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                # Extract target if pattern has capture groups
                target = self._extract_target(query_lower, intent_type, match)
                
                # Resolve app aliases
                if intent_type in (IntentType.OPEN_APP, IntentType.CLOSE_APP):
                    target = self._resolve_app_alias(target)
                
                return Intent(
                    type=intent_type,
                    target=target,
                    query=query,
                    confidence=0.9 if target else 0.7,
                )
        
        # Default to conversation
        return Intent(
            type=IntentType.CONVERSATION,
            target=None,
            query=query,
            confidence=0.5,
        )
    
    def _extract_target(self, query: str, intent_type: IntentType, match) -> Optional[str]:
        """Extract the target from the query based on intent type."""
        
        if intent_type == IntentType.OPEN_APP:
            # Extract app name - last word after open/launch keywords
            # Remove common filler words
            fillers = {'please', 'can', 'you', 'could', 'would', 'the', 'a', 'an', 'my', 'for', 'me', '?', '.'}
            words = query.split()
            
            # Find position of action keyword
            action_idx = -1
            for i, word in enumerate(words):
                if word in ('open', 'launch', 'start', 'run'):
                    action_idx = i
                    break
            
            if action_idx >= 0 and action_idx < len(words) - 1:
                # Get words after the action keyword
                target_words = [w for w in words[action_idx + 1:] if w.lower() not in fillers]
                if target_words:
                    return target_words[0].strip('?.,!')
            
            # Fallback: last word that looks like an app name
            for word in reversed(words):
                word = word.strip('?.,!')
                if word.lower() not in fillers and len(word) > 2:
                    return word
        
        elif intent_type == IntentType.CLOSE_APP:
            # Similar logic for close
            words = query.split()
            for i, word in enumerate(words):
                if word in ('close', 'kill', 'quit', 'stop'):
                    if i < len(words) - 1:
                        return words[i + 1].strip('?.,!')
        
        elif intent_type == IntentType.SEARCH_WEB:
            # Extract search query
            match = re.search(r'(?:search|google|look up|find)\s+(?:for\s+)?(.+)', query, re.IGNORECASE)
            if match:
                return match.group(1).strip('?.,!')
        
        return None
    
    def _resolve_app_alias(self, app_name: Optional[str]) -> Optional[str]:
        """Resolve common app aliases to actual app names."""
        if not app_name:
            return None
        
        app_lower = app_name.lower()
        return self.APP_ALIASES.get(app_lower, app_name)


# =============================================================================
# SINGLETON
# =============================================================================

_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get or create intent classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier

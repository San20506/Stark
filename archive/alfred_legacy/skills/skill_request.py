"""
ALFRED Skill Request Handler
Detects unknown capabilities and asks user for help or offers to learn.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger("Alfred.SkillRequest")

class SkillRequestHandler:
    """Handles requests for unknown skills."""
    
    def __init__(self, tool_registry=None, skill_generator=None):
        self.tool_registry = tool_registry
        self.skill_generator = skill_generator
        self.pending_requests = {}  # Store pending skill requests
        logger.info("✅ SkillRequestHandler initialized")
    
    def check_capability(self, query: str, suggestions: list) -> Tuple[bool, str]:
        """
        Check if ALFRED can handle the query.
        
        Args:
            query: User's query
            suggestions: Tool suggestions from reasoning engine
        
        Returns:
            (can_handle, message)
        """
        # If we have tool suggestions, we can handle it
        if suggestions:
            return True, ""
        
        # Check if query matches any generated skill triggers
        if self.tool_registry:
            for name, tool in self.tool_registry.tools.items():
                desc = tool.get("description", "").lower()
                if any(word in desc for word in query.lower().split() if len(word) > 3):
                    return True, ""
        
        # Can't handle - ask user
        return False, self._generate_help_message(query)
    
    def _generate_help_message(self, query: str) -> str:
        """Generate a message asking for help."""
        return f"""I don't currently have a skill for that. I can:

1️⃣ **Learn it** - I can search online and create a new skill for "{query[:50]}"
2️⃣ **Get info** - You can tell me what API or method to use
3️⃣ **Skip** - We can move on to something else

Would you like me to try learning this capability?"""
    
    def request_skill_creation(self, query: str, skill_name: str) -> Tuple[bool, str]:
        """
        Attempt to create a new skill.
        
        Args:
            query: What the user wants
            skill_name: Name for the new skill
        
        Returns:
            (success, message)
        """
        if not self.skill_generator:
            return False, "Skill generation not available."
        
        logger.info(f"🔨 Attempting to create skill: {skill_name}")
        
        success, message = self.skill_generator.generate_skill(
            user_request=query,
            skill_name=skill_name,
            tool_registry=self.tool_registry
        )
        
        if success:
            return True, f"✅ I've learned a new skill: **{skill_name}**! Try asking again."
        else:
            return False, f"I couldn't learn that automatically. {message}"
    
    def parse_user_response(self, response: str) -> str:
        """
        Parse user's response to help request.
        
        Args:
            response: User's response
        
        Returns:
            Action: "learn", "info", "skip", or "unknown"
        """
        response_lower = response.lower()
        
        if any(word in response_lower for word in ["yes", "learn", "try", "sure", "go ahead", "1"]):
            return "learn"
        elif any(word in response_lower for word in ["info", "tell", "use", "api", "2"]):
            return "info"
        elif any(word in response_lower for word in ["no", "skip", "nevermind", "cancel", "3"]):
            return "skip"
        else:
            return "unknown"


def detect_missing_capability(query: str, tool_registry, suggester) -> Optional[str]:
    """
    Quick check if we're missing a capability.
    
    Args:
        query: User query
        tool_registry: ALFRED's tool registry
        suggester: Tool suggester
    
    Returns:
        Help message if missing capability, None if we can handle it
    """
    # Conversational patterns that should NOT trigger skill learning
    CONVERSATIONAL_PATTERNS = [
        'hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
        'how are you', 'whats up', "what's up", 'sup', 'yo',
        'thanks', 'thank you', 'thanks a lot', 'appreciate it',
        'ok', 'okay', 'alright', 'sure', 'yes', 'no', 'maybe',
        'bye', 'goodbye', 'see you', 'later',
        'umm', 'hmm', 'uh', 'well', 'so',
        'tell me', 'can you', 'could you', 'would you',
        'what is', 'who is', 'where is', 'when is', 'why is', 'how is',
        'help', 'test', 'testing'
    ]
    
    # Check if query is conversational
    query_lower = query.lower()
    for pattern in CONVERSATIONAL_PATTERNS:
        if pattern in query_lower:
            return None  # Let LLM handle conversation
    
    # Check if query contains action verbs (skill indicators)
    ACTION_VERBS = [
        'send', 'email', 'call', 'text', 'message',
        'book', 'schedule', 'reserve', 'order',
        'play', 'stop', 'pause', 'music',
        'turn on', 'turn off', 'set', 'control',
        'translate', 'convert', 'transform'
    ]
    
    has_action = any(verb in query_lower for verb in ACTION_VERBS)
    
    # Get suggestions
    suggestions = suggester.suggest(query) if suggester else []
    
    # Check known tools
    known_keywords = set()
    if tool_registry:
        for name, tool in tool_registry.tools.items():
            known_keywords.add(name)
            desc = tool.get("description", "")
            known_keywords.update(word.lower() for word in desc.split() if len(word) > 3)
    
    # Check if any query word matches our capabilities
    query_words = [w.lower() for w in query.split() if len(w) > 3]
    matches = set(query_words) & known_keywords
    
    # Decision logic:
    # - If we have suggestions → can handle
    # - If matches without action verb → probably conversational
    # - If action verb but no matches → missing capability
    if suggestions or matches:
        return None  # We can handle it
    
    if not has_action:
        return None  # Conversational, let LLM handle
    
    # Generate capability request message (only for clear action requests)
    return f"""Hmm, I'm not sure I can do that yet. 

**What you asked:** "{query[:60]}..."

I could try to **learn this skill** by searching online. Should I try?
(Say "yes" to learn, or tell me more about what you need)"""


# Global instance (initialized when imported)
skill_request_handler = None

def init_skill_request_handler(tool_registry, skill_generator):
    """Initialize the global handler."""
    global skill_request_handler
    skill_request_handler = SkillRequestHandler(tool_registry, skill_generator)
    return skill_request_handler

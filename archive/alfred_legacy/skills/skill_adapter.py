"""
ALFRED Skill Adapter
Adapts found code to ALFRED skill format using LLM.
"""

import logging
import ollama
from typing import Optional
from datetime import datetime

logger = logging.getLogger("Alfred.SkillAdapter")

SKILL_TEMPLATE = '''"""
Skill: {name}
Source: {source_url}
Generated: {date}
"""

from typing import Dict, Any

SKILL_META = {{
    "name": "{name}",
    "triggers": {triggers},
    "requires": {requires},
    "description": "{description}"
}}

def run(**kwargs) -> Any:
    """
    {description}
    
    Args:
        **kwargs: Skill-specific parameters
    
    Returns:
        Result of skill execution
    """
    {code_body}
'''

class SkillAdapter:
    """Adapts found code to ALFRED skill format."""
    
    def __init__(self, model: str = "deepseek-r1:1.5b"):  # Smaller model
        self.model = model
        logger.info(f"✅ SkillAdapter initialized (model: {model})")
    
    def adapt(self, source_code: str, skill_name: str, user_request: str, source_url: str = "") -> Optional[str]:
        """
        Adapt source code to ALFRED skill format.
        """
        # First try: Template-based adaptation (more reliable)
        template_code = self._template_based_adapt(source_code, skill_name, user_request, source_url)
        if template_code:
            return template_code
        
        # Second try: LLM adaptation
        prompt = f"""You are converting Python code to ALFRED skill format.

USER WANTS: {user_request}

FOUND CODE:
```python
{source_code[:1500]}
```

OUTPUT THIS EXACT STRUCTURE (fill in the blanks):

```python
from typing import Any

SKILL_META = {{
    "name": "{skill_name}",
    "triggers": ["keyword1", "keyword2"],
    "requires": ["package1"],
    "description": "Brief description"
}}

def run(**kwargs) -> Any:
    # Your implementation here
    return "result"
```

RULES:
1. Keep SKILL_META exactly as shown
2. Put main logic in run() function
3. Use only safe imports (no os, sys, subprocess)
4. Return a string or dict

OUTPUT ONLY THE CODE, NO EXPLANATIONS:"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Output only Python code. No markdown, no explanations."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            code = response['message']['content'].strip()
            
            # Clean up code
            code = self._extract_code(code)
            
            # Validate basic structure
            if "SKILL_META" in code and "def run(" in code:
                logger.info(f"✅ Adapted skill: {skill_name}")
                return code
            else:
                logger.warning("LLM output missing required structure, using template")
                return self._template_based_adapt(source_code, skill_name, user_request, source_url)
            
        except Exception as e:
            logger.error(f"Adaptation failed: {e}")
            return self._template_based_adapt(source_code, skill_name, user_request, source_url)
    
    def _template_based_adapt(self, source_code: str, skill_name: str, user_request: str, source_url: str) -> str:
        """Template-based adaptation (fallback)."""
        # Extract imports from source
        imports = []
        for line in source_code.split('\n'):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Filter safe imports
                if not any(blocked in line for blocked in ['os', 'sys', 'subprocess']):
                    imports.append(line.strip())
        
        # Extract main logic (simplified)
        main_logic = "    # Adapted from source\n"
        main_logic += "    # TODO: Implement based on source code\n"
        main_logic += "    return 'Not yet implemented'"
        
        # Generate triggers from user request
        triggers = []
        for word in user_request.lower().split():
            if len(word) > 3 and word not in ['the', 'and', 'for', 'with']:
                triggers.append(word)
        triggers = triggers[:5]  # Max 5 triggers
        
        # Build skill
        code = f'''"""
Skill: {skill_name}
Source: {source_url}
Generated: {datetime.now().strftime("%Y-%m-%d")}
"""

from typing import Any
{chr(10).join(imports) if imports else ""}

SKILL_META = {{
    "name": "{skill_name}",
    "triggers": {triggers},
    "requires": [],
    "description": "{user_request[:100]}"
}}

def run(**kwargs) -> Any:
    """
    {user_request}
    
    Args:
        **kwargs: Skill parameters
    
    Returns:
        Result of execution
    """
{main_logic}
'''
        
        logger.info(f"✅ Template-based adaptation: {skill_name}")
        return code
    
    def generate_from_scratch(self, skill_name: str, user_request: str) -> Optional[str]:
        """Generate skill from scratch - simplified for smaller models."""
        
        # Use template directly for reliability
        triggers = [word.lower() for word in user_request.split() if len(word) > 3][:5]
        
        code = f'''"""
Skill: {skill_name}
Generated: {datetime.now().strftime("%Y-%m-%d")}
"""

from typing import Any

SKILL_META = {{
    "name": "{skill_name}",
    "triggers": {triggers},
    "requires": [],
    "description": "{user_request[:100]}"
}}

def run(**kwargs) -> Any:
    """
    {user_request}
    
    Args:
        **kwargs: Skill parameters
    
    Returns:
        Result string
    """
    # TODO: Implement {skill_name}
    # Request: {user_request}
    return "Skill '{skill_name}' not yet fully implemented. Please add implementation."
'''
        
        logger.info(f"✅ Generated template skill: {skill_name}")
        return code
    
    def _extract_code(self, text: str) -> str:
        """Extract Python code from text."""
        # Remove markdown code blocks
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
        
        return text.strip()

# Global instance
skill_adapter = SkillAdapter()

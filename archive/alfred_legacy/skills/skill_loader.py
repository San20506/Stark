"""
ALFRED Skill Loader
Dynamically loads and registers skills.
"""

import logging
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("Alfred.SkillLoader")

class SkillLoader:
    """Loads and manages dynamically generated skills."""
    
    def __init__(self, skills_dir: str = "d:/ALFRED/modules/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py if it doesn't exist
        init_file = self.skills_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# ALFRED Skills\n")
        
        self.loaded_skills = {}
        logger.info(f"✅ SkillLoader initialized (dir: {self.skills_dir})")
    
    def save_skill(self, skill_name: str, code: str) -> bool:
        """
        Save skill to file.
        
        Args:
            skill_name: Name of the skill
            code: Python code
        
        Returns:
            True if saved successfully
        """
        try:
            skill_file = self.skills_dir / f"{skill_name}.py"
            skill_file.write_text(code, encoding='utf-8')
            logger.info(f"💾 Saved skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save skill {skill_name}: {e}")
            return False
    
    def load_skill(self, skill_name: str) -> Optional[any]:
        """
        Load a skill module.
        
        Args:
            skill_name: Name of the skill
        
        Returns:
            Loaded module or None
        """
        try:
            skill_file = self.skills_dir / f"{skill_name}.py"
            if not skill_file.exists():
                logger.warning(f"Skill file not found: {skill_name}")
                return None
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[skill_name] = module
                spec.loader.exec_module(module)
                
                self.loaded_skills[skill_name] = module
                logger.info(f"📦 Loaded skill: {skill_name}")
                return module
            
        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
        
        return None
    
    def load_all_skills(self) -> List[str]:
        """
        Load all skills from directory.
        
        Returns:
            List of loaded skill names
        """
        loaded = []
        
        for skill_file in self.skills_dir.glob("*.py"):
            if skill_file.name.startswith("__"):
                continue
            
            skill_name = skill_file.stem
            if self.load_skill(skill_name):
                loaded.append(skill_name)
        
        logger.info(f"📚 Loaded {len(loaded)} skills")
        return loaded
    
    def register_with_tool_registry(self, skill_name: str, tool_registry) -> bool:
        """
        Register a loaded skill with ALFRED's tool registry.
        
        Args:
            skill_name: Name of the skill
            tool_registry: ALFRED's ToolRegistry instance
        
        Returns:
            True if registered successfully
        """
        try:
            module = self.loaded_skills.get(skill_name)
            if not module:
                module = self.load_skill(skill_name)
            
            if not module:
                return False
            
            # Get skill metadata
            meta = getattr(module, "SKILL_META", {})
            run_func = getattr(module, "run", None)
            
            if not run_func:
                logger.error(f"Skill {skill_name} has no run() function")
                return False
            
            # Register with tool registry
            tool_registry.register(
                name=skill_name,
                description=meta.get("description", f"Generated skill: {skill_name}"),
                handler=lambda args: self._execute_skill(skill_name, args)
            )
            
            logger.info(f"✅ Registered skill: {skill_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register skill {skill_name}: {e}")
            return False
    
    def _execute_skill(self, skill_name: str, args: str) -> str:
        """Execute a skill."""
        try:
            module = self.loaded_skills.get(skill_name)
            if not module:
                return f"Error: Skill {skill_name} not loaded"
            
            run_func = getattr(module, "run")
            
            # Parse args (simple key=value format)
            kwargs = {}
            if args:
                for pair in args.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        kwargs[key.strip()] = value.strip()
            
            result = run_func(**kwargs)
            return str(result)
            
        except Exception as e:
            return f"Error executing skill: {e}"

# Global instance
skill_loader = SkillLoader()

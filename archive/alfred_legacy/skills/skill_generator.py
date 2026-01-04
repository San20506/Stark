"""
ALFRED Skill Generator
Orchestrates the skill generation workflow.
"""

import logging
from typing import Optional
from skill_searcher import skill_searcher
from skill_adapter import skill_adapter
from skill_validator import skill_validator
from skill_loader import skill_loader

logger = logging.getLogger("Alfred.SkillGenerator")

class SkillGenerator:
    """Orchestrates skill generation from search to execution."""
    
    def __init__(self):
        self.searcher = skill_searcher
        self.adapter = skill_adapter
        self.validator = skill_validator
        self.loader = skill_loader
        logger.info("✅ SkillGenerator initialized")
    
    def generate_skill(self, user_request: str, skill_name: str, tool_registry=None) -> tuple[bool, str]:
        """
        Generate a new skill from user request.
        
        Args:
            user_request: What the user wants
            skill_name: Name for the new skill
            tool_registry: ALFRED's tool registry (optional)
        
        Returns:
            (success, message)
        """
        logger.info(f"🔨 Generating skill: {skill_name}")
        logger.info(f"   Request: {user_request}")
        
        # Step 1: Search for existing code
        logger.info("📡 Searching for code solutions...")
        results = self.searcher.search(user_request, max_results=3)
        
        if not results:
            logger.warning("No search results found, generating from scratch...")
            return self._generate_from_scratch(user_request, skill_name, tool_registry)
        
        logger.info(f"   Found {len(results)} results")
        
        # Step 2: Try adapting top results
        for i, result in enumerate(results, 1):
            logger.info(f"   Trying result {i}: {result.title[:50]}...")
            
            if not result.code:
                logger.debug("   No code in result, skipping")
                continue
            
            # Step 3: Adapt code
            adapted_code = self.adapter.adapt(
                source_code=result.code,
                skill_name=skill_name,
                user_request=user_request,
                source_url=result.url
            )
            
            if not adapted_code:
                logger.debug("   Adaptation failed, trying next result")
                continue
            
            # Step 4: Validate
            is_valid, error_msg = self.validator.validate(adapted_code)
            if not is_valid:
                logger.warning(f"   Validation failed: {error_msg}")
                continue
            
            # Step 5: Sandbox test
            test_ok, test_msg = self.validator.sandbox_test(adapted_code)
            if not test_ok:
                logger.warning(f"   Sandbox test failed: {test_msg}")
                continue
            
            # Step 6: Save skill
            if not self.loader.save_skill(skill_name, adapted_code):
                logger.error("   Failed to save skill")
                continue
            
            # Step 7: Load and register
            if tool_registry:
                if self.loader.register_with_tool_registry(skill_name, tool_registry):
                    logger.info(f"✅ Skill generated and registered: {skill_name}")
                    return True, f"Skill '{skill_name}' created successfully from {result.source}"
            else:
                logger.info(f"✅ Skill generated: {skill_name}")
                return True, f"Skill '{skill_name}' created successfully"
        
        # If all results failed, try generating from scratch
        logger.warning("All search results failed, generating from scratch...")
        return self._generate_from_scratch(user_request, skill_name, tool_registry)
    
    def _generate_from_scratch(self, user_request: str, skill_name: str, tool_registry=None) -> tuple[bool, str]:
        """Generate skill from scratch using LLM."""
        logger.info("🤖 Generating skill from scratch...")
        
        # Generate code
        code = self.adapter.generate_from_scratch(skill_name, user_request)
        if not code:
            return False, "Failed to generate skill code"
        
        # Validate
        is_valid, error_msg = self.validator.validate(code)
        if not is_valid:
            return False, f"Generated code failed validation: {error_msg}"
        
        # Sandbox test
        test_ok, test_msg = self.validator.sandbox_test(code)
        if not test_ok:
            return False, f"Generated code failed sandbox test: {test_msg}"
        
        # Save
        if not self.loader.save_skill(skill_name, code):
            return False, "Failed to save generated skill"
        
        # Register
        if tool_registry:
            if self.loader.register_with_tool_registry(skill_name, tool_registry):
                logger.info(f"✅ Skill generated from scratch: {skill_name}")
                return True, f"Skill '{skill_name}' generated from scratch"
        
        return True, f"Skill '{skill_name}' generated (not registered)"

# Global instance
skill_generator = SkillGenerator()

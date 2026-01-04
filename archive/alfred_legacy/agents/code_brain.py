"""
ALFRED Code Brain
DeepSeek V3.2 Speciale integration via HuggingFace for code development.

Features:
- On-demand documentation scraping
- Code generation with context
- Code review and bug fixing
- ALFRED project-aware prompts
"""

import os
import sys
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("CodeBrain")

# Lazy imports for heavy dependencies
torch = None
AutoTokenizer = None
AutoModelForCausalLM = None


def _load_model_deps():
    """Lazy load transformers and torch."""
    global torch, AutoTokenizer, AutoModelForCausalLM
    if torch is None:
        import torch as _torch
        torch = _torch
    if AutoTokenizer is None:
        from transformers import AutoTokenizer as _tok, AutoModelForCausalLM as _model
        AutoTokenizer = _tok
        AutoModelForCausalLM = _model


@dataclass
class CodeResult:
    """Result from code brain."""
    code: str
    explanation: str
    success: bool
    model_used: str
    tokens_used: int


class CodeBrain:
    """
    DeepSeek V3.2 Speciale code development assistant.
    
    Usage:
        brain = CodeBrain()
        brain.initialize()
        
        result = brain.generate_code(
            task="Create a file watcher",
            docs_url="https://pythonhosted.org/watchdog/"
        )
        print(result.code)
    """
    
    # Model - Nemotron 3 Nano (30B with 3B active, optimized for 24GB VRAM)
    MODEL_OPTIONS = {
        "nemotron-nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16",
    }
    
    # ALFRED-specific system prompt
    SYSTEM_PROMPT = """You are ALFRED's Code Brain, a specialized developer assistant.

## Core Rules
1. Follow PEP 8, use type hints, add docstrings (Google style)
2. Use ALFRED project structure:
   - agents/ = Core AI modules
   - core/ = Tool definitions  
   - memory/ = Memory systems
   - utils/ = Utilities
   - tests/ = Test files
3. Return complete, working code
4. Include error handling
5. Use logging, not print statements

## Response Format
Always respond with:
1. Brief explanation of approach
2. Complete code in a code block
3. Usage example if applicable

## Current Task
{task}

## Documentation Context
{context}
"""
    
    def __init__(self, model_size: str = "nemotron-nano"):
        """
        Initialize Code Brain.
        
        Args:
            model_size: Model to use (deepseek-v3.2-speciale, deepseek-coder-7b, deepseek-coder-1.3b)
        """
        self.model_size = model_size
        self.model_id = self.MODEL_OPTIONS.get(model_size, model_size)
        self.model = None
        self.tokenizer = None
        self.scraper = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the model and dependencies.
        
        Returns:
            True if successful
        """
        if self._initialized:
            return True
        
        logger.info(f"🧠 Initializing Code Brain: {self.model_id}")
        
        try:
            _load_model_deps()
            
            # Load doc scraper
            from utils.doc_scraper import get_doc_scraper
            self.scraper = get_doc_scraper()
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                trust_remote_code=True
            )
            
            # Load model with quantization for lower VRAM
            logger.info("Loading model (this may take a few minutes)...")
            
            # Check available VRAM
            if torch.cuda.is_available():
                vram = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"GPU VRAM: {vram:.1f} GB")
                
                from transformers import BitsAndBytesConfig
                
                if vram >= 24:
                    # 24GB+ - Use 8-bit for best quality
                    logger.info("Using 8-bit quantization (24GB+ VRAM)")
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True
                    )
                elif vram >= 16:
                    # 16-24GB - Use 8-bit
                    logger.info("Using 8-bit quantization (16-24GB VRAM)")
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True
                    )
                else:
                    # <16GB - Use 4-bit
                    logger.info("Using 4-bit quantization (<16GB VRAM)")
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16
                    )
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True
                    )
            else:
                # CPU fallback (slow but works)
                logger.warning("No GPU detected, using CPU (will be slow)")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float32,
                    device_map="cpu",
                    trust_remote_code=True
                )
            
            self._initialized = True
            logger.info("✅ Code Brain initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Code Brain: {e}")
            return False
    
    def generate_code(
        self,
        task: str,
        docs_url: str = None,
        context: str = None,
        max_tokens: int = 2048
    ) -> CodeResult:
        """
        Generate code for a development task.
        
        Args:
            task: Description of what to build
            docs_url: Optional URL to scrape for context
            context: Optional manual context
            max_tokens: Maximum tokens in response
            
        Returns:
            CodeResult with generated code
        """
        if not self._initialized:
            if not self.initialize():
                return CodeResult(
                    code="",
                    explanation="Failed to initialize Code Brain",
                    success=False,
                    model_used=self.model_id,
                    tokens_used=0
                )
        
        # Build context from docs
        doc_context = ""
        if docs_url:
            logger.info(f"Scraping docs: {docs_url[:50]}...")
            doc_context = self.scraper.scrape(docs_url, max_length=4000)
        if context:
            doc_context = f"{context}\n\n{doc_context}"
        
        # Build prompt
        system = self.SYSTEM_PROMPT.format(
            task=task,
            context=doc_context[:6000] if doc_context else "No additional context provided."
        )
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Please implement: {task}"}
        ]
        
        # Generate
        try:
            inputs = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt",
                add_generation_prompt=True
            ).to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(
                outputs[0][inputs.shape[1]:],
                skip_special_tokens=True
            )
            
            # Extract code block if present
            code = self._extract_code(response)
            explanation = self._extract_explanation(response)
            
            return CodeResult(
                code=code,
                explanation=explanation,
                success=True,
                model_used=self.model_id,
                tokens_used=len(outputs[0])
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return CodeResult(
                code="",
                explanation=f"Generation failed: {e}",
                success=False,
                model_used=self.model_id,
                tokens_used=0
            )
    
    def review_code(self, code: str, focus: str = "general") -> str:
        """
        Review code and suggest improvements.
        
        Args:
            code: Code to review
            focus: Review focus (general, performance, security, style)
            
        Returns:
            Review feedback
        """
        task = f"""Review the following code with focus on {focus}:

```python
{code}
```

Provide:
1. Issues found (if any)
2. Suggested improvements
3. Overall assessment
"""
        result = self.generate_code(task, max_tokens=1024)
        return result.explanation if result.success else f"Review failed: {result.explanation}"
    
    def fix_bug(self, code: str, error: str) -> CodeResult:
        """
        Fix a bug in code given the error message.
        
        Args:
            code: Buggy code
            error: Error message
            
        Returns:
            CodeResult with fixed code
        """
        task = f"""Fix the bug in this code:

```python
{code}
```

Error message:
{error}

Return the fixed code.
"""
        return self.generate_code(task, max_tokens=2048)
    
    def _extract_code(self, response: str) -> str:
        """Extract code block from response."""
        import re
        
        # Try to find Python code block
        patterns = [
            r'```python\n(.*?)```',
            r'```py\n(.*?)```',
            r'```\n(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Return full response if no code block
        return response.strip()
    
    def _extract_explanation(self, response: str) -> str:
        """Extract explanation (non-code) from response."""
        import re
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        return text.strip()[:500]


# Singleton
_code_brain = None

def get_code_brain(model_size: str = "nemotron-nano") -> CodeBrain:
    """Get or create Code Brain singleton."""
    global _code_brain
    if _code_brain is None:
        _code_brain = CodeBrain(model_size=model_size)
    return _code_brain


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   ALFRED Code Brain Test")
    print("=" * 60)
    
    # Use smaller model for testing
    brain = CodeBrain(model_size="deepseek-coder-1.3b")
    
    print("\n🧠 Initializing (first run downloads model)...")
    if not brain.initialize():
        print("Failed to initialize. Check GPU/dependencies.")
        sys.exit(1)
    
    print("\n📝 Generating code...")
    result = brain.generate_code(
        task="Create a simple file watcher that prints when files change",
        docs_url="https://pythonhosted.org/watchdog/"
    )
    
    if result.success:
        print(f"\n✅ Generated ({result.tokens_used} tokens):")
        print("-" * 60)
        print(result.code[:1000])
        print("-" * 60)
    else:
        print(f"\n❌ Failed: {result.explanation}")
    
    print("\n✅ Done!")

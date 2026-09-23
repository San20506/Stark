"""
STARK LoRA Adapter
==================
Low-Rank Adaptation (LoRA) implementation for task-specific fine-tuning.

Module 4 of 9 - LoRA Adapters
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

import torch
from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
    PeftModel,
)

from core.constants import (
    LORA_RANK,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_TARGET_MODULES,
    ADAPTERS_DIR,
)

logger = logging.getLogger(__name__)


def create_lora_config(
    rank: int = LORA_RANK,
    alpha: int = LORA_ALPHA,
    dropout: float = LORA_DROPOUT,
    target_modules: Optional[List[str]] = None,
    task_type: TaskType = TaskType.CAUSAL_LM,
) -> LoraConfig:
    """
    Create a LoRA configuration.
    
    Args:
        rank: Low-rank dimension (r)
        alpha: Scaling factor
        dropout: Dropout rate for LoRA layers
        target_modules: Which modules to apply LoRA to
        task_type: Type of task (causal LM, seq2seq, etc.)
        
    Returns:
        LoraConfig object
    """
    modules = target_modules or LORA_TARGET_MODULES
    
    config = LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=modules,
        bias="none",
        task_type=task_type,
    )
    
    logger.debug(f"Created LoRA config: r={rank}, alpha={alpha}, modules={modules}")
    return config


def attach_lora(
    model: torch.nn.Module,
    config: Optional[LoraConfig] = None,
) -> PeftModel:
    """
    Attach LoRA layers to a model.
    
    Args:
        model: Base model to attach LoRA to
        config: LoRA configuration (uses defaults if None)
        
    Returns:
        PeftModel with LoRA attached
    """
    if config is None:
        config = create_lora_config()
    
    peft_model = get_peft_model(model, config)
    
    # Log trainable parameters
    trainable, total = get_trainable_params(peft_model)
    logger.info(
        f"LoRA attached: {trainable:,} trainable / {total:,} total "
        f"({100 * trainable / total:.4f}%)"
    )
    
    return peft_model


def get_trainable_params(model: torch.nn.Module) -> tuple:
    """
    Count trainable and total parameters.
    
    Args:
        model: Model to analyze
        
    Returns:
        Tuple of (trainable_params, total_params)
    """
    trainable = 0
    total = 0
    
    for param in model.parameters():
        total += param.numel()
        if param.requires_grad:
            trainable += param.numel()
    
    return trainable, total


def estimate_adapter_size_mb(
    rank: int = LORA_RANK,
    hidden_size: int = 4096,
    num_layers: int = 32,
    num_modules: int = 7,  # q, k, v, o, gate, up, down
) -> float:
    """
    Estimate LoRA adapter size in MB.
    
    Args:
        rank: LoRA rank
        hidden_size: Model hidden dimension
        num_layers: Number of transformer layers
        num_modules: Number of LoRA-adapted modules per layer
        
    Returns:
        Estimated size in MB
    """
    # Each LoRA module has A (hidden x rank) and B (rank x hidden) matrices
    params_per_module = 2 * hidden_size * rank
    total_params = params_per_module * num_modules * num_layers
    
    # Assuming float16 storage (2 bytes per param)
    size_bytes = total_params * 2
    size_mb = size_bytes / (1024 * 1024)
    
    return size_mb


class LoRAAdapter:
    """
    Wrapper for a single LoRA adapter.
    
    Attributes:
        name: Adapter name (usually task name)
        config: LoRA configuration
        path: Path to saved weights
    """
    
    def __init__(
        self,
        name: str,
        rank: int = LORA_RANK,
        alpha: int = LORA_ALPHA,
    ):
        """
        Initialize LoRA adapter.
        
        Args:
            name: Adapter name
            rank: LoRA rank
            alpha: LoRA alpha
        """
        self.name = name
        self.rank = rank
        self.alpha = alpha
        self.config = create_lora_config(rank=rank, alpha=alpha)
        self.path = ADAPTERS_DIR / name
        
        self._is_loaded = False
        self._is_trained = False
        self._training_steps = 0
    
    def save(self, model: PeftModel) -> Path:
        """
        Save adapter weights to disk.
        
        Args:
            model: PeftModel with adapter to save
            
        Returns:
            Path where adapter was saved
        """
        self.path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(self.path))
        
        logger.info(f"Saved adapter '{self.name}' to {self.path}")
        return self.path
    
    def exists(self) -> bool:
        """Check if adapter weights exist on disk."""
        return self.path.exists() and (self.path / "adapter_model.safetensors").exists()
    
    def get_size_mb(self) -> float:
        """Get actual adapter size on disk in MB."""
        if not self.exists():
            return 0.0
        
        total = 0
        for f in self.path.iterdir():
            if f.is_file():
                total += f.stat().st_size
        
        return total / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize adapter metadata."""
        return {
            "name": self.name,
            "rank": self.rank,
            "alpha": self.alpha,
            "path": str(self.path),
            "exists": self.exists(),
            "size_mb": self.get_size_mb(),
            "is_trained": self._is_trained,
            "training_steps": self._training_steps,
        }
    
    def __repr__(self) -> str:
        status = "trained" if self._is_trained else "untrained"
        return f"LoRAAdapter(name={self.name}, r={self.rank}, {status})"

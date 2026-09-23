"""
STARK Adapter Manager
=====================
Manage multiple LoRA adapters with LRU eviction and dynamic loading.

Module 4 of 9 - LoRA Adapters
"""

import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Any

import torch
from peft import PeftModel

from learning.lora_adapter import (
    LoRAAdapter,
    create_lora_config,
    attach_lora,
    get_trainable_params,
)
from core.constants import (
    ADAPTERS_DIR,
    MAX_ACTIVE_ADAPTERS,
    MAX_TOTAL_ADAPTERS,
    LORA_RANK,
    LORA_ALPHA,
    TASK_CATEGORIES,
)

logger = logging.getLogger(__name__)


class AdapterManager:
    """
    Manages multiple LoRA adapters with:
    - LRU eviction when exceeding MAX_ACTIVE_ADAPTERS
    - Dynamic loading/unloading
    - Adapter lifecycle tracking
    
    Usage:
        manager = AdapterManager(base_model)
        manager.create_adapter("error_debugging")
        manager.switch_adapter("error_debugging")
    """
    
    def __init__(
        self,
        base_model: torch.nn.Module,
        adapters_dir: Optional[Path] = None,
        max_active: int = MAX_ACTIVE_ADAPTERS,
    ):
        """
        Initialize adapter manager.
        
        Args:
            base_model: The frozen base model
            adapters_dir: Directory for adapter storage
            max_active: Maximum adapters in memory
        """
        self.base_model = base_model
        self.adapters_dir = adapters_dir or ADAPTERS_DIR
        self.max_active = max_active
        
        # Adapter storage
        self._adapters: Dict[str, LoRAAdapter] = {}
        
        # LRU tracking for loaded adapters
        self._loaded_order: OrderedDict[str, float] = OrderedDict()
        
        # Current active adapter
        self._active_adapter: Optional[str] = None
        self._peft_model: Optional[PeftModel] = None
        
        # Ensure directory exists
        self.adapters_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover existing adapters
        self._discover_adapters()
        
        logger.info(
            f"AdapterManager initialized: {len(self._adapters)} adapters found, "
            f"max_active={max_active}"
        )
    
    # =========================================================================
    # ADAPTER LIFECYCLE
    # =========================================================================
    
    def create_adapter(
        self,
        name: str,
        rank: int = LORA_RANK,
        alpha: int = LORA_ALPHA,
        overwrite: bool = False,
    ) -> LoRAAdapter:
        """
        Create a new LoRA adapter.
        
        Args:
            name: Adapter name (usually task name)
            rank: LoRA rank
            alpha: LoRA alpha
            overwrite: Overwrite if exists
            
        Returns:
            LoRAAdapter object
        """
        if name in self._adapters and not overwrite:
            logger.warning(f"Adapter '{name}' already exists")
            return self._adapters[name]
        
        adapter = LoRAAdapter(name=name, rank=rank, alpha=alpha)
        self._adapters[name] = adapter
        
        logger.info(f"Created adapter '{name}' (r={rank}, alpha={alpha})")
        return adapter
    
    def load_adapter(self, name: str) -> bool:
        """
        Load an adapter into memory.
        
        Args:
            name: Adapter name
            
        Returns:
            True if loaded successfully
        """
        if name not in self._adapters:
            logger.error(f"Adapter '{name}' not found")
            return False
        
        adapter = self._adapters[name]
        
        # Check if already loaded
        if name in self._loaded_order:
            # Move to end (most recently used)
            self._loaded_order.move_to_end(name)
            return True
        
        # Evict if necessary
        self._evict_if_needed()
        
        # Load adapter
        if adapter.exists():
            try:
                self._peft_model = PeftModel.from_pretrained(
                    self.base_model,
                    str(adapter.path),
                    adapter_name=name,
                )
                adapter._is_loaded = True
                self._loaded_order[name] = time.time()
                logger.info(f"Loaded adapter '{name}' from disk")
                return True
            except Exception as e:
                logger.error(f"Failed to load adapter '{name}': {e}")
                return False
        else:
            # Create fresh adapter (not yet trained)
            config = adapter.config
            self._peft_model = attach_lora(self.base_model, config)
            adapter._is_loaded = True
            self._loaded_order[name] = time.time()
            logger.info(f"Created fresh adapter '{name}'")
            return True
    
    def unload_adapter(self, name: str, save: bool = True) -> bool:
        """
        Unload an adapter from memory.
        
        Args:
            name: Adapter name
            save: Save before unloading
            
        Returns:
            True if unloaded successfully
        """
        if name not in self._loaded_order:
            return True  # Already unloaded
        
        adapter = self._adapters.get(name)
        
        if save and adapter and self._peft_model:
            adapter.save(self._peft_model)
        
        # Remove from loaded tracking
        del self._loaded_order[name]
        
        if adapter:
            adapter._is_loaded = False
        
        # If this was active, clear active
        if self._active_adapter == name:
            self._active_adapter = None
        
        logger.info(f"Unloaded adapter '{name}'")
        return True
    
    def save_adapter(self, name: str) -> bool:
        """
        Save an adapter to disk.
        
        Args:
            name: Adapter name
            
        Returns:
            True if saved successfully
        """
        if name not in self._adapters:
            logger.error(f"Adapter '{name}' not found")
            return False
        
        adapter = self._adapters[name]
        
        if self._peft_model and name in self._loaded_order:
            adapter.save(self._peft_model)
            return True
        else:
            logger.warning(f"Adapter '{name}' not loaded, cannot save")
            return False
    
    def delete_adapter(self, name: str) -> bool:
        """
        Delete an adapter from disk and memory.
        
        Args:
            name: Adapter name
            
        Returns:
            True if deleted
        """
        if name in self._loaded_order:
            self.unload_adapter(name, save=False)
        
        adapter = self._adapters.pop(name, None)
        
        if adapter and adapter.path.exists():
            import shutil
            shutil.rmtree(adapter.path)
            logger.info(f"Deleted adapter '{name}'")
            return True
        
        return False
    
    # =========================================================================
    # ADAPTER SWITCHING
    # =========================================================================
    
    def switch_adapter(self, name: str) -> bool:
        """
        Switch to a different adapter.
        
        Args:
            name: Adapter name
            
        Returns:
            True if switched successfully
        """
        if name == self._active_adapter:
            return True  # Already active
        
        # Ensure adapter is loaded
        if name not in self._loaded_order:
            if not self.load_adapter(name):
                return False
        
        # Switch active adapter
        if self._peft_model and hasattr(self._peft_model, 'set_adapter'):
            try:
                self._peft_model.set_adapter(name)
                self._active_adapter = name
                self._loaded_order.move_to_end(name)
                logger.debug(f"Switched to adapter '{name}'")
                return True
            except Exception as e:
                logger.error(f"Failed to switch adapter: {e}")
                return False
        
        self._active_adapter = name
        return True
    
    def get_active_adapter(self) -> Optional[str]:
        """Get the currently active adapter name."""
        return self._active_adapter
    
    def get_model(self) -> Optional[PeftModel]:
        """Get the current PeftModel with active adapter."""
        return self._peft_model
    
    # =========================================================================
    # LRU EVICTION
    # =========================================================================
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used adapter if at capacity."""
        while len(self._loaded_order) >= self.max_active:
            # Get oldest (first in OrderedDict)
            oldest_name = next(iter(self._loaded_order))
            
            # Don't evict the active adapter
            if oldest_name == self._active_adapter and len(self._loaded_order) > 1:
                self._loaded_order.move_to_end(oldest_name)
                oldest_name = next(iter(self._loaded_order))
            
            logger.info(f"Evicting adapter '{oldest_name}' (LRU)")
            self.unload_adapter(oldest_name, save=True)
    
    # =========================================================================
    # DISCOVERY
    # =========================================================================
    
    def _discover_adapters(self) -> None:
        """Discover existing adapters on disk."""
        if not self.adapters_dir.exists():
            return
        
        for path in self.adapters_dir.iterdir():
            if path.is_dir() and (path / "adapter_config.json").exists():
                name = path.name
                if name not in self._adapters:
                    # Load config to get rank/alpha
                    try:
                        with open(path / "adapter_config.json") as f:
                            config = json.load(f)
                        adapter = LoRAAdapter(
                            name=name,
                            rank=config.get("r", LORA_RANK),
                            alpha=config.get("lora_alpha", LORA_ALPHA),
                        )
                        adapter._is_trained = True
                        self._adapters[name] = adapter
                    except Exception as e:
                        logger.warning(f"Failed to load adapter config for '{name}': {e}")
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        """
        List all known adapters.
        
        Returns:
            List of adapter info dicts
        """
        result = []
        for name, adapter in self._adapters.items():
            info = adapter.to_dict()
            info["is_loaded"] = name in self._loaded_order
            info["is_active"] = name == self._active_adapter
            result.append(info)
        return result
    
    def get_adapter(self, name: str) -> Optional[LoRAAdapter]:
        """Get adapter by name."""
        return self._adapters.get(name)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def create_task_adapters(self) -> List[str]:
        """
        Create adapters for all defined task categories.
        
        Returns:
            List of created adapter names
        """
        created = []
        for task in TASK_CATEGORIES:
            if task not in self._adapters:
                self.create_adapter(task)
                created.append(task)
        return created
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter manager statistics."""
        total_size = sum(a.get_size_mb() for a in self._adapters.values())
        
        return {
            "total_adapters": len(self._adapters),
            "loaded_adapters": len(self._loaded_order),
            "active_adapter": self._active_adapter,
            "total_size_mb": total_size,
            "max_active": self.max_active,
            "adapters": [a.to_dict() for a in self._adapters.values()],
        }
    
    def __len__(self) -> int:
        return len(self._adapters)
    
    def __repr__(self) -> str:
        return (
            f"AdapterManager(total={len(self._adapters)}, "
            f"loaded={len(self._loaded_order)}, active={self._active_adapter})"
        )


# =============================================================================
# SINGLETON
# =============================================================================

_manager_instance: Optional[AdapterManager] = None


def get_adapter_manager(base_model: torch.nn.Module) -> AdapterManager:
    """
    Get or create the global adapter manager.
    
    Args:
        base_model: Base model for adapter attachment
        
    Returns:
        AdapterManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = AdapterManager(base_model)
    
    return _manager_instance

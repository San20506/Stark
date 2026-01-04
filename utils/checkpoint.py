"""
STARK Checkpoint Manager
========================
Atomic save/load of system state including adapters, memory, and optimizer.

Module 9 of 9 - Utilities
"""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.constants import (
    CHECKPOINTS_DIR,
    CHECKPOINT_INTERVAL_STEPS,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages STARK system checkpoints with atomic saves.
    
    Features:
    - Atomic writes (temp file + rename)
    - Versioned checkpoints with pruning
    - Separate adapter, memory, and optimizer state
    - Recovery from latest checkpoint
    
    Usage:
        ckpt = CheckpointManager()
        ckpt.save({"adapters": {...}, "memory": {...}})
        state = ckpt.load()
    """
    
    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        max_checkpoints: int = 5,
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory for checkpoints
            max_checkpoints: Maximum checkpoints to keep
        """
        self.checkpoint_dir = checkpoint_dir or CHECKPOINTS_DIR
        self.max_checkpoints = max_checkpoints
        
        # Create directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"CheckpointManager initialized: {self.checkpoint_dir}")
    
    # =========================================================================
    # SAVE OPERATIONS
    # =========================================================================
    
    def save(
        self,
        state: Dict[str, Any],
        name: Optional[str] = None,
    ) -> Path:
        """
        Save checkpoint atomically.
        
        Args:
            state: State dictionary to save
            name: Optional checkpoint name (default: timestamp)
            
        Returns:
            Path to saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = name or f"checkpoint_{timestamp}"
        
        checkpoint_path = self.checkpoint_dir / f"{name}.json"
        temp_path = checkpoint_path.with_suffix(".tmp")
        
        # Atomic write: write to temp, then rename
        try:
            # Add metadata
            state["_metadata"] = {
                "timestamp": timestamp,
                "name": name,
                "version": "1.0",
            }
            
            # Write to temp file
            with open(temp_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            
            # Atomic rename
            temp_path.replace(checkpoint_path)
            
            logger.info(f"Saved checkpoint: {checkpoint_path}")
            
            # Prune old checkpoints
            self._prune_old_checkpoints()
            
            return checkpoint_path
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def save_component(
        self,
        component_name: str,
        state: Dict[str, Any],
    ) -> Path:
        """
        Save a single component checkpoint.
        
        Args:
            component_name: Name of component (e.g., "adapters", "memory")
            state: Component state
            
        Returns:
            Path to saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.save(
            {component_name: state},
            name=f"{component_name}_{timestamp}"
        )
    
    # =========================================================================
    # LOAD OPERATIONS
    # =========================================================================
    
    def load(
        self,
        name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint.
        
        Args:
            name: Checkpoint name (default: latest)
            
        Returns:
            State dictionary or None if not found
        """
        if name:
            checkpoint_path = self.checkpoint_dir / f"{name}.json"
        else:
            checkpoint_path = self._get_latest_checkpoint()
        
        if not checkpoint_path or not checkpoint_path.exists():
            logger.info("No checkpoint found")
            return None
        
        try:
            with open(checkpoint_path, "r") as f:
                state = json.load(f)
            
            logger.info(f"Loaded checkpoint: {checkpoint_path}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def load_latest(self) -> Optional[Dict[str, Any]]:
        """Load the most recent checkpoint."""
        return self.load()
    
    def load_component(
        self,
        component_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Load latest checkpoint for a specific component.
        
        Args:
            component_name: Component to load
            
        Returns:
            Component state or None
        """
        checkpoints = self._list_checkpoints(prefix=component_name)
        if not checkpoints:
            return None
        
        state = self.load(checkpoints[0].stem)
        return state.get(component_name) if state else None
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _get_latest_checkpoint(self) -> Optional[Path]:
        """Get path to most recent checkpoint."""
        checkpoints = self._list_checkpoints()
        return checkpoints[0] if checkpoints else None
    
    def _list_checkpoints(
        self,
        prefix: Optional[str] = None,
    ) -> List[Path]:
        """List checkpoints sorted by modification time (newest first)."""
        pattern = f"{prefix}*.json" if prefix else "*.json"
        checkpoints = list(self.checkpoint_dir.glob(pattern))
        checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return checkpoints
    
    def _prune_old_checkpoints(self) -> None:
        """Remove checkpoints beyond max_checkpoints."""
        checkpoints = self._list_checkpoints()
        
        if len(checkpoints) > self.max_checkpoints:
            for old_ckpt in checkpoints[self.max_checkpoints:]:
                try:
                    old_ckpt.unlink()
                    logger.debug(f"Pruned old checkpoint: {old_ckpt}")
                except Exception as e:
                    logger.warning(f"Failed to prune checkpoint: {e}")
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all checkpoints with metadata.
        
        Returns:
            List of checkpoint info dicts
        """
        result = []
        for ckpt in self._list_checkpoints():
            result.append({
                "name": ckpt.stem,
                "path": str(ckpt),
                "size_kb": ckpt.stat().st_size / 1024,
                "modified": datetime.fromtimestamp(ckpt.stat().st_mtime).isoformat(),
            })
        return result
    
    def __repr__(self) -> str:
        count = len(self._list_checkpoints())
        return f"CheckpointManager(checkpoints={count}, dir={self.checkpoint_dir})"


# =============================================================================
# SINGLETON
# =============================================================================

_checkpoint_instance: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create the global checkpoint manager."""
    global _checkpoint_instance
    
    if _checkpoint_instance is None:
        _checkpoint_instance = CheckpointManager()
    
    return _checkpoint_instance

"""
STARK Dynamic Configuration
===========================
Runtime configuration management with YAML support and validation.

Module 1 of 9 - Core Infrastructure
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator

from core.constants import (
    PROJECT_ROOT,
    DATA_DIR,
    MODELS_DIR,
    CHECKPOINTS_DIR,
    LOGS_DIR,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    BASE_MODEL_NAME,
    MAX_LENGTH,
    BATCH_SIZE,
    LEARNING_RATE,
    LORA_RANK,
    LORA_ALPHA,
    MEMORY_MAX_NODES,
    TRAIN_INTERVAL_SECONDS,
    TASK_DETECTION_THRESHOLD,
    GPU_DEVICE,
    VRAM_LIMIT_GB,
    LOG_LEVEL,
    MCP_SERVER_ENABLED,
    MCP_SERVER_HOST,
    MCP_SERVER_PORT,
    MCP_CLIENT_ENABLED,
    MCP_CLIENT_TIMEOUT_SECONDS,
    MCP_MAX_EXTERNAL_SERVERS,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURATION MODELS (Pydantic for validation)
# ==============================================================================

class ModelConfig(BaseModel):
    """Model-related configuration for Ollama."""
    
    name: str = Field(default=OLLAMA_MODEL, description="Ollama model name")
    base_url: str = Field(default=OLLAMA_BASE_URL, description="Ollama API URL")
    max_length: int = Field(default=MAX_LENGTH, ge=1, le=32768)
    device: str = Field(default=GPU_DEVICE)


class LoRAConfig(BaseModel):
    """LoRA adapter configuration."""
    
    rank: int = Field(default=LORA_RANK, ge=1, le=128)
    alpha: int = Field(default=LORA_ALPHA, ge=1, le=256)
    dropout: float = Field(default=0.1, ge=0.0, le=0.5)
    target_modules: list = Field(default=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])


class LearningConfig(BaseModel):
    """Continuous learning configuration."""
    
    batch_size: int = Field(default=BATCH_SIZE, ge=1, le=128)
    learning_rate: float = Field(default=LEARNING_RATE, ge=1e-6, le=1e-2)
    replay_ratio: float = Field(default=0.5, ge=0.0, le=1.0)  # 50% old, 50% new
    train_interval_seconds: int = Field(default=TRAIN_INTERVAL_SECONDS, ge=10)
    memory_capacity: int = Field(default=MEMORY_MAX_NODES, ge=1000)


class TaskConfig(BaseModel):
    """Task detection configuration."""
    
    detection_threshold: float = Field(default=TASK_DETECTION_THRESHOLD, ge=0.0, le=1.0)
    categories: list = Field(default=[
        "error_debugging", "code_explanation", "task_planning",
        "research", "health_monitoring", "system_control",
        "conversation", "math_reasoning"
    ])


class HardwareConfig(BaseModel):
    """Hardware resource configuration."""
    
    device: str = Field(default=GPU_DEVICE)
    vram_limit_gb: float = Field(default=VRAM_LIMIT_GB, ge=1.0)
    use_mixed_precision: bool = Field(default=True)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default=LOG_LEVEL, description="Log level")
    log_to_file: bool = Field(default=True, description="Log to file")
    log_dir: str = Field(default=str(LOGS_DIR))
    
    @validator("level")
    def validate_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"level must be one of {allowed}")
        return v.upper()


class MCPServerConfig(BaseModel):
    """MCP Server configuration."""
    
    enabled: bool = Field(default=MCP_SERVER_ENABLED, description="Enable MCP server")
    host: str = Field(default=MCP_SERVER_HOST, description="MCP server host")
    port: int = Field(default=MCP_SERVER_PORT, description="MCP server port")
    name: str = Field(default="STARK", description="MCP server name")


class MCPClientConfig(BaseModel):
    """MCP Client configuration."""
    
    enabled: bool = Field(default=MCP_CLIENT_ENABLED, description="Enable MCP client")
    timeout_seconds: int = Field(default=MCP_CLIENT_TIMEOUT_SECONDS, description="Client timeout")
    max_servers: int = Field(default=MCP_MAX_EXTERNAL_SERVERS, description="Max external servers")


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration."""
    
    server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    client: MCPClientConfig = Field(default_factory=MCPClientConfig)


class STARKConfig(BaseModel):
    """Root configuration for STARK system."""
    
    model: ModelConfig = Field(default_factory=ModelConfig)
    lora: LoRAConfig = Field(default_factory=LoRAConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    
    # Paths
    project_root: str = Field(default=str(PROJECT_ROOT))
    data_dir: str = Field(default=str(DATA_DIR))
    models_dir: str = Field(default=str(MODELS_DIR))
    checkpoints_dir: str = Field(default=str(CHECKPOINTS_DIR))


# ==============================================================================
# CONFIGURATION LOADER
# ==============================================================================

class ConfigLoader:
    """
    Load and manage STARK configuration from multiple sources.
    
    Priority (highest to lowest):
    1. Environment variables (STARK_*)
    2. YAML config file
    3. Default constants
    """
    
    DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[STARKConfig] = None
        
    def load(self) -> STARKConfig:
        """
        Load configuration from all sources.
        
        Returns:
            STARKConfig: Validated configuration object
        """
        # Start with defaults
        config_dict: Dict[str, Any] = {}
        
        # Load from YAML if exists
        if self.config_path.exists():
            config_dict = self._load_yaml()
            logger.info(f"Loaded config from {self.config_path}")
        else:
            logger.info("No config file found, using defaults")
            
        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)
        
        # Validate and create config object
        self._config = STARKConfig(**config_dict)
        
        return self._config
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load YAML config: {e}")
            return {}
    
def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides.
        
        Environment variables follow pattern: STARK_SECTION_KEY
        Example: STARK_MODEL_NAME, STARK_LEARNING_BATCH_SIZE
        """
        env_mapping = {
            "STARK_MODEL_NAME": ("model", "name"),
            "STARK_MODEL_URL": ("model", "base_url"),
            "STARK_LORA_RANK": ("lora", "rank"),
            "STARK_LORA_ALPHA": ("lora", "alpha"),
            "STARK_LEARNING_ENABLED": ("learning", "enabled"),
            "STARK_LEARNING_BATCH_SIZE": ("learning", "batch_size"),
            "STARK_LEARNING_LR": ("learning", "learning_rate"),
            "STARK_HARDWARE_DEVICE": ("hardware", "device"),
            "STARK_HARDWARE_VRAM_LIMIT": ("hardware", "vram_limit_gb"),
            "STARK_LOG_LEVEL": ("logging", "level"),
            "STARK_MCP_SERVER_ENABLED": ("mcp", "server", "enabled"),
            "STARK_MCP_SERVER_HOST": ("mcp", "server", "host"),
            "STARK_MCP_SERVER_PORT": ("mcp", "server", "port"),
            "STARK_MCP_CLIENT_ENABLED": ("mcp", "client", "enabled"),
            "STARK_MCP_CLIENT_TIMEOUT": ("mcp", "client", "timeout_seconds"),
            "STARK_MCP_MAX_SERVERS": ("mcp", "client", "max_servers"),
        }
        
for env_var, path in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Navigate nested structure
                current = config
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                final_key = path[-1]
                # Type conversion
                if final_key in ("rank", "alpha", "batch_size", "port", "timeout_seconds", "max_servers"):
                    value = int(value)
                elif final_key in ("learning_rate", "vram_limit_gb"):
                    value = float(value)
                elif final_key in ("enabled",):
                    value = value.lower() in ("true", "1", "yes", "on")
                
                current[final_key] = value
                logger.debug(f"Applied env override: {env_var}={value}")
                
        return config
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Output path. If None, uses config_path.
        """
        if self._config is None:
            raise RuntimeError("No configuration loaded")
            
        output_path = path or self.config_path
        with open(output_path, "w") as f:
            yaml.dump(self._config.dict(), f, default_flow_style=False)
        logger.info(f"Saved config to {output_path}")
    
@property
    def config(self) -> STARKConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config  # type: ignore


# ==============================================================================
# GLOBAL CONFIG SINGLETON
# ==============================================================================

_config_loader: Optional[ConfigLoader] = None


def get_config(config_path: Optional[Path] = None) -> STARKConfig:
    """
    Get or create the global configuration singleton.
    
    Args:
        config_path: Optional path to config file (only used on first call)
        
    Returns:
        STARKConfig: The global configuration object
    """
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
        _config_loader.load()
        
    return _config_loader.config


def reload_config(config_path: Optional[Path] = None) -> STARKConfig:
    """
    Force reload configuration from disk.
    
    Args:
        config_path: Optional new path to config file
        
    Returns:
        STARKConfig: The reloaded configuration object
    """
    global _config_loader
    
    _config_loader = ConfigLoader(config_path)
    return _config_loader.load()


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def ensure_directories() -> None:
    """Create all required directories if they don't exist."""
    config = get_config()
    
    directories = [
        Path(config.data_dir),
        Path(config.models_dir),
        Path(config.checkpoints_dir),
        Path(config.logging.log_dir),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")


# ==============================================================================
# MODULE TEST
# ==============================================================================

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("STARK Configuration Test")
    print("=" * 60)
    
    config = get_config()
    
    print(f"\nModel: {config.model.name}")
    print(f"Quantization: {config.model.quantization}")
    print(f"LoRA Rank: {config.lora.rank}")
    print(f"Batch Size: {config.learning.batch_size}")
    print(f"Device: {config.hardware.device}")
    print(f"Log Level: {config.logging.level}")
    
    print("\n✅ Config loaded successfully!")

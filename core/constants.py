"""
STARK System Constants
======================
All system configuration constants in one place.
No hardcoded values anywhere else in the codebase.

Module 1 of 9 - Core Infrastructure
"""

from pathlib import Path
from typing import Final

# ==============================================================================
# SYSTEM PATHS
# ==============================================================================

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"
CHECKPOINTS_DIR: Final[Path] = PROJECT_ROOT / "checkpoints"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"
ADAPTERS_DIR: Final[Path] = MODELS_DIR / "adapters"

# ==============================================================================
# MODEL CONFIGURATION
# ==============================================================================

# Ollama Model Settings
OLLAMA_BASE_URL: Final[str] = "http://127.0.0.1:11434"  # Ollama API endpoint
OLLAMA_DEFAULT_MODEL: Final[str] = "stark-fast"  # Default model for simple tasks

# Task-to-Model Routing (multi-model orchestration)
# STARK uses different specialized models for different tasks
TASK_MODELS: Final[dict] = {
    # Fast model for simple interactions (llama3.2:3b - 2B params, instant)
    "conversation": "llama3.2:3b",
    "greeting": "llama3.2:3b",
    "general": "llama3.2:3b",
    
    # Reasoning model for complex tasks (qwen3:4b - thinking capability)
    "error_debugging": "qwen3:4b",
    "code_explanation": "qwen3:4b",
    "code_generation": "qwen3:4b",
    "code_review": "qwen3:4b",
    
    # Default fallback
    "default": "llama3.2:3b",
}

# Inference Settings
MAX_LENGTH: Final[int] = 2048
MAX_NEW_TOKENS: Final[int] = 512
TEMPERATURE: Final[float] = 0.7
TOP_P: Final[float] = 0.9
TOP_K: Final[int] = 50
REPETITION_PENALTY: Final[float] = 1.1

# Legacy compatibility
OLLAMA_MODEL: Final[str] = OLLAMA_DEFAULT_MODEL
BASE_MODEL_NAME: Final[str] = OLLAMA_MODEL

# Performance Targets
TARGET_INFERENCE_LATENCY_MS: Final[int] = 100  # <100ms per query
TARGET_VRAM_USAGE_GB: Final[float] = 5.0  # Managed by Ollama

# ==============================================================================
# LORA ADAPTER CONFIGURATION
# ==============================================================================

LORA_RANK: Final[int] = 8  # Low-rank dimension (r)
LORA_ALPHA: Final[int] = 16  # Scaling factor (alpha)
LORA_DROPOUT: Final[float] = 0.1
LORA_TARGET_MODULES: Final[list] = [
    "q_proj",
    "k_proj", 
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]

# Adapter sizes
MAX_ADAPTER_SIZE_MB: Final[float] = 10.0  # ~5-10MB per adapter
MAX_ACTIVE_ADAPTERS: Final[int] = 5  # Concurrent adapters in memory
MAX_TOTAL_ADAPTERS: Final[int] = 50  # Total adapters on disk

# ==============================================================================
# NEUROMORPHIC MEMORY CONFIGURATION
# ==============================================================================

# Memory capacity
MEMORY_MAX_NODES: Final[int] = 100_000  # Maximum memory nodes
MEMORY_RAM_LIMIT_GB: Final[float] = 4.0  # RAM limit for memory network

# Activation settings
ACTIVATION_INITIAL: Final[float] = 1.0  # Initial activation for new memories
ACTIVATION_THRESHOLD: Final[float] = 0.1  # Below this, memory is forgotten
ACTIVATION_DECAY_RATE: Final[float] = 0.05  # Decay per hour
ACTIVATION_SPREAD_FACTOR: Final[float] = 0.3  # How much activation spreads

# Synaptic connections
CONNECTION_SIMILARITY_THRESHOLD: Final[float] = 0.6  # Min similarity to connect
CONNECTION_MAX_WEIGHT: Final[float] = 1.0  # Maximum connection weight
CONNECTION_HEBBIAN_RATE: Final[float] = 0.1  # Hebbian learning rate
CONNECTION_PRUNE_THRESHOLD: Final[float] = 0.05  # Below this, prune connection

# Consolidation
CONSOLIDATION_ACCESS_COUNT: Final[int] = 3  # Accesses to consolidate
CONSOLIDATION_DECAY_REDUCTION: Final[float] = 0.5  # Reduction in decay rate

# Garbage collection
GC_INTERVAL_SECONDS: Final[int] = 300  # Run GC every 5 minutes
GC_BATCH_SIZE: Final[int] = 100  # Nodes to evaluate per GC cycle

# ==============================================================================
# CONTINUOUS LEARNING CONFIGURATION
# ==============================================================================

# Training settings
BATCH_SIZE: Final[int] = 32
LEARNING_RATE: Final[float] = 1e-4
WEIGHT_DECAY: Final[float] = 0.01
WARMUP_STEPS: Final[int] = 100
MAX_GRAD_NORM: Final[float] = 1.0

# Background training
TRAIN_INTERVAL_SECONDS: Final[int] = 60  # Train every 60 seconds
MIN_BATCH_FOR_TRAINING: Final[int] = 32  # Minimum batch size to trigger training
CHECKPOINT_INTERVAL_STEPS: Final[int] = 100  # Save checkpoint every N steps

# Learning targets
TARGET_LOSS_DECREASE_PER_100: Final[float] = 0.01  # 0.5-1.5% per 100 experiences

# ==============================================================================
# TASK DETECTION CONFIGURATION
# ==============================================================================

# Task categories (practical focus)
TASK_CATEGORIES: Final[list] = [
    "error_debugging",      # Analyze and fix errors
    "code_explanation",     # Explain code functionality
    "task_planning",        # Create plans and roadmaps
    "research",             # Find and summarize information
    "health_monitoring",    # Posture, breaks, screen time
    "system_control",       # Desktop automation
    "conversation",         # General chat and follow-ups
    "math_reasoning",       # Calculations and logic
]

# Classification
TASK_DETECTION_THRESHOLD: Final[float] = 0.15  # Minimum confidence for classification
UNKNOWN_TASK_NAME: Final[str] = "unknown"

# ==============================================================================
# HARDWARE CONFIGURATION
# ==============================================================================

# GPU Settings (RTX 4060 / RTX 4090)
GPU_DEVICE: Final[str] = "cuda:0"
VRAM_LIMIT_GB: Final[float] = 8.0  # RTX 4060: 8GB, adjust for your GPU

# System RAM
SYSTEM_RAM_LIMIT_GB: Final[float] = 16.0  # For experience buffer
EXPERIENCE_BUFFER_RAM_GB: Final[float] = 8.0  # Dedicated to buffer

# Mixed Precision
USE_MIXED_PRECISION: Final[bool] = True
AUTOCAST_DTYPE: Final[str] = "bfloat16"  # "float16" or "bfloat16"

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

LOG_LEVEL: Final[str] = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT: Final[str] = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_TO_FILE: Final[bool] = True
LOG_FILE_MAX_BYTES: Final[int] = 10_000_000  # 10MB
LOG_FILE_BACKUP_COUNT: Final[int] = 5

# ==============================================================================
# METRICS & MONITORING
# ==============================================================================

METRICS_ENABLED: Final[bool] = True
METRICS_FLUSH_INTERVAL_SECONDS: Final[int] = 30
TENSORBOARD_ENABLED: Final[bool] = True

# Tracked metrics
TRACKED_METRICS: Final[list] = [
    "inference_latency_ms",
    "training_loss",
    "vram_usage_mb",
    "experiences_count",
    "active_adapters",
    "task_accuracy",
]

# ==============================================================================
# SAFETY & LIMITS
# ==============================================================================

MAX_QUERY_LENGTH: Final[int] = 2048
MAX_RESPONSE_LENGTH: Final[int] = 4096
REQUEST_TIMEOUT_SECONDS: Final[int] = 30
MAX_CONCURRENT_REQUESTS: Final[int] = 4

# Emergency stops
VRAM_CRITICAL_THRESHOLD_GB: Final[float] = 7.5  # Trigger cleanup
CPU_CRITICAL_THRESHOLD_PERCENT: Final[float] = 95.0

# ==============================================================================
# MCP (MODEL CONTEXT PROTOCOL) CONFIGURATION
# ==============================================================================

# MCP Server Settings (expose STARK capabilities)
MCP_SERVER_ENABLED: Final[bool] = True
MCP_SERVER_HOST: Final[str] = "localhost"
MCP_SERVER_PORT: Final[int] = 8080
MCP_SERVER_NAME: Final[str] = "STARK"
MCP_SERVER_VERSION: Final[str] = "0.1.0"

# MCP Client Settings (access external apps)
MCP_CLIENT_ENABLED: Final[bool] = True
MCP_CLIENT_TIMEOUT_SECONDS: Final[int] = 30
MCP_MAX_EXTERNAL_SERVERS: Final[int] = 10

# MCP Tool Categories
MCP_TOOL_CATEGORIES: Final[dict] = {
    "code": ["code_generation", "code_explanation", "code_review", "error_debugging"],
    "file": ["file_read", "file_write", "file_search", "file_analyze"],
    "web": ["web_scrape", "web_search", "web_interact", "web_download"],
    "system": ["system_info", "system_control", "health_monitor", "task_planning"],
    "memory": ["memory_store", "memory_recall", "memory_search", "memory_analyze"],
    "learning": ["adapter_create", "adapter_train", "adapter_list", "adapter_stats"],
}

# MCP Resource Types
MCP_RESOURCE_TYPES: Final[list] = [
    "config",      # System configuration files
    "logs",        # System logs and debug info
    "memory",      # Neuromorphic memory data
    "adapters",    # LoRA adapter files
    "models",      # Model information and stats
    "agents",      # Agent status and capabilities
]

# ==============================================================================
# VERSION & METADATA
# ==============================================================================

STARK_VERSION: Final[str] = "0.1.0"
STARK_CODENAME: Final[str] = "Genesis"
BUILD_DATE: Final[str] = "2025-12-20"

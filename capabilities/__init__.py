# STARK Capabilities Module
from capabilities.error_debugger import (
    ErrorDebugger,
    ErrorAnalysis,
    ErrorType,
    get_error_debugger,
)
try:
    from capabilities.health_monitor import (
        HealthMonitor,
        HealthAlert,
        HealthStats,
        PostureStatus,
        AlertType,
        get_health_monitor,
    )
    _HEALTH_AVAILABLE = True
except ImportError:
    _HEALTH_AVAILABLE = False
from capabilities.code_explanation import (
    CodeExplainer,
    CodeAnalysis,
    PatternType,
    get_code_explainer,
)

__all__ = [
    # Error Debugging
    "ErrorDebugger",
    "ErrorAnalysis",
    "ErrorType",
    "get_error_debugger",
    # Health Monitoring (quarantined — present only if importable)
    *(
        [
            "HealthMonitor",
            "HealthAlert",
            "HealthStats",
            "PostureStatus",
            "AlertType",
            "get_health_monitor",
        ]
        if _HEALTH_AVAILABLE
        else []
    ),
    # Code Explanation
    "CodeExplainer",
    "CodeAnalysis",
    "PatternType",
    "get_code_explainer",
]

"""Stub: re-exports types from the external mcp package."""
import os as _os
import sys as _sys


def _import_external_types():
    _project_root = _os.path.dirname(
        _os.path.dirname(_os.path.abspath(__file__))
    )
    _orig_path = _sys.path.copy()
    _sys.path = [p for p in _sys.path if _os.path.abspath(p) != _project_root]

    _stashed = {k: v for k, v in _sys.modules.items() if k == "mcp" or k.startswith("mcp.")}
    for _k in _stashed:
        del _sys.modules[_k]

    try:
        from mcp.types import TextContent  # noqa: F401
        return TextContent
    finally:
        _sys.path = _orig_path
        for _k, _v in _stashed.items():
            _sys.modules[_k] = _v


TextContent = _import_external_types()

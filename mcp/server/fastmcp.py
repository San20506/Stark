"""Stub: re-exports FastMCP from the external mcp package.

The project mcp/ directory shadows the installed mcp package. To import
from the real package we must temporarily remove both the project root from
sys.path AND the project mcp.* entries from sys.modules, so Python's import
system resolves 'mcp' to site-packages instead of this directory.
"""
import os as _os
import sys as _sys


def _import_external_fastmcp():
    _project_root = _os.path.dirname(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    )
    _orig_path = _sys.path.copy()
    _sys.path = [p for p in _sys.path if _os.path.abspath(p) != _project_root]

    _stashed = {k: v for k, v in _sys.modules.items() if k == "mcp" or k.startswith("mcp.")}
    for _k in _stashed:
        del _sys.modules[_k]

    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
        return FastMCP
    finally:
        _sys.path = _orig_path
        for _k, _v in _stashed.items():
            _sys.modules[_k] = _v


FastMCP = _import_external_fastmcp()

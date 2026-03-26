# Stub module: re-exports FastMCP from the external mcp package.
# The project mcp/ directory shadows the external mcp package, so we temporarily
# remove the project mcp entries from sys.modules to let the external package load.
import sys as _sys

_proj_modules = {k: v for k, v in _sys.modules.items() if k == "mcp" or k.startswith("mcp.")}
for _k in _proj_modules:
    _sys.modules.pop(_k, None)

try:
    from mcp.server.fastmcp import FastMCP  # noqa: F401  (external mcp)
finally:
    # Restore project mcp entries
    for _k, _v in _proj_modules.items():
        _sys.modules.setdefault(_k, _v)

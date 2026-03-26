# Stub module: re-exports ClientSession from the external mcp package.
import sys as _sys

_proj_modules = {k: v for k, v in _sys.modules.items() if k == "mcp" or k.startswith("mcp.")}
for _k in _proj_modules:
    _sys.modules.pop(_k, None)

try:
    from mcp.client.session import ClientSession  # noqa: F401  (external mcp)
finally:
    for _k, _v in _proj_modules.items():
        _sys.modules.setdefault(_k, _v)

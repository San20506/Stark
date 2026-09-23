# Change: Rebuild Dev Env (S0)

## Why
System Python 3.14.7 has no `pip`, `yaml`, `pydantic`, `sklearn`, `pytest`, or
`sentence_transformers`. Nothing imports, nothing tests. All other specs block
on this.

## What Changes
- Pin `.python-version` to 3.11 (torch compat) and upper-bound `requirements.txt`
- Document `python -m venv .venv && pip install` flow for the pure-Python slice
- `README` install block only; no `*.py` edits

## Impact
- Affected specs: refactor-s0-env (new)
- Affected code: none (`*.py` untouched)
- Unblocks: S1–S8

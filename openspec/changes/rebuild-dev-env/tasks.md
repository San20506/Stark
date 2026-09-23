## 1. Pin Environment
- [x] 1.1 Add `.python-version` with `3.11`
- [x] 1.2 Add upper bounds / lockfile for `pyyaml`, `pydantic>=2`, `scikit-learn`, `pytest`, `sentence-transformers`, `requests`, `numpy`
- [x] 1.3 Document venv flow in `README` install block

## 2. Verify
- [ ] 2.1 `python -c "from core.config import get_config; print('config OK')"`
- [ ] 2.2 `python -m pytest --collect-only -q` runs

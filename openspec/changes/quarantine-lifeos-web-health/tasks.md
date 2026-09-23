## 1. Delete Surfaces
- [x] 1.1 Delete `modules/life_os/`, `web_server.py`, `web/`, `capabilities/health_monitor.py`
- [x] 1.2 Remove `core/main.py:491-528` orchestrator branch (keep `TASK_MODELS` routing)

## 2. Verify
- [x] 2.1 `stark_cli.py` is the single entry point
- [x] 2.2 No Notion/GCal/Flask import from core path

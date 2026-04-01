"""
Life OS Web Routes
==================
Flask Blueprint exposing a dashboard panel and trigger endpoints.

Mount in web_server.py:
    from modules.life_os.web_routes import life_os_bp
    app.register_blueprint(life_os_bp, url_prefix="/api/life_os")

Endpoints:
    GET  /api/life_os/dashboard           — last briefing, habits, goals
    POST /api/life_os/briefing/morning    — trigger morning briefing
    POST /api/life_os/briefing/evening    — submit intake + run evening review
    POST /api/life_os/briefing/weekly     — trigger weekly audit
    GET  /api/life_os/scheduler/status    — APScheduler job info
"""
import logging
from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request

from core.constants import LIFE_OS_LOG_DIR

logger = logging.getLogger(__name__)

life_os_bp = Blueprint("life_os", __name__)


# ==============================================================================
# Dashboard
# ==============================================================================


@life_os_bp.route("/dashboard", methods=["GET"])
def dashboard() -> Any:
    """Return dashboard snapshot: last briefing, habit grid, goal/project status."""
    from modules.life_os.context_manager import get_context_manager

    try:
        cm = get_context_manager()
        context = cm.read_all()

        today = date.today().isoformat()
        log_path = LIFE_OS_LOG_DIR / f"{today}.md"
        last_briefing: str | None = (
            log_path.read_text(encoding="utf-8") if log_path.exists() else None
        )

        return jsonify(
            {
                "date": today,
                "last_briefing": last_briefing,
                "habits": context.get("habits", {}).get("body", ""),
                "goals": context.get("goals", {}).get("body", ""),
                "projects": context.get("projects", {}).get("body", ""),
            }
        )
    except Exception as exc:
        logger.error("Life OS dashboard error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ==============================================================================
# Triggers
# ==============================================================================


@life_os_bp.route("/briefing/morning", methods=["POST"])
def trigger_morning() -> Any:
    """Trigger morning briefing on demand."""
    from modules.life_os.voice_hooks import handle_morning

    try:
        briefing = handle_morning(query="morning briefing")
        return jsonify({"briefing": briefing})
    except Exception as exc:
        logger.error("Morning trigger error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@life_os_bp.route("/briefing/evening", methods=["POST"])
def trigger_evening() -> Any:
    """Submit end-of-day intake and run evening review.

    Request body: ``{"intake": "Finished STARK context_manager, blocked on X..."}``
    """
    from modules.life_os.voice_hooks import handle_evening

    try:
        data = request.get_json(silent=True) or {}
        intake = data.get("intake", "").strip()
        if not intake:
            return jsonify({"error": "'intake' field is required"}), 400
        reflection = handle_evening(query=intake)
        return jsonify({"reflection": reflection})
    except Exception as exc:
        logger.error("Evening trigger error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@life_os_bp.route("/briefing/weekly", methods=["POST"])
def trigger_weekly() -> Any:
    """Trigger weekly review on demand."""
    from modules.life_os.voice_hooks import handle_weekly

    try:
        result = handle_weekly(query="weekly review")
        return jsonify({"result": result})
    except Exception as exc:
        logger.error("Weekly trigger error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ==============================================================================
# Scheduler info
# ==============================================================================


@life_os_bp.route("/scheduler/status", methods=["GET"])
def scheduler_status() -> Any:
    """Return life_os scheduler job info."""
    from modules.life_os.scheduler import get_scheduler

    sched = get_scheduler()
    if sched is None or not sched.running:
        return jsonify({"running": False, "jobs": []})

    jobs = [
        {
            "id": job.id,
            "next_run": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
        }
        for job in sched.get_jobs()
    ]
    return jsonify({"running": True, "jobs": jobs})

from datetime import datetime, timezone
import threading

from app.services.accountability_service import verify_all_due_predictions

_scheduler_state = {
    "running": False,
    "interval_seconds": 60,
    "last_run_at": None,
    "last_checked": 0,
    "last_verified": 0,
    "total_runs": 0,
    "last_error": None,
}
_stop_event = threading.Event()
_thread: threading.Thread | None = None


def get_scheduler_status() -> dict:
    return dict(_scheduler_state)


def start_verification_scheduler(app) -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return

    interval = max(10, int(app.config.get("SCHEDULER_INTERVAL_SECONDS", 60)))
    _scheduler_state["interval_seconds"] = interval
    _scheduler_state["running"] = True
    _stop_event.clear()

    def _worker():
        # Brief initial delay to allow app startup to finish cleanly
        if _stop_event.wait(3):
            return
        while not _stop_event.is_set():
            try:
                with app.app_context():
                    summary = verify_all_due_predictions()
                    _scheduler_state["last_run_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                    _scheduler_state["last_checked"] = summary["checked_count"]
                    _scheduler_state["last_verified"] = summary["verified_count"]
                    _scheduler_state["total_runs"] += 1
                    _scheduler_state["last_error"] = None
            except Exception as exc:
                _scheduler_state["last_error"] = str(exc)
            _stop_event.wait(interval)
        _scheduler_state["running"] = False

    _thread = threading.Thread(target=_worker, name="PredictionVerificationScheduler", daemon=True)
    _thread.start()


def stop_verification_scheduler() -> None:
    _stop_event.set()
    _scheduler_state["running"] = False


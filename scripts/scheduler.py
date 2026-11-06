"""
SPECTRE Autonomous Background Scheduler
========================================
A lightweight cron-style automation engine using threading.Timer.
Runs recurring tasks (dependency audits, health checks, git status)
in the background without blocking the main dashboard server.

Usage:
    from scripts.scheduler import SchedulerEngine, Automation
    engine = SchedulerEngine()
    engine.add(Automation("health_check", "every 5 minutes", lambda: ...))
    engine.start()
"""

import threading
import time
import json
import uuid
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("spectre.scheduler")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

INTERVAL_MAP = {
    "every minute":   60,
    "every 5 minutes": 300,
    "every 15 minutes": 900,
    "every 30 minutes": 1800,
    "every hour":     3600,
    "every 6 hours":  21600,
    "every day":      86400,
}


@dataclass
class AutomationResult:
    automation_id: str
    name: str
    started_at: float
    finished_at: float
    exit_code: int
    output: str
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "automation_id": self.automation_id,
            "name": self.name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration": round(self.finished_at - self.started_at, 2),
            "exit_code": self.exit_code,
            "output": self.output[:2000],
            "error": self.error[:500],
        }


@dataclass
class Automation:
    name: str
    schedule: str                      # e.g. "every 5 minutes"
    command: Optional[str] = None      # shell command to run
    fn: Optional[Callable] = None      # or a Python callable
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    last_run: Optional[float] = None
    last_result: Optional[dict] = None
    run_count: int = 0
    description: str = ""

    @property
    def interval_seconds(self) -> int:
        return INTERVAL_MAP.get(self.schedule.lower(), 3600)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "schedule": self.schedule,
            "interval_seconds": self.interval_seconds,
            "command": self.command,
            "enabled": self.enabled,
            "description": self.description,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "last_result": self.last_result,
        }

    def run(self) -> AutomationResult:
        t0 = time.time()
        self.last_run = t0
        self.run_count += 1
        try:
            if self.fn:
                raw = self.fn()
                output = str(raw) if raw is not None else "ok"
                exit_code = 0
            elif self.command:
                proc = subprocess.run(
                    self.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = (proc.stdout or "").strip()
                exit_code = proc.returncode
                if proc.stderr:
                    output += ("\n" + proc.stderr.strip()) if output else proc.stderr.strip()
            else:
                output = "No command or function defined."
                exit_code = 1
        except subprocess.TimeoutExpired:
            output = "Automation timed out after 120s."
            exit_code = 124
        except Exception as exc:
            output = f"Automation error: {type(exc).__name__}: {exc}"
            exit_code = 1

        result = AutomationResult(
            automation_id=self.id,
            name=self.name,
            started_at=t0,
            finished_at=time.time(),
            exit_code=exit_code,
            output=output,
        )
        self.last_result = result.to_dict()
        return result


# ---------------------------------------------------------------------------
# Scheduler engine
# ---------------------------------------------------------------------------

class SchedulerEngine:
    """Thread-safe background scheduler. Uses threading.Timer for each job."""

    def __init__(self):
        self._automations: dict[str, Automation] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._running = False
        self._results: list[dict] = []          # rolling log of last 100 runs
        self._results_max = 100

    # -- Registration --------------------------------------------------------

    def add(self, automation: Automation) -> str:
        with self._lock:
            self._automations[automation.id] = automation
        if self._running and automation.enabled:
            self._schedule_next(automation)
        return automation.id

    def remove(self, automation_id: str) -> bool:
        with self._lock:
            if automation_id not in self._automations:
                return False
            del self._automations[automation_id]
        self._cancel_timer(automation_id)
        return True

    def enable(self, automation_id: str) -> bool:
        with self._lock:
            auto = self._automations.get(automation_id)
            if not auto:
                return False
            auto.enabled = True
        if self._running:
            self._schedule_next(auto)
        return True

    def disable(self, automation_id: str) -> bool:
        with self._lock:
            auto = self._automations.get(automation_id)
            if not auto:
                return False
            auto.enabled = False
        self._cancel_timer(automation_id)
        return True

    # -- Lifecycle -----------------------------------------------------------

    def start(self):
        self._running = True
        with self._lock:
            autos = list(self._automations.values())
        for auto in autos:
            if auto.enabled:
                self._schedule_next(auto, delay=10)  # 10s startup grace
        logger.info("SchedulerEngine started with %d automations.", len(autos))

    def stop(self):
        self._running = False
        with self._lock:
            ids = list(self._timers.keys())
        for aid in ids:
            self._cancel_timer(aid)
        logger.info("SchedulerEngine stopped.")

    # -- Introspection -------------------------------------------------------

    def list_automations(self) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self._automations.values()]

    def get_results(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return list(reversed(self._results[-limit:]))

    def get_automation(self, automation_id: str) -> Optional[dict]:
        with self._lock:
            auto = self._automations.get(automation_id)
            return auto.to_dict() if auto else None

    def run_now(self, automation_id: str) -> Optional[dict]:
        with self._lock:
            auto = self._automations.get(automation_id)
        if not auto:
            return None
        result = auto.run()
        with self._lock:
            self._results.append(result.to_dict())
            if len(self._results) > self._results_max:
                self._results = self._results[-self._results_max:]
        return result.to_dict()

    # -- Internal ------------------------------------------------------------

    def _schedule_next(self, auto: Automation, delay: int = None):
        self._cancel_timer(auto.id)
        if not self._running or not auto.enabled:
            return
        wait = delay if delay is not None else auto.interval_seconds

        def _fire():
            result = auto.run()
            logger.debug("Automation '%s' finished: exit=%d dur=%.2fs",
                         auto.name, result.exit_code, result.finished_at - result.started_at)
            with self._lock:
                self._results.append(result.to_dict())
                if len(self._results) > self._results_max:
                    self._results = self._results[-self._results_max:]
            # Schedule next run
            self._schedule_next(auto)

        timer = threading.Timer(wait, _fire)
        timer.daemon = True
        timer.start()
        with self._lock:
            self._timers[auto.id] = timer

    def _cancel_timer(self, automation_id: str):
        with self._lock:
            timer = self._timers.pop(automation_id, None)
        if timer:
            timer.cancel()


# ---------------------------------------------------------------------------
# Built-in automations factory
# ---------------------------------------------------------------------------

def make_default_automations(workspace_path: str = ".") -> list[Automation]:
    """Returns the default set of SPECTRE background automations."""
    return [
        Automation(
            name="Dependency Security Audit",
            schedule="every hour",
            command=f'cd "{workspace_path}" && python -m pip_audit --format json 2>&1 | head -100 || echo "pip-audit not installed; run: pip install pip-audit"',
            description="Scans Python dependencies for known CVEs via pip-audit.",
        ),
        Automation(
            name="Git Status Check",
            schedule="every 15 minutes",
            command=f'git -C "{workspace_path}" status --short && git -C "{workspace_path}" log --oneline -3',
            description="Reports uncommitted changes and recent commits.",
        ),
        Automation(
            name="SPECTRE Health Check",
            schedule="every 5 minutes",
            command='python -c "import requests; r=requests.get(\'http://127.0.0.1:5050/api/status\', timeout=5); print(r.json())" 2>&1 || echo "SPECTRE server offline"',
            description="Pings the SPECTRE dashboard health endpoint and logs status.",
        ),
        Automation(
            name="Open Port Scan",
            schedule="every 30 minutes",
            command='python -c "import socket; ports=[3000,5173,8000,8080,5000,4200]; open_=[p for p in ports if socket.socket().connect_ex((\'127.0.0.1\',p))==0]; print(\'Open ports:\', open_ or \'none\')"',
            description="Scans common dev-server ports for open services.",
        ),
    ]


# ---------------------------------------------------------------------------
# Global singleton (imported by spectre_dashboard.py)
# ---------------------------------------------------------------------------

_scheduler: Optional[SchedulerEngine] = None


def get_scheduler() -> SchedulerEngine:
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerEngine()
    return _scheduler


def init_scheduler(workspace_path: str = ".") -> SchedulerEngine:
    """Initialize scheduler with default automations and start it."""
    engine = get_scheduler()
    if not engine._running:
        for auto in make_default_automations(workspace_path):
            engine.add(auto)
        engine.start()
        logger.info("SPECTRE Scheduler initialized with %d default automations.", len(engine._automations))
    return engine


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    engine = init_scheduler(".")
    print("Scheduler running. Automations:")
    for a in engine.list_automations():
        print(f"  [{a['id']}] {a['name']} — {a['schedule']}")
    print("\nPress Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        engine.stop()
        print("Stopped.")


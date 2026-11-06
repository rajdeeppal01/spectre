"""
Unit tests for SPECTRE Autonomous Background Scheduler (scripts/scheduler.py).
"""

import time
import pytest
from scripts.scheduler import SchedulerEngine, Automation, AutomationResult, make_default_automations


def test_automation_creation():
    auto = Automation(
        name="Test Echo",
        schedule="every minute",
        command="echo test_automation_ok",
        description="Test automation",
    )
    assert auto.name == "Test Echo"
    assert auto.interval_seconds == 60
    assert auto.enabled is True
    assert auto.run_count == 0


def test_automation_execution():
    auto = Automation(
        name="Test Py Run",
        schedule="every 5 minutes",
        fn=lambda: "custom_function_output",
    )
    res = auto.run()
    assert isinstance(res, AutomationResult)
    assert res.exit_code == 0
    assert "custom_function_output" in res.output
    assert auto.run_count == 1
    assert auto.last_result is not None


def test_scheduler_engine_lifecycle():
    engine = SchedulerEngine()
    auto = Automation(
        name="Quick Ping",
        schedule="every minute",
        fn=lambda: "ping",
    )
    aid = engine.add(auto)
    assert aid == auto.id
    assert len(engine.list_automations()) == 1

    # Run manually
    res = engine.run_now(aid)
    assert res is not None
    assert res["exit_code"] == 0
    assert len(engine.get_results()) >= 1

    # Disable / Enable
    assert engine.disable(aid) is True
    assert engine.get_automation(aid)["enabled"] is False

    assert engine.enable(aid) is True
    assert engine.get_automation(aid)["enabled"] is True

    # Remove
    assert engine.remove(aid) is True
    assert len(engine.list_automations()) == 0


def test_default_automations():
    autos = make_default_automations(".")
    assert len(autos) >= 4
    names = [a.name for a in autos]
    assert "Dependency Security Audit" in names
    assert "Git Status Check" in names
    assert "SPECTRE Health Check" in names
    assert "Open Port Scan" in names

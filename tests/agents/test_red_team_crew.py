"""
Tests for agents/red_team_crew.py — create_red_team_crew factory.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

from unittest.mock import MagicMock

import pytest

crewai = pytest.importorskip("crewai", reason="crewai not installed; skipping Red Team Crew tests")

from agents.red_team_crew import create_red_team_crew  # noqa: E402


# ── Module-level Ollama mock ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_ollama_llm(monkeypatch):
    """Prevent Ollama constructors from attempting a real connection."""
    monkeypatch.setattr("agents.red_team_crew.Ollama", MagicMock(return_value=MagicMock()))


# ── Shared crew fixture ───────────────────────────────────────────────────────

@pytest.fixture
def crew():
    return create_red_team_crew("target.example.com")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCreateRedTeamCrew:
    """Unit tests for the create_red_team_crew factory function."""

    def test_crew_has_four_agents(self, crew):
        """Crew must contain exactly four specialised agents.

        Validates: Requirement 8.1
        """
        assert len(crew.agents) == 4

    def test_agent_roles(self, crew):
        """Each agent must carry the expected role string, in order.

        Validates: Requirement 8.2
        """
        expected_role_substrings = [
            "Reconnaissance Specialist",
            "Exploit Developer",
            "Security Code Reviewer",
            "Lead Penetration Tester",
        ]
        for agent, expected in zip(crew.agents, expected_role_substrings):
            assert expected in agent.role, (
                f"Expected role containing '{expected}', got '{agent.role}'"
            )

    def test_all_agents_no_delegation(self, crew):
        """No agent should be allowed to delegate tasks to another agent.

        Validates: Requirement 8.3
        """
        for agent in crew.agents:
            assert agent.allow_delegation is False, (
                f"Agent '{agent.role}' has allow_delegation=True"
            )

    def test_crew_has_four_tasks(self, crew):
        """Crew must contain exactly four tasks (one per pipeline stage).

        Validates: Requirement 8.4
        """
        assert len(crew.tasks) == 4

    def test_task_agent_assignment(self, crew):
        """Each task must be assigned to the correct specialist agent.

        Validates: Requirement 8.5
        """
        assert "Reconnaissance Specialist" in crew.tasks[0].agent.role
        assert "Exploit Developer" in crew.tasks[1].agent.role
        assert "Security Code Reviewer" in crew.tasks[2].agent.role
        assert "Lead Penetration Tester" in crew.tasks[3].agent.role

    def test_recon_task_contains_target(self, crew):
        """The reconnaissance task description must embed the target hostname.

        Validates: Requirement 8.1
        """
        assert "target.example.com" in crew.tasks[0].description

"""
Tests for scripts/quantum_sim.py — Task 6.1: TestStatevectorSimGates

Validates Requirements: 5.1, 5.2, 5.3
"""

import math
import sys
import os

import pytest

# Ensure the project root is on the path so the scripts package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.quantum_sim import StatevectorSim


class TestStatevectorSimGates:
    """Unit tests for StatevectorSim gate operations.

    Validates: Requirements 5.1, 5.2, 5.3
    """

    def test_hadamard_on_zero_state(self):
        """Applying H to |0⟩ produces equal superposition: both amplitudes have magnitude 1/sqrt(2).

        Validates: Requirements 5.1
        """
        sim = StatevectorSim(1)
        sim.apply_hadamard(0)

        expected = 1.0 / math.sqrt(2.0)

        assert abs(sim.state[0]) == pytest.approx(expected, abs=1e-9), (
            f"Amplitude |0⟩ magnitude should be 1/sqrt(2) ≈ {expected:.10f}, got {abs(sim.state[0]):.10f}"
        )
        assert abs(sim.state[1]) == pytest.approx(expected, abs=1e-9), (
            f"Amplitude |1⟩ magnitude should be 1/sqrt(2) ≈ {expected:.10f}, got {abs(sim.state[1]):.10f}"
        )

    def test_hadamard_self_inverse(self):
        """Applying H twice returns the statevector to |0⟩: amplitude[0] ≈ 1.0, amplitude[1] ≈ 0.0.

        H is unitary and self-inverse (H² = I), so H|0⟩ followed by H yields |0⟩ again.

        Validates: Requirements 5.2
        """
        sim = StatevectorSim(1)
        sim.apply_hadamard(0)
        sim.apply_hadamard(0)

        assert abs(sim.state[0]) == pytest.approx(1.0, abs=1e-9), (
            f"|0⟩ amplitude magnitude should be 1.0 after H², got {abs(sim.state[0]):.10f}"
        )
        assert abs(sim.state[1]) == pytest.approx(0.0, abs=1e-9), (
            f"|1⟩ amplitude magnitude should be 0.0 after H², got {abs(sim.state[1]):.10f}"
        )

    def test_bell_state_via_hadamard_cnot(self):
        """H on qubit 0 then CNOT(0→1) produces Bell state |Φ+⟩ = (|00⟩ + |11⟩) / sqrt(2).

        The |01⟩ and |10⟩ components must have zero amplitude (magnitude < 1e-9).
        Only |00⟩ (index 0) and |11⟩ (index 3) should carry non-zero amplitudes.

        Statevector index layout for 2 qubits (qubit 1 is MSB, qubit 0 is LSB):
          index 0 → |00⟩, index 1 → |01⟩, index 2 → |10⟩, index 3 → |11⟩

        Validates: Requirements 5.3
        """
        sim = StatevectorSim(2)
        sim.apply_hadamard(0)
        sim.apply_cnot(control=0, target=1)

        # |01⟩ and |10⟩ must be zero in a valid Bell state
        assert abs(sim.state[1]) < 1e-9, (
            f"|01⟩ amplitude should be ~0 in Bell state, got {abs(sim.state[1]):.2e}"
        )
        assert abs(sim.state[2]) < 1e-9, (
            f"|10⟩ amplitude should be ~0 in Bell state, got {abs(sim.state[2]):.2e}"
        )

        # |00⟩ and |11⟩ must each carry magnitude 1/sqrt(2)
        expected = 1.0 / math.sqrt(2.0)
        assert abs(sim.state[0]) == pytest.approx(expected, abs=1e-9), (
            f"|00⟩ amplitude magnitude should be 1/sqrt(2) ≈ {expected:.10f}, got {abs(sim.state[0]):.10f}"
        )
        assert abs(sim.state[3]) == pytest.approx(expected, abs=1e-9), (
            f"|11⟩ amplitude magnitude should be 1/sqrt(2) ≈ {expected:.10f}, got {abs(sim.state[3]):.10f}"
        )

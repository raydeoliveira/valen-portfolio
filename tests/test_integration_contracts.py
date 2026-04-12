"""Integration contract tests — verify component interfaces match consumer access patterns.

The #1 bug pattern in VALEN's deep audit was interface mismatch: producers emit data with
one schema but consumers access different attribute names, causing silent failures caught
by bare `except Exception: pass` handlers.

These tests lock down the contracts between:
    Recalibrator -> Orchestrator
    Governor     -> Orchestrator
    SOR Health   -> Orchestrator
    SleeveState  (self-consistency)

Why this matters: The recalibrator once produced `change_pct` but the orchestrator consumed
`pct_change`. The silent mismatch (caught by bare except) meant the entire recalibration
pipeline was a no-op for an entire development session. Rule 44 was added to prevent this.

NOTE: This is a curated excerpt. The full test suite has 150+ contract assertions across
all component boundaries. Signal parameters and scoring formulas are not included.
"""

from __future__ import annotations

import dataclasses


# ---------------------------------------------------------------------------
# 1. Recalibrator -> Orchestrator contract
# ---------------------------------------------------------------------------


class TestRecalibratorOrchestratorContract:
    """Verify attribute names the orchestrator uses on recalibrator output."""

    def test_leverage_change_event_has_pct_change(self) -> None:
        """Orchestrator accesses result.events[0].pct_change — NOT change_pct."""
        from src.services.leverage_recalibrator import LeverageChangeEvent

        fields = {f.name for f in dataclasses.fields(LeverageChangeEvent)}
        assert "pct_change" in fields, (
            "LeverageChangeEvent must have 'pct_change', not 'change_pct'"
        )
        assert "change_pct" not in fields, (
            "Legacy 'change_pct' found — orchestrator expects 'pct_change'"
        )

    def test_recalibration_result_has_sleeves_dict(self) -> None:
        """Orchestrator accesses result.sleeves — NOT result.new_weights."""
        from src.services.leverage_recalibrator import RecalibrationResult

        fields = {f.name for f in dataclasses.fields(RecalibrationResult)}
        assert "sleeves" in fields, (
            "RecalibrationResult must have 'sleeves' dict"
        )
        assert "new_weights" not in fields, (
            "Legacy 'new_weights' found — orchestrator expects 'sleeves'"
        )

    def test_recalibration_result_has_events_list(self) -> None:
        from src.services.leverage_recalibrator import RecalibrationResult

        fields = {f.name for f in dataclasses.fields(RecalibrationResult)}
        assert "events" in fields
        assert "alerts" in fields
        assert "any_changes" in fields

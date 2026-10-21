"""FLEX-eligibility guard: only RB/WR/TE may be assigned to a FLEX slot.

Covers both places that assign a FLEX slot: a user manually editing a roster
(app.routers.teams._validate_slot) and the AI lineup builder's own output
(app.services.lineup._validate_flex_eligibility) - the model isn't
guaranteed to respect the rule just because the system prompt states it."""

import pytest
from fastapi import HTTPException

from app.routers.teams import _validate_slot
from app.services.lineup import LineupGenerationError, _validate_flex_eligibility


@pytest.mark.parametrize("position", ["RB", "WR", "TE"])
def test_flex_eligible_positions_are_allowed(position):
    _validate_slot(position, "FLEX")  # should not raise


@pytest.mark.parametrize("position", ["QB", "K", "DST", None])
def test_flex_ineligible_positions_are_rejected(position):
    with pytest.raises(HTTPException) as exc_info:
        _validate_slot(position, "FLEX")
    assert exc_info.value.status_code == 400


def test_non_flex_slot_is_never_validated_against_position():
    # Any position is fine for a slot that matches it directly (e.g. QB in
    # the QB slot) - the guard only applies to FLEX.
    _validate_slot("QB", "QB")
    _validate_slot(None, "BN")


@pytest.mark.parametrize("position", ["RB", "WR", "TE"])
def test_ai_lineup_builder_allows_flex_eligible_positions(position):
    _validate_flex_eligibility("FLEX", position, "Some Player")  # should not raise


@pytest.mark.parametrize("position", ["QB", "K", "DST", None])
def test_ai_lineup_builder_rejects_flex_ineligible_positions(position):
    # Regression test: the model would occasionally put a QB in FLEX with
    # nothing catching it, since recommend_lineup() never validated its own
    # tool-call output against FLEX_ELIGIBLE_POSITIONS.
    with pytest.raises(LineupGenerationError):
        _validate_flex_eligibility("FLEX", position, "Some Player")


def test_ai_lineup_builder_non_flex_slot_is_never_validated_against_position():
    _validate_flex_eligibility("QB", "QB", "Some Player")
    _validate_flex_eligibility("BN", None, "Some Player")

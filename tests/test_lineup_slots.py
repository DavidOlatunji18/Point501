"""FLEX-eligibility guard: only RB/WR/TE may be assigned to a FLEX slot."""

import pytest
from fastapi import HTTPException

from app.routers.teams import _validate_slot


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

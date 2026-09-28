"""Regression tests for app/services/roster_import.py, covering three real
bugs found earlier while building roster paste-import: multiple players
squished onto one line, same-position players back-to-back merging into
one entry, and BE/BN bench markers being silently auto-promoted into an
open FLEX slot."""

from app.services.roster_import import (
    ParsedRosterEntry,
    assign_starting_slots,
    parse_roster_text,
)


def test_single_player_line():
    entries = parse_roster_text("QB Patrick Mahomes")
    assert len(entries) == 1
    assert entries[0].name == "Patrick Mahomes"
    assert entries[0].position == "QB"


def test_multiple_players_on_one_line_are_split():
    entries = parse_roster_text("QB L. Jackson RB D. Swift WR A. Brown")
    assert [e.position for e in entries] == ["QB", "RB", "WR"]
    assert [e.name for e in entries] == ["L. Jackson", "D. Swift", "A. Brown"]


def test_same_position_players_back_to_back_are_not_merged():
    entries = parse_roster_text("WR A. Brown WR CeeDee Lamb")
    assert len(entries) == 2
    assert entries[0].name == "A. Brown"
    assert entries[1].name == "CeeDee Lamb"


def test_redundant_repeated_marker_is_not_a_new_player():
    # "WR, MIN" trailing after the name is just more info about the same
    # player, not a second entry.
    entries = parse_roster_text("WR Justin Jefferson, WR, MIN")
    assert len(entries) == 1
    assert entries[0].name == "Justin Jefferson"
    assert entries[0].nfl_team == "MIN"


def test_bench_marker_is_recognized_and_not_treated_as_a_slot():
    entries = parse_roster_text("K A. Borregales BE P. Mahomes BE J. Dart")
    assert len(entries) == 3
    assert entries[0].bench is False
    assert entries[1].bench is True
    assert entries[1].name == "P. Mahomes"
    assert entries[2].bench is True
    # Bench markers never become a starting slot label.
    assert all(e.slot != "BE" and e.slot != "BN" for e in entries)


def test_bare_defense_line():
    entries = parse_roster_text("SF DST")
    assert len(entries) == 1
    assert entries[0].name == "SF"
    assert entries[0].position == "DST"


def test_def_alias_normalized_to_dst():
    entries = parse_roster_text("DEF SF")
    assert entries[0].position == "DST"


def test_assign_starting_slots_matches_exact_position():
    entries = [ParsedRosterEntry(name="Patrick Mahomes", position="QB")]
    assign_starting_slots(entries, open_slots=["QB", "RB", "FLEX"])
    assert entries[0].slot == "QB"


def test_assign_starting_slots_fills_flex_from_leftover_eligible_position():
    entries = [
        ParsedRosterEntry(name="Christian McCaffrey", position="RB"),
        ParsedRosterEntry(name="Bijan Robinson", position="RB"),
    ]
    assign_starting_slots(entries, open_slots=["RB", "FLEX"])
    assert entries[0].slot == "RB"
    assert entries[1].slot == "FLEX"


def test_assign_starting_slots_never_promotes_a_benched_entry_into_flex():
    # This is the exact bug that was fixed: a player explicitly marked BE in
    # the pasted text must stay benched, even if their position would
    # otherwise fit an open FLEX slot.
    entries = [ParsedRosterEntry(name="Bijan Robinson", position="RB", bench=True)]
    assign_starting_slots(entries, open_slots=["FLEX"])
    assert entries[0].slot is None


def test_assign_starting_slots_leaves_overflow_entries_on_bench():
    entries = [
        ParsedRosterEntry(name="Patrick Mahomes", position="QB"),
        ParsedRosterEntry(name="Jalen Hurts", position="QB"),
    ]
    assign_starting_slots(entries, open_slots=["QB"])
    assert entries[0].slot == "QB"
    assert entries[1].slot is None

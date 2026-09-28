import pytest
from ui_helpers import pick_invite_code


def test_pick_invite_code_typed_wins_over_pending():
    assert pick_invite_code("PENDING", "TYPED") == "TYPED"


def test_pick_invite_code_falls_back_to_pending():
    assert pick_invite_code("PENDING", "") == "PENDING"
    assert pick_invite_code("PENDING", None) == "PENDING"


def test_pick_invite_code_blank_when_neither():
    assert pick_invite_code(None, None) == ""
    assert pick_invite_code("  ", "  ") == ""

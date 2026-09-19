"""
Unit tests for keyboards.py.

The router decides what to do by comparing the text of the pressed button,
so a wrong / duplicated / missing button silently breaks a feature.
These tests lock the layout and check that keyboards, constants and the
graph handler / graph module agree with each other.

Tests never hardcode button texts: they use the constants, so changing a
label in handlers/constants.py will not break them.
"""

import pytest
from telegram import ReplyKeyboardMarkup

import keyboards
from keyboards import (
    MAIN_KEYBOARD,
    HISTORY_KEYBOARD,
    GRAPH_KEYBOARD,
    SETTINGS_KEYBOARD,
    BACK_KEYBOARD,
)
from handlers import constants as c
from graph import TIMELINE_DAYS


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def layout(keyboard):
    """ReplyKeyboardMarkup -> [[text, text], [text], ...]"""
    return [
        [getattr(button, "text", button) for button in row]
        for row in keyboard.keyboard
    ]


def flat(keyboard):
    return [text for row in layout(keyboard) for text in row]


ALL_KEYBOARDS = {
    "MAIN": MAIN_KEYBOARD,
    "HISTORY": HISTORY_KEYBOARD,
    "GRAPH": GRAPH_KEYBOARD,
    "SETTINGS": SETTINGS_KEYBOARD,
    "BACK": BACK_KEYBOARD,
}

# every keyboard except the main one is a sub-menu and needs a way back
SUB_KEYBOARDS = {
    name: kb for name, kb in ALL_KEYBOARDS.items() if name != "MAIN"
}

ALL_BUTTONS = {
    "GRAPH_BUTTON": c.GRAPH_BUTTON,
    "TODAY_RECORD_BUTTON": c.TODAY_RECORD_BUTTON,
    "NEW_RECORD_BUTTON": c.NEW_RECORD_BUTTON,
    "STATISTICS_BUTTON": c.STATISTICS_BUTTON,
    "HISTORY_BUTTON": c.HISTORY_BUTTON,
    "SETTINGS_BUTTON": c.SETTINGS_BUTTON,
    "BACK_BUTTON": c.BACK_BUTTON,
    "EXPORT_BUTTON": c.EXPORT_BUTTON,
    "WEEKLY_BUTTON": c.WEEKLY_BUTTON,
    "MONTHLY_BUTTON": c.MONTHLY_BUTTON,
    "THREE_MONTHS_BUTTON": c.THREE_MONTHS_BUTTON,
    "SIX_MONTHS_BUTTON": c.SIX_MONTHS_BUTTON,
    "ONE_YEAR_BUTTON": c.ONE_YEAR_BUTTON,
    "DARK_THEME_BUTTON": c.DARK_THEME_BUTTON,
    "LIGHT_THEME_BUTTON": c.LIGHT_THEME_BUTTON,
}

TIMELINE_BUTTONS = [
    c.WEEKLY_BUTTON,
    c.MONTHLY_BUTTON,
    c.THREE_MONTHS_BUTTON,
    c.SIX_MONTHS_BUTTON,
    c.ONE_YEAR_BUTTON,
]


# ------------------------------------------------------------------
# General rules for every keyboard
# ------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_KEYBOARDS)
def test_is_reply_keyboard_markup(name):
    assert isinstance(ALL_KEYBOARDS[name], ReplyKeyboardMarkup)


@pytest.mark.parametrize("name", ALL_KEYBOARDS)
def test_keyboard_is_resized(name):
    assert ALL_KEYBOARDS[name].resize_keyboard is True


@pytest.mark.parametrize("name", ALL_KEYBOARDS)
def test_no_empty_rows(name):
    assert all(len(row) > 0 for row in layout(ALL_KEYBOARDS[name]))


@pytest.mark.parametrize("name", ALL_KEYBOARDS)
def test_labels_are_non_empty_strings(name):
    for text in flat(ALL_KEYBOARDS[name]):
        assert isinstance(text, str)
        assert text.strip() != ""


@pytest.mark.parametrize("name", ALL_KEYBOARDS)
def test_no_duplicate_buttons_inside_a_keyboard(name):
    texts = flat(ALL_KEYBOARDS[name])
    assert len(texts) == len(set(texts))


# ------------------------------------------------------------------
# Back button
# ------------------------------------------------------------------

@pytest.mark.parametrize("name", SUB_KEYBOARDS)
def test_sub_keyboards_have_back_button(name):
    assert c.BACK_BUTTON in flat(SUB_KEYBOARDS[name])


@pytest.mark.parametrize("name", SUB_KEYBOARDS)
def test_back_button_is_on_the_last_row_alone(name):
    last_row = layout(SUB_KEYBOARDS[name])[-1]
    assert last_row == [c.BACK_BUTTON]


def test_main_keyboard_has_no_back_button():
    assert c.BACK_BUTTON not in flat(MAIN_KEYBOARD)


# ------------------------------------------------------------------
# Exact layouts (locks the current design)
# ------------------------------------------------------------------

def test_main_keyboard_layout():
    assert layout(MAIN_KEYBOARD) == [
        [c.GRAPH_BUTTON, c.TODAY_RECORD_BUTTON],
        [c.NEW_RECORD_BUTTON, c.STATISTICS_BUTTON],
        [c.HISTORY_BUTTON, c.SETTINGS_BUTTON],
    ]


def test_history_keyboard_layout():
    assert layout(HISTORY_KEYBOARD) == [
        [c.EXPORT_BUTTON],
        [c.BACK_BUTTON],
    ]


def test_graph_keyboard_layout():
    assert layout(GRAPH_KEYBOARD) == [
        [c.WEEKLY_BUTTON, c.MONTHLY_BUTTON],
        [c.THREE_MONTHS_BUTTON, c.SIX_MONTHS_BUTTON],
        [c.ONE_YEAR_BUTTON],
        [c.BACK_BUTTON],
    ]


def test_settings_keyboard_layout():
    assert layout(SETTINGS_KEYBOARD) == [
        [c.DARK_THEME_BUTTON, c.LIGHT_THEME_BUTTON],
        [c.BACK_BUTTON],
    ]


def test_back_keyboard_layout():
    assert layout(BACK_KEYBOARD) == [[c.BACK_BUTTON]]


# ------------------------------------------------------------------
# Constants: the router matches on text, so texts must be unique
# ------------------------------------------------------------------

def test_all_button_texts_are_unique():
    seen = {}
    duplicates = []

    for name, text in ALL_BUTTONS.items():
        if text in seen:
            duplicates.append(f"{name} and {seen[text]} share {text!r}")
        seen[text] = name

    assert not duplicates, "; ".join(duplicates)


def test_every_button_constant_is_used_by_some_keyboard():
    used = {text for kb in ALL_KEYBOARDS.values() for text in flat(kb)}
    unused = [name for name, text in ALL_BUTTONS.items() if text not in used]

    assert not unused, f"constants not on any keyboard: {unused}"


def test_every_keyboard_button_is_a_known_constant():
    known = set(ALL_BUTTONS.values())
    unknown = [
        text
        for kb in ALL_KEYBOARDS.values()
        for text in flat(kb)
        if text not in known
    ]

    assert not unknown, f"buttons without a constant: {unknown}"


# ------------------------------------------------------------------
# Consistency with the graph feature
# ------------------------------------------------------------------

def test_graph_keyboard_buttons_match_accepted_timelines():
    """Every timeline button must be accepted by the handler
    (send_graph checks `name in GRAPH_TIMELINES`), and every accepted
    timeline must have a button."""
    buttons = set(flat(GRAPH_KEYBOARD)) - {c.BACK_BUTTON}

    assert buttons == set(TIMELINE_BUTTONS)
    assert set(TIMELINE_BUTTONS) == set(c.GRAPH_TIMELINES)


def test_accepted_timelines_exist_in_graph_module():
    """
    Regression guard: create_graph() uses TIMELINE_DAYS.get(name, 30),
    so an unknown name would NOT fail, it would silently draw 30 days.
    """
    missing = [t for t in c.GRAPH_TIMELINES if t not in TIMELINE_DAYS]

    assert not missing, f"unknown to create_graph (falls back to 30 days): {missing}"


def test_every_graph_timeline_is_accepted_by_a_button():
    """Reverse direction: no timeline in graph.py without a button."""
    assert set(TIMELINE_DAYS) == set(c.GRAPH_TIMELINES)
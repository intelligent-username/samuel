"""Tests for stagnation detector."""

from app.services.ats_stagnation import should_early_break


def test_window3_exact_formula():
    # gains (81-80)/80=0.0125, (82-81)/81=0.0123, (82-82)/82=0 => all <0.03 => True
    assert should_early_break([80, 81, 82, 82], window=3, min_relative_gain=0.03) is True
    # gains ~0.06 >0.03 => False
    assert should_early_break([80, 85, 90, 95], window=3, min_relative_gain=0.03) is False
    assert should_early_break([50, 50, 50, 50], window=3, min_relative_gain=0.03) is True


def test_window_configurable():
    # window 2 with 3 elements, all small gains => True
    assert should_early_break([80, 81, 82], window=2, min_relative_gain=0.03) is True
    # same but one gain large => False
    assert should_early_break([80, 81, 90], window=2, min_relative_gain=0.03) is False


def test_custom_min_gain():
    # with min_gain 0.05, gain 0.03 is <0.05 => stagnated
    assert should_early_break([80, 82, 84, 85], window=3, min_relative_gain=0.05) is True
    # gain 0.06 => not stagnated
    assert should_early_break([80, 85, 90, 95], window=3, min_relative_gain=0.05) is False


def test_prev_zero_edge():
    assert should_early_break([0, 0, 0, 0], window=3, min_relative_gain=0.03) is True
    # 0->10 infinite gain => not stagnated
    assert should_early_break([0, 10, 10, 10], window=3, min_relative_gain=0.03) is False
    assert should_early_break([0, 0, 1, 1], window=3, min_relative_gain=0.03) is False


def test_len_le_window_false():
    assert should_early_break([80, 81, 82], window=3) is False
    assert should_early_break([], window=3) is False
    assert should_early_break([80], window=3) is False
    assert should_early_break([80, 81], window=3) is False


def test_config_defaults(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ats_stagnation_window", 2)
    monkeypatch.setattr(settings, "ats_min_gain", 0.05)
    # without explicit args reads settings
    assert should_early_break([80, 81, 82]) is True  # window 2, min 0.05, gains 0.0125,0.012 <0.05
    assert should_early_break([80, 90, 100]) is False  # gains large

    monkeypatch.setattr(settings, "ats_stagnation_window", 3)
    monkeypatch.setattr(settings, "ats_min_gain", 0.03)
    assert should_early_break([80, 81, 82, 82]) is True

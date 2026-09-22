"""Tests for python_utils.text."""

from __future__ import annotations

import pytest

from python_utils import text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hello, World!", "hello-world"),
        ("Café déjà vu", "cafe-deja-vu"),
        ("  --spaced  out--  ", "spaced-out"),
        ("under_score stays", "under-score-stays"),
        ("trailing...dots", "trailing-dots"),
        ("MiXeD CaSe", "mixed-case"),
        ("already-a-slug", "already-a-slug"),
    ],
)
def test_slugify(value: str, expected: str) -> None:
    assert text.slugify(value) == expected


def test_slugify_empty_and_all_punctuation() -> None:
    assert text.slugify("") == ""
    assert text.slugify("!!!") == ""
    # Non-Latin scripts get stripped to nothing. Documented, and asserted here
    # so nobody "fixes" it by accident.
    assert text.slugify("日本語") == ""


def test_slugify_max_length_drops_trailing_separator() -> None:
    # Cutting at 6 lands right after "hello-", so the trailing dash must go.
    assert text.slugify("hello world foo", max_length=6) == "hello"
    assert text.slugify("hello world foo", max_length=5) == "hello"


def test_slugify_custom_separator() -> None:
    assert text.slugify("hello world", separator="_") == "hello_world"


def test_slugify_rejects_bad_input() -> None:
    with pytest.raises(TypeError):
        text.slugify(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        text.slugify("x", max_length=0)


def test_truncate_short_input_is_untouched() -> None:
    assert text.truncate("hello", 10) == "hello"
    assert text.truncate("hello", 5) == "hello"


def test_truncate_backs_up_to_word_boundary() -> None:
    # "hello wo" splits "world", so it backs up to the space and appends.
    assert text.truncate("hello world", 8, suffix="...") == "hello..."


def test_truncate_mid_word_when_asked() -> None:
    assert text.truncate("hello world", 8, suffix="...", word_boundary=False) == "hello wo..."


def test_truncate_no_space_to_back_up_to() -> None:
    # A single long token: there's no boundary, so cut anyway rather than
    # return an empty string.
    assert text.truncate("abcdefghij", 4, suffix="...") == "abcd..."


def test_truncate_zero_length() -> None:
    assert text.truncate("hello", 0, suffix="") == ""
    assert text.truncate("hello", 0, suffix="...") == "..."


def test_truncate_output_may_exceed_length() -> None:
    # The suffix is added on top of the kept characters. Asserted so the
    # behavior is pinned, not accidental.
    out = text.truncate("hello world", 5, suffix="[more]")
    assert out == "hello[more]"
    assert len(out) > 5


def test_truncate_rejects_negative_length() -> None:
    with pytest.raises(ValueError):
        text.truncate("hello", -1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (10, "10th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (101, "101st"),
        (111, "111th"),
        (0, "0th"),
        (-1, "-1st"),
    ],
)
def test_ordinal(value: int, expected: str) -> None:
    assert text.ordinal(value) == expected


def test_ordinal_rejects_non_int() -> None:
    with pytest.raises(TypeError):
        text.ordinal(1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        text.ordinal(True)  # type: ignore[arg-type]

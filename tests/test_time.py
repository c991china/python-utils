"""Tests for python_utils.time_utils."""

from __future__ import annotations

import pytest

from python_utils import time_utils


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("90", 90.0),
        (90, 90.0),
        ("30s", 30.0),
        ("5m", 300.0),
        ("2h", 7200.0),
        ("1d", 86400.0),
        ("2h30m", 9000.0),
        ("1.5h", 5400.0),
        ("1d2h3m4s", 93784.0),
        ("  2h 30m  ", 9000.0),
        ("1H30M", 9000.0),  # units are case-insensitive
    ],
)
def test_parse_duration_ok(value: object, expected: float) -> None:
    assert time_utils.parse_duration(value) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["", "   ", "abc", "2x", "h30", "2h30"])
def test_parse_duration_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        time_utils.parse_duration(bad)


def test_parse_duration_rejects_bad_types() -> None:
    with pytest.raises(TypeError):
        time_utils.parse_duration(None)  # type: ignore[arg-type]
    # bool is technically an int; we reject it because True == 1 second is
    # never what a caller meant.
    with pytest.raises(TypeError):
        time_utils.parse_duration(True)  # type: ignore[arg-type]


def test_parse_duration_rejects_negative() -> None:
    with pytest.raises(ValueError):
        time_utils.parse_duration(-1)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0s"),
        (59, "59s"),
        (60, "1m"),
        (9000, "2h 30m"),
        (93784, "1d 2h"),
        (-3661, "-1h 1m"),
    ],
)
def test_humanize_delta_default_precision(seconds: float, expected: str) -> None:
    assert time_utils.humanize_delta(seconds) == expected


def test_humanize_delta_precision_three() -> None:
    assert time_utils.humanize_delta(93784, precision=4) == "1d 2h 3m 4s"
    assert time_utils.humanize_delta(93784, precision=3) == "1d 2h 3m"


def test_humanize_delta_rounds_subsecond_to_zero() -> None:
    assert time_utils.humanize_delta(0.4) == "0s"


def test_humanize_delta_rejects_bad_precision() -> None:
    with pytest.raises(ValueError):
        time_utils.humanize_delta(10, precision=0)


def test_retry_succeeds_without_retrying() -> None:
    calls = []

    @time_utils.retry(times=3, backoff=0)
    def ok() -> str:
        calls.append(1)
        return "done"

    assert ok() == "done"
    assert len(calls) == 1


def test_retry_retries_then_succeeds() -> None:
    calls = []

    @time_utils.retry(times=4, backoff=0)
    def flaky() -> int:
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError(f"boom {len(calls)}")
        return len(calls)

    assert flaky() == 3
    assert len(calls) == 3


def test_retry_gives_up_and_reraises_original() -> None:
    calls = []

    @time_utils.retry(times=2, backoff=0)
    def always_fails() -> None:
        calls.append(1)
        raise KeyError("nope")

    with pytest.raises(KeyError):
        always_fails()
    # times=2 means two attempts total, not two retries.
    assert len(calls) == 2


def test_retry_only_catches_listed_exceptions() -> None:
    calls = []

    @time_utils.retry(times=3, backoff=0, exceptions=(ValueError,))
    def wrong_error() -> None:
        calls.append(1)
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        wrong_error()
    assert len(calls) == 1


def test_retry_validates_arguments() -> None:
    with pytest.raises(ValueError):
        time_utils.retry(times=0)
    with pytest.raises(ValueError):
        time_utils.retry(backoff=-1)
    with pytest.raises(ValueError):
        time_utils.retry(factor=0.5)


def test_retry_preserves_metadata() -> None:
    @time_utils.retry(times=2, backoff=0)
    def documented() -> None:
        """A docstring that should survive wrapping."""

    assert documented.__name__ == "documented"
    assert "should survive" in (documented.__doc__ or "")

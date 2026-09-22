"""Tests for python_utils.fs. Run with: pytest -q"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_utils import fs


def test_safe_write_json_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    fs.safe_write_json(target, {"b": 1, "a": [1, 2, 3]})

    assert json.loads(target.read_text(encoding="utf-8")) == {"b": 1, "a": [1, 2, 3]}
    # The file should end in exactly one newline, not zero and not two.
    assert target.read_text(encoding="utf-8").endswith("}\n")


def test_safe_write_json_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "out.json"
    fs.safe_write_json(target, {"ok": True})
    assert target.is_file()


def test_safe_write_json_sorts_keys_when_asked(tmp_path: Path) -> None:
    target = tmp_path / "sorted.json"
    fs.safe_write_json(target, {"z": 1, "a": 2}, sort_keys=True)
    assert target.read_text(encoding="utf-8").startswith('{\n  "a"')


def test_safe_write_json_leaves_no_temp_files(tmp_path: Path) -> None:
    # The whole point of the atomic path is that nothing half-written is left
    # behind. If the temp file survives, this test fails loudly.
    for i in range(5):
        fs.safe_write_json(tmp_path / "x.json", {"i": i})

    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "x.json"]
    assert leftovers == []


def test_safe_write_json_non_atomic(tmp_path: Path) -> None:
    target = tmp_path / "plain.json"
    returned = fs.safe_write_json(target, {"x": 1}, atomic=False, indent=None)
    assert returned == target
    assert target.read_text(encoding="utf-8").strip() == '{"x": 1}'


def test_safe_write_json_serializes_unknown_types(tmp_path: Path) -> None:
    # default=str is a deliberate escape hatch for things like Path and Decimal.
    target = tmp_path / "path.json"
    fs.safe_write_json(target, {"p": Path("/tmp/x")})
    assert "x" in target.read_text(encoding="utf-8")


def test_iter_files_filters_and_sorts(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    (tmp_path / ".hidden.py").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("x")
    (tmp_path / "sub" / ".git").mkdir()
    (tmp_path / "sub" / ".git" / "d.py").write_text("x")

    found = list(fs.iter_files(tmp_path, "py"))

    assert found == [tmp_path / "a.py", tmp_path / "sub" / "c.py"]


def test_iter_files_accepts_ext_with_or_without_dot(tmp_path: Path) -> None:
    (tmp_path / "a.JSON").write_text("x")
    assert list(fs.iter_files(tmp_path, ".json")) == [tmp_path / "a.JSON"]
    assert list(fs.iter_files(tmp_path, "json")) == [tmp_path / "a.JSON"]


def test_iter_files_includes_hidden_when_asked(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("x")
    (tmp_path / "visible").write_text("x")

    assert list(fs.iter_files(tmp_path)) == [tmp_path / "visible"]
    assert len(list(fs.iter_files(tmp_path, skip_hidden=False))) == 2


def test_iter_files_missing_root_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(fs.iter_files(tmp_path / "nope"))


def test_iter_files_on_a_file_raises(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        list(fs.iter_files(f))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1536, "1.5 KiB"),
        (1048576, "1.0 MiB"),
        (-1536, "-1.5 KiB"),
    ],
)
def test_human_bytes_binary(value: float, expected: str) -> None:
    assert fs.human_bytes(value) == expected


def test_human_bytes_decimal_units() -> None:
    # 1536 bytes is 1.5 KiB but 1.5 kB too, so use a value where they differ.
    assert fs.human_bytes(1500000, binary=True) == "1.4 MiB"
    assert fs.human_bytes(1500000, binary=False) == "1.5 MB"


def test_human_bytes_precision() -> None:
    assert fs.human_bytes(1234567, precision=3) == "1.177 MiB"
    with pytest.raises(ValueError):
        fs.human_bytes(1, precision=-1)

"""Filesystem helpers. Nothing here is clever; it's the boring stuff done right.

The one function worth reading is safe_write_json. Writing JSON directly to the
target path means a crash mid-write leaves a half file behind, and if something
else is reading that path (a watcher, a container, another process) it gets
truncated JSON. Temp file plus os.replace fixes that.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

__all__ = ["safe_write_json", "iter_files", "human_bytes"]

_UNITS_BINARY = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
_UNITS_DECIMAL = ["B", "kB", "MB", "GB", "TB", "PB"]


def safe_write_json(
    path: str | os.PathLike[str],
    data: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = False,
    atomic: bool = True,
) -> Path:
    """Serialize `data` to `path` as UTF-8 JSON.

    With atomic=True (the default) the write goes to a temp file in the same
    directory and is then renamed over the target. Renames are atomic on the
    same filesystem, so readers see either the old file or the new one, never a
    partial. The temp file has to be in the same directory as the target for
    that guarantee to hold; putting it in /tmp and moving across filesystems
    degrades to a copy and loses atomicity.

    Missing parent directories are created. A trailing newline is appended
    because `git diff` on a file without one is annoying.

    Returns the path written to, as a Path.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        data,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,
        default=str,
    )
    if not payload.endswith("\n"):
        payload += "\n"

    if not atomic:
        target.write_text(payload, encoding="utf-8")
        return target

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            # Without fsync the rename can land before the data does on a
            # power loss. Cheap insurance for config files.
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        # mkstemp's fd is owned by fdopen now; only the file needs cleaning up.
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return target


def iter_files(
    root: str | os.PathLike[str],
    ext: str | Iterable[str] | None = None,
    *,
    skip_hidden: bool = True,
    follow_symlinks: bool = False,
) -> Iterator[Path]:
    """Walk `root` and yield files, sorted, with an optional extension filter.

    `ext` accepts a single extension or an iterable; with or without the leading
    dot ("json" and ".json" behave the same), case-insensitive.

    skip_hidden drops any file or directory whose name starts with a dot. It's
    on by default because the alternative is walking .git on every call, which
    is slow and never what you wanted.

    Raises FileNotFoundError if root doesn't exist. Note this returns a sorted
    list wrapped in an iterator, so the walk finishes before you get the first
    item. For a 2M-file tree that matters; for anything normal it doesn't.
    """
    base = Path(root)
    if not base.exists():
        raise FileNotFoundError(f"no such path: {base}")
    if not base.is_dir():
        raise NotADirectoryError(f"not a directory: {base}")

    wanted: set[str] | None = None
    if ext is not None:
        raw = {ext} if isinstance(ext, str) else set(ext)
        wanted = {
            (e if e.startswith(".") else f".{e}").lower() for e in raw if e
        }

    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=follow_symlinks):
        if skip_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if skip_hidden and name.startswith("."):
                continue
            candidate = Path(dirpath) / name
            if wanted is not None and candidate.suffix.lower() not in wanted:
                continue
            found.append(candidate)

    return iter(sorted(found))


def human_bytes(n: float, *, binary: bool = True, precision: int = 1) -> str:
    """Format a byte count for humans. 1536 -> '1.5 KiB'.

    binary=True uses 1024 and KiB/MiB labels. binary=False uses 1000 and kB/MB,
    which is what disk vendors mean by "500 GB". Pick deliberately; mixing the
    two is how you end up 7% short on a capacity estimate.

    Values under 1 KiB are printed as a whole number of bytes with no decimals.
    Negative inputs keep their sign.
    """
    if precision < 0:
        raise ValueError("precision must be >= 0")

    value = float(n)
    sign = "-" if value < 0 else ""
    value = abs(value)

    base = 1024 if binary else 1000
    units = _UNITS_BINARY if binary else _UNITS_DECIMAL

    idx = 0
    while value >= base and idx < len(units) - 1:
        value /= base
        idx += 1

    if idx == 0:
        return f"{sign}{int(value)} B"
    return f"{sign}{value:.{precision}f} {units[idx]}"

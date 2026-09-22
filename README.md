# python-utils

Small, stdlib-only helpers I kept copy-pasting between projects. Now they live
in one place with tests.

Why this exists: every project I touch ends up needing the same four things. Write
JSON without leaving a half file if the process dies. Walk a tree filtered by
extension without dragging in `.git`. Turn "30d" into seconds. Print a byte
count that a human can read. Each is a few lines, and each has a way to get it
subtly wrong. This is the version I got right, once, with tests.

No runtime dependencies. Python 3.9+. Not trying to replace `requests`, `attrs`,
`pydantic`, or anything else that does real work.

## Install

From a checkout:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Straight from git:

```bash
pip install "git+https://github.com/c991china/python-utils@v0.4.2"
```

The distribution is named `python-utils-c991china` because `python-utils` was
already taken on PyPI. The import name is `python_utils`.

## What's in it

| Module | Functions |
| --- | --- |
| `fs` | `safe_write_json`, `iter_files`, `human_bytes` |
| `time_utils` | `parse_duration`, `humanize_delta`, `retry` |
| `text` | `slugify`, `truncate`, `ordinal` |
| `net` | `get_json` (one GET, retries, real errors) |
| `cli` | wires all of the above to `python-utils` |

## Usage

```python
from python_utils import fs, text, time_utils

# Atomic JSON write. Creates parent dirs, appends a trailing newline.
fs.safe_write_json("build/manifest.json", {"retention": 86400})

# "30d" -> 2592000.0, and back again as "30d"
seconds = time_utils.parse_duration("30d")
print(time_utils.humanize_delta(seconds))

# Extension filter, case-insensitive, dot optional, dotfiles skipped.
for path in fs.iter_files("src", ["py", "pyi"]):
    print(path, fs.human_bytes(path.stat().st_size))
```

Output of the last bit on this repo:

```
src/python_utils/__init__.py 401 B
src/python_utils/cli.py 3.1 KiB
src/python_utils/fs.py 5.6 KiB
...
```

Retrying something flaky:

```python
from python_utils.time_utils import retry

@retry(times=4, backoff=0.25)   # 4 attempts total, 0.25s / 0.5s / 1s waits
def fetch_config(url: str) -> dict:
    ...
```

`times` is attempts, not retries. `times=4` means one call plus three retries.
The last exception is re-raised untouched so the traceback is useful.

One HTTP GET:

```python
from python_utils.net import get_json, HttpStatusError

try:
    data = get_json("https://api.example.com/v1/status",
                    timeout=5, retries=2, params={"verbose": "1"})
except HttpStatusError as exc:
    print(exc.status, exc.body[:200])   # body is kept, truncated in the message
```

Retries only fire on 408/425/429/5xx and on connection-level errors. A 404 is
raised immediately. Retrying a 404 is a good way to get rate limited for nothing.

## CLI

```bash
python-utils human-bytes 1536            # 1.5 KiB
python-utils human-bytes 1536 --decimal  # 1.5 kB
python-utils slugify "Café déjà vu"      # cafe-deja-vu
python-utils truncate "hello world" 8    # hello…
python-utils duration 2h30m              # 9000
python-utils humanize 93784              # 1d 2h
python-utils ls ./src --ext .py
```

Exit code 1 on bad input, 2 on a usage error, 0 on success. Useful in shell
scripts where you want `if ! python-utils duration "$X"; then`.

## Gotchas

**`slugify` deletes non-Latin scripts.** `slugify("日本語")` returns `""`. Accents
are handled (NFKD + strip combining marks), everything outside Latin is not.
There's no transliteration here and I'm not adding a dependency for it.

**`truncate` output can be longer than the length you passed.** The suffix is
added on top. `truncate("hello world", 5, suffix="[more]")` is `"hello[more]"`,
11 characters. The alternative was dropping characters from your text silently,
which I liked less.

**`iter_files` returns an iterator over a fully-sorted list.** The walk completes
before you get the first item. On a tree with a few million files that's a real
pause. For normal source trees it's irrelevant.

**`iter_files` follows symlinks only if you ask.** Default is `follow_symlinks=False`,
so a symlink loop can't hang the walk.

**`retry` is sync only.** Decorating an `async def` gives you back a coroutine
that's never awaited, and no retries happen. It doesn't error, which is worse
than erroring. I left async out on purpose rather than half-do it.

**`parse_duration("2h30")` raises.** Every number needs a unit once you've used
one. Mixed bare-and-united strings are ambiguous and I'd rather fail than guess.

## Notes

Version 0.4.x is what I'd call stable for my own use: the API hasn't changed in
about a year and the tests cover the edge cases that used to bite. Nothing here
is thread-safe in an interesting way; the functions are pure except for the file
writes, and `safe_write_json` to the same path from two processes is last-write-
wins (the rename keeps each write whole, but they still race).

Tested on CPython 3.9.18, 3.11.7 and 3.12.3, on Ubuntu 22.04 and macOS 14.4.
The Windows path handling in `safe_write_json` uses `os.replace`, which is
atomic there too, but I haven't run the suite on Windows.

Run the tests:

```bash
pytest -q                    # ~85 tests, under a second
pytest --cov=python_utils    # needs the [dev] extra
```

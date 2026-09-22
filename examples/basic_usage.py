"""Walk through the four modules. Run from the repo root:

    python examples/basic_usage.py

Nothing here touches the network except the last block, which is commented out
because it needs a live URL.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from python_utils import fs, text, time_utils


def fs_demo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Config values from a config string, the way you'd parse a settings file.
        retention = time_utils.parse_duration("30d")
        print(f"retention is {retention:g}s ({time_utils.humanize_delta(retention)})")

        fs.safe_write_json(
            root / "build" / "manifest.json",
            {"retention_seconds": retention, "generated_by": "example"},
        )

        (root / "build" / "notes.md").write_text("# notes\n")

        print("files under tmp root:")
        for path in fs.iter_files(root):
            size = fs.human_bytes(path.stat().st_size)
            print(f"  {path.relative_to(root)}  {size}")


def text_demo() -> None:
    title = "How We Cut p99 Latency by 40% (a postmortem)"
    print(f"slug:     {text.slugify(title, max_length=40)}")
    print(f"short:    {text.truncate(title, 24)}")
    print(f"rank:     {text.ordinal(23)} percentile")


def retry_demo() -> None:
    attempts = {"n": 0}

    @time_utils.retry(times=3, backoff=0.05)
    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError(f"attempt {attempts['n']} failed")
        return "connected"

    print(f"retry:    {flaky()} after {attempts['n']} attempts")


def net_demo() -> None:
    # Uncomment and point at something real.
    #
    # from python_utils import net
    # data = net.get_json("https://api.github.com/repos/python/cpython",
    #                     timeout=5, retries=1)
    # print(data["stargazers_count"])
    print("net:      skipped (needs a live URL)")


if __name__ == "__main__":
    fs_demo()
    text_demo()
    retry_demo()
    net_demo()

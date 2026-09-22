"""python_utils - the handful of helpers I retype in every project.

Small on purpose. No dependencies outside the standard library, Python 3.9+.
If you want a big toolkit, use `boltons` or `more-itertools`; this is for the
four or five functions that never justify pulling in a dependency.

    from python_utils import fs, text, time_utils

    fs.safe_write_json("out.json", {"ok": True})
    print(text.slugify("Café déjà vu"))          # cafe-deja-vu
    print(time_utils.parse_duration("2h30m"))    # 9000.0
"""

from __future__ import annotations

from . import fs, net, text, time_utils

__version__ = "0.4.2"

__all__ = ["fs", "net", "text", "time_utils", "__version__"]

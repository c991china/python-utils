"""Text munging: slugs, truncation, ordinals.

All three of these have a subtlety that bit me at some point, which is why
they're here instead of being one-liners in whatever project needed them.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["slugify", "truncate", "ordinal"]

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(
    value: str,
    *,
    max_length: int | None = None,
    separator: str = "-",
) -> str:
    """Make a URL-safe slug. 'Café déjà vu' -> 'cafe-deja-vu'.

    Accents are stripped by NFKD-decomposing and dropping the combining marks,
    so 'é' becomes 'e'. This handles Latin scripts well and destroys everything
    else: '日本語' slugifies to an empty string, and Cyrillic becomes empty too.
    If you need non-Latin slugs, transcode first or don't use this.

    With max_length set, the result is cut and any trailing separator removed.
    Cutting is by character, not by word, so you can end up with a partial word.
    That's usually fine for slugs and I'd rather not guess at word boundaries.

    Raises TypeError for non-str input.
    """
    if not isinstance(value, str):
        raise TypeError(f"expected str, got {type(value).__name__}")
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")

    decomposed = unicodedata.normalize("NFKD", value)
    ascii_ish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = ascii_ish.lower()

    slug = _NON_SLUG.sub(separator, lowered)
    slug = slug.strip(separator)

    # A separator that is itself non-alphanumeric can't come from the input, but
    # a multi-char one plus adjacent runs can still double up.
    if separator:
        doubled = separator + separator
        while doubled in slug:
            slug = slug.replace(doubled, separator)

    if max_length is not None:
        slug = slug[:max_length].strip(separator)

    return slug


def truncate(
    text: str,
    length: int,
    *,
    suffix: str = "\u2026",
    word_boundary: bool = True,
) -> str:
    """Cut `text` to at most `length` characters, appending `suffix` if cut.

    The returned string can be longer than `length` when a suffix is added.
    I know that's surprising. The alternative is silently dropping characters
    from the caller's text, and I'd rather the output be honest.

    With word_boundary=True (default) it backs up to the last space instead of
    splitting a word mid-way. If there's no space in the kept portion it cuts
    anyway rather than returning an empty string.

    Raises ValueError for a negative length.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if length < 0:
        raise ValueError("length must be >= 0")

    if len(text) <= length:
        return text
    if length == 0:
        return suffix

    kept = text[:length]

    if word_boundary and not text[length].isspace():
        last_space = kept.rfind(" ")
        # Only back up if that leaves something; a 3-char word cut at 2 should
        # still produce output.
        if last_space > 0:
            kept = kept[:last_space]

    return kept.rstrip() + suffix


def ordinal(n: int) -> str:
    """1 -> '1st', 12 -> '12th', 23 -> '23rd'.

    The 11/12/13 cases are the reason this isn't a lookup table on n % 10.
    Negatives keep the sign and use the absolute value for the suffix, so -1
    gives '-1st'. Not sure anyone wants that, but it's less surprising than
    crashing.

    Raises TypeError for non-int. Floats are rejected rather than truncated;
    pass int(x) if you meant that.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"expected int, got {type(n).__name__}")

    remainder_100 = abs(n) % 100
    if 10 <= remainder_100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(abs(n) % 10, "th")

    return f"{n}{suffix}"

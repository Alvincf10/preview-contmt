#!/usr/bin/env python3
"""Count the columns each Arduino data source writes, by reading the code.

An off-by-one here puts a temperature into a date field, so the count is derived
from the source rather than from prose.

The subtlety is helpers. `sensors()` writes three channel values and an average,
with a `sep()` after each, then a mask: five fields but only four separators
visible if you count `sep()` calls without following the loop. And a caller that
ends with `sep(); sensors(...)` adds five more columns, not four.

So this counts fields, not separators: a field is written by `real`, `digits`,
`scaled`, `storedText`, `timestamp`, `flash`, `localDate`, `prediction`, or by a
helper that writes several of them. Following each helper is what makes the count
right.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "arduino" / "ConMT" / "src" / "Panel.cpp"
text = SOURCE.read_text(encoding="utf-8", errors="replace")

# A call that writes one column.
SCALAR_WRITERS = (
    "digits(", "scaled(", "real(", "storedText(", "timestamp(", "localDate(",
    "flash(FSTR(\"1.0.0\"))",
)
# A helper that writes several; each one is followed to its own body.
HELPERS = ("sensors(", "identityData(", "baseData(", "prediction(", "runData(", "pointData(")


def body_of(name: str) -> str:
    pattern = rf"\n(?:Answer|void|static\s+\w+|inline\s+\w+)\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
    match = re.search(pattern, text)
    if not match:
        return ""
    start = text.find("{", match.start())
    depth = 0
    end = start
    while end < len(text):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                break
        end += 1
    return text[start:end]


def fields_written(body: str, seen: set[str] | None = None) -> int:
    """How many columns a function body writes, following its helpers."""
    seen = seen or set()
    count = 0

    for name in HELPERS:
        stem = name[:-1]
        for match in re.finditer(re.escape(name), body):
            # A helper's own definition must not be counted as a call.
            if stem in seen:
                continue
            inner = body_of(stem)
            if inner:
                seen.add(stem)
                count += fields_written(inner, seen)

    for writer in SCALAR_WRITERS:
        if writer == 'flash(FSTR("1.0.0"))':
            count += body.count(writer)
        else:
            count += body.count(writer)

    # A loop over three channels writes three values where the body has one call.
    for match in re.finditer(r"for\s*\([^)]*<\s*3[^)]*\)\s*\{", body):
        start = body.find("{", match.start())
        depth = 0
        end = start
        while end < len(body):
            if body[end] == "{":
                depth += 1
            elif body[end] == "}":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        inner = body[start:end]
        once = sum(inner.count(w) for w in ("real(", "digits(", "scaled("))
        count += once * 2  # the body writes one, the loop writes three

    return count


def main() -> None:
    for name in ("sensors", "identityData", "baseData", "runData", "pointData", "readView"):
        body = body_of(name)
        if not body:
            print(f"{name}: not found")
            continue
        print(f"{name:14} {fields_written(body):3} columns")


if __name__ == "__main__":
    main()

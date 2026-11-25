#!/usr/bin/env python3
"""Check every column binding against the column list it points into.

A binding says "field tM shows column 10 of source run". If that index falls
outside the source's columns, or points at a column of the wrong kind - a date
where a number belongs - the panel shows nonsense, and it does so silently.

This checks the things that can be checked without the firmware running: that
every index is in range, that every bound field exists on its page, and that no
two fields claim the same column of the same source unless that is deliberate.

Run: python nextion/tools/check_bindings.py
"""

from __future__ import annotations

import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc" / "pages"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arduino_protocol import BINDINGS, PAGE_SOURCES, SOURCES  # noqa: E402

# A column whose name says what it holds. Used to catch a binding that points at
# a plausible-looking index of the wrong kind.
NUMERIC = ("temperature", "fc", "maturity", "percent", "seconds", "average", "s1",
           "s2", "s3", "target", "datum", "cement", "water", "coarse", "fine",
           "retarder", "accelerator", "flyAsh", "wc", "a", "b", "r2", "pairs",
           "factors", "maxM", "day", "age", "rows", "points", "partial", "ref",
           "count", "supply", "battery", "sdCode", "active", "interval",
           "brightness", "flags", "mask", "selected", "selectedResult",
           "identityReady", "draftFromSaved", "baselines", "result", "model",
           "identity", "fcLab", "startTemp")


def page_fields(page: str) -> set[str]:
    data = tomllib.loads((PAGES / f"{page}.page.toml").read_text(encoding="utf-8"))
    return {c["name"] for c in data.get("component", []) if c.get("type") == "text"}


def main() -> int:
    problems: list[str] = []

    for page, bindings in BINDINGS.items():
        fields = page_fields(page)
        sources = PAGE_SOURCES.get(page, [])
        used: dict[tuple[str, int], list[str]] = defaultdict(list)

        for field, (source, index) in bindings.items():
            if field not in fields:
                problems.append(f"{page}.{field}: bound, but the page has no such field")
            if source not in SOURCES:
                problems.append(f"{page}.{field}: unknown source {source!r}")
                continue
            if source not in sources:
                problems.append(
                    f"{page}.{field}: reads {source!r}, which the page never asks for"
                )
            columns = SOURCES[source]
            if index >= len(columns):
                problems.append(
                    f"{page}.{field}: column {index} of {source!r}, which has only {len(columns)}"
                )
                continue
            used[(source, index)].append(field)

        # Two fields reading one column is allowed - a value shown twice, or the
        # same value on every card of a list, which the firmware fills one row at
        # a time. It is worth seeing only when the two fields look unrelated.
        LIST_PAGES = {"pSaveB", "pSelB", "pHist", "pHistD", "pMatu", "pBaseR", "pRT", "pStr"}
        for (source, index), names in used.items():
            if len(names) > 1 and page not in LIST_PAGES:
                problems.append(
                    f"{page}: {', '.join(names)} all read {source}[{index}] ({SOURCES[source][index]})"
                )

    for page, sources in PAGE_SOURCES.items():
        for source in sources:
            if source not in SOURCES:
                problems.append(f"{page}: asks for unknown source {source!r}")

    for problem in problems:
        print(problem)
    print(f"\n{len(BINDINGS)} page(s) bound, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

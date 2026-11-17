# Numerical fixtures

reference-vectors.json is the executable TypeScript oracle output from the original ConMT source and lab workbook, preserved here so a clone can run firmware tests without the local firmware-plan folder. excel.tsv is the full-precision41-row workflow fixture. No fixture is linked into production.

Source workbook: docs/acuan/Syarat-Kroscek-Perhitungan-ConMT-Data-Real.xlsx. Domain source: src/maturityFit.ts. Audit/provenance summaries are in firmware/reviews/2026-11-16-audit. The complete local planning package remains excluded from Git at the owner's request.

hmi-wire.txt was captured by tests/hmi_snapshot.cpp from the presenter at checkpoint72697e1 before flash-text changes. It covers all17pages, populated/empty fields, preserved laboratory input strings, session/results/history and settings. It is a regression oracle for UART field output, not an assertion that the physical panel layout has been verified. Do not regenerate it to conceal behavior changes.

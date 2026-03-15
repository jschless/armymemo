# armymemo

`armymemo` is a standalone Python library for generating Army memorandums from structured text or Python objects and rendering them with Typst.

## What is included

- Legacy `.Amd` parsing and `MemoDoc` parsing
- Deterministic Typst templates and rulebook-driven layout
- PDF compilation through a managed Typst binary
- Review helpers for structural and rendered-PDF checks
- Packaged example memo fixtures available after install
- A small CLI for rendering, review, corpus generation, PDF comparison, and benchmarking

## Install

```bash
pip install .
```

For development:

```bash
pip install -e .[dev]
```

## CLI

The CLI accepts either a real file path or the basename of a packaged example such as `basic_mfr.Amd`.

Render a memo to PDF:

```bash
armymemo render basic_mfr.Amd --output basic_mfr.pdf
```

Render Typst source only:

```bash
armymemo render basic_mfr.Amd --source-only --output basic_mfr.typ
```

Run a rendered review:

```bash
armymemo review long_memo.Amd --render
```

Benchmark Typst rendering:

```bash
armymemo benchmark basic_mfr.Amd
```

Generate the representative visual review pack:

```bash
armymemo review-pack artifacts/review-pack-01
```

## Tests

```bash
PYTHONPATH=. pytest
```

## Notes

- The standalone repo ships Typst as the only supported renderer.
- The managed Typst runtime is pinned to `0.14.2` for fresh installs.
- The current rulebook is grounded in AR 25-50 excerpts plus historical calibration notes from the prior mixed-repo implementation.
- Generated PDFs and local artifacts should stay out of version control.

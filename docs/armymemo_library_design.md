# ArmyMemo Standalone Library Design

## Status

- Historical extraction design
- Retained to document major decisions behind the standalone repo split
- The standalone `armymemo` package now lives in this repo, and Typst is the only shipped renderer

## Summary

The current repository mixes three distinct concerns:

1. Memo authoring and rendering logic
2. Web application concerns such as auth, persistence, and background jobs
3. PDF validation and presentation features

This design split the memo engine into a standalone Python library that can be installed with `pip`, used directly by AI agents, and rendered through Typst. The old `.Amd` format remains supported as a compatibility input path, but the new default authoring format becomes a structured, AI-friendly text format named `MemoDoc`.

The migration was not just a renderer swap. It was a layout-equivalence effort during extraction. References to LaTeX in this document are historical notes from that migration period, not part of the standalone repo's supported public surface.

## Goals

- Provide a standalone Python library with a small, explicit public API
- Support direct programmatic generation by LLMs and non-web automation
- Replace LaTeX as the primary PDF backend with Typst
- Keep legacy `.Amd` input working during the transition
- Introduce a clearer default input format for humans and AI
- Make rendering quality measurable through automated PDF equivalence testing
- Keep web-app integration out of scope until the library contract stabilizes

## Non-Goals

- Migrating the Flask app in the same change
- Preserving the current `app.*` import surface
- Solving Windows packaging in v1
- Declaring the existing AR 25-50 validator to be sufficient as the renderer quality gate

## Repo and Package Boundary

### Target shape

The standalone engine should live as a first-class package with no dependency on Flask, SQLAlchemy, S3, Huey, or the template/static web layer.

Planned package responsibilities:

- `armymemo.document`
  - canonical memo document model
- `armymemo.parser`
  - input parsing for legacy `.Amd` and new `MemoDoc`
- `armymemo.renderers`
  - Typst primary renderer
- `armymemo.compiler`
  - Typst binary resolution and compilation
- `armymemo.comparison`
  - PDF layout extraction and equivalence checks
- `armymemo.corpus`
  - deterministic synthetic memo generation
- `armymemo.cli`
  - local/manual CLI entrypoint

### Dependencies intentionally excluded from the standalone library

- Flask and WTForms
- Auth and database packages
- S3 upload/storage logic
- Background task orchestration
- Web-specific validation endpoints

## Canonical Document Model

The library should render from a neutral model, not from LaTeX-escaped strings.

Core model types:

- `MemoDocument`
  - unit header metadata
  - office symbol
  - subject
  - author metadata
  - memo type
  - recipients
  - optional suspense/authority/enclosure/distro/cf fields
  - body nodes
- `Recipient`
  - name
  - street address
  - city/state/zip
- `BodyItem`
  - one or more paragraphs
  - nested children
- `TableBlock`
  - headers
  - rows

This model is renderer-neutral and should be the only object that flows into Typst rendering and review tooling.

## Input Formats

### 1. Legacy `.Amd` compatibility

Legacy `.Amd` stays supported because:

- existing examples are valuable regression fixtures
- the current web app depends on it
- it provides a migration path for current users

The library should parse legacy `.Amd` and be able to serialize back to `.Amd` when needed.

### 2. New default format: `MemoDoc`

`MemoDoc` is the AI-facing and human-friendly format. It uses YAML front matter for metadata plus a markdown-style body for paragraphs, nested list items, and tables.

Example:

```text
---
unit:
  name: 4th Engineer Battalion
  street_address: 588 Wetzel Road
  city_state_zip: Colorado Springs, CO 80904
office_symbol: ABC-DEF-GH
date: 14 March 2026
memo_type: memorandum_for_record
subject: Motor Pool Safety Inspection Results
author:
  name: Jordan A. Carter
  rank: CPT
  branch: EN
  title: Company Commander
enclosures:
  - Inspection Roster
---
- Conduct a weekly review of safety deficiencies.
- Track all unresolved issues in the battalion maintenance tracker.
    - Include the corrective action owner.
    - Include the target completion date.
```

Why this format:

- metadata is structurally explicit, which helps LLM generation
- body syntax stays readable and close to current memo authoring behavior
- YAML supports lists and nested recipients cleanly
- it is easier to validate and evolve than ad hoc key-value headers

### Parsing policy

- `parse_text()` auto-detects `MemoDoc` when the text starts with YAML front matter
- otherwise it parses legacy `.Amd`
- the document model does not preserve source-specific quirks beyond what is needed for round-tripping

## Public API

Initial Python API:

```python
from armymemo import (
    MemoDocument,
    parse_file,
    parse_text,
    render_latex_source,
    render_typst_source,
    TypstCompiler,
    compare_pdfs,
    generate_corpus,
)
```

Required operations:

- `parse_text(text) -> MemoDocument`
- `parse_file(path) -> MemoDocument`
- `document.to_memodoc() -> str`
- `document.to_amd() -> str`
- `render_typst_source(document) -> str`
- `render_latex_source(document) -> str`
- `TypstCompiler.compile_source(source, output_path) -> Path`
- `compare_pdfs(reference_pdf, candidate_pdf) -> ComparisonResult`
- `generate_corpus(seed, count) -> list[CorpusCase]`

## CLI

The standalone package should ship a lightweight CLI.

Initial subcommands:

- `armymemo render`
  - render source or PDF from `.Amd` or `MemoDoc`
- `armymemo compare`
  - compare a candidate PDF against a baseline PDF
- `armymemo corpus`
  - generate a seeded regression corpus

This is a convenience layer around the library API, not a separate product surface.

## Rendering Architecture

### Overview

Pipeline:

1. Parse source text into `MemoDocument`
2. Render document into engine-specific source
3. Compile engine-specific source into PDF
4. Compare resulting PDF against baseline when running migration tests

### LaTeX renderer

The LaTeX renderer remains in the library only for baseline generation and regression comparison during the migration. It is not the long-term primary backend.

Responsibilities:

- accept `MemoDocument`
- emit stable LaTeX source using the packaged Army memo class
- compile to PDF when baseline generation is requested

### Typst renderer

The Typst renderer is the target backend for production library use.

Responsibilities:

- accept `MemoDocument`
- own Typst-specific escaping and layout rules
- produce Typst source without LaTeX assumptions leaking into the model
- compile through a managed Typst binary

### Inline formatting policy

The model stores plain memo text with lightweight markup markers. Renderers convert that text into their own inline syntax.

Supported inline features:

- bold
- italic
- underline
- highlighted / monospace text

The renderer layer, not the parser, owns escaping and final inline syntax mapping.

## Typst Distribution Strategy

### v1 target platforms

- macOS
- Linux

### v1 strategy

The package should attempt resolution in this order:

1. explicit `ARMYMEMO_TYPST_BIN`
2. `typst` found on `PATH`
3. cached auto-provisioned binary
4. download a pinned Typst release into a local cache

This provides a near-self-contained `pip install` story without forcing large bundled wheels in v1.

### Constraints

- Windows is deferred
- networkless environments must either have Typst installed already or pre-seed the cache
- pinned versioning matters because layout drift between Typst versions would invalidate regression baselines

## LaTeX-to-Typst Equivalence Strategy

### Canonical reference

Current LaTeX output is the baseline of record during migration.

The equivalence question is not:

- "does the Typst memo look reasonable?"

It is:

- "does the Typst PDF match the established LaTeX output closely enough that we can trust it as a drop-in rendering replacement?"

### Why AR 25-50 validation is not enough

Rule-based compliance checks are useful, but they do not prove renderer equivalence. Two PDFs can both be technically compliant while differing materially in line wrapping, vertical spacing, signature placement, or page breaks.

The migration gate therefore must be direct PDF layout comparison.

### Comparison metrics

The PDF comparison layer should extract:

- page count
- line text
- line x/y positions
- per-page content bounding boxes
- page assignment for each extracted line

The first version does not need full glyph-by-glyph image comparison, but it must be precise enough to catch:

- line wrap drift
- paragraph reflow
- indentation drift
- header/footer movement
- page break differences
- signature block placement differences

### Initial tolerances

Default tolerances for automated comparison:

- page count must match exactly
- normalized line text must match exactly
- line x-position tolerance: 2.0 pt
- line y-position tolerance: 2.0 pt
- page bounding box tolerance: 4.0 pt

These are starting tolerances, not permanent guarantees. Once Typst output converges, the thresholds should be tightened, especially for critical regions.

### Critical regions for stricter review

These areas matter more than generic body text:

- office symbol/date line
- route lines
- subject line
- first paragraph start
- continuation page header
- signature block
- enclosure/distro/cf block

If needed, the comparator can grow region-aware rules after the generic comparison layer proves useful.

## Regression Corpus

### Seed sources

The regression suite should combine:

- existing hand-written example memos
- a deterministic synthetic corpus generated from the new model

### Why deterministic generation matters

Random coverage is good for discovery but bad for debugging. The corpus generator must be seeded so any failure is reproducible from:

- seed
- case name
- renderer version
- Typst version

### Corpus coverage goals

Generated cases should vary:

- memo type
- recipient count
- subject length
- nested body depth
- paragraph length
- optional fields
- multi-page scenarios
- tables
- enclosures/distro/cf

## Packaging

### Short-term in this repo

- keep the current web app working
- add the standalone library as a separate package surface
- package the memo assets needed by both renderers

### Long-term target

Move the standalone library into its own repo once:

- the API is stable
- Typst rendering quality is acceptable
- the regression harness is trustworthy
- the web app integration strategy is settled

## Migration Plan

### Phase 1: Library boundary and proof of concept

- create `armymemo/` package
- define the neutral document model
- support `.Amd` and `MemoDoc`
- add LaTeX and Typst source renderers
- add Typst binary manager

### Phase 2: Baseline harness

- package LaTeX assets locally
- compile LaTeX baselines
- implement PDF extraction and comparison
- build seeded corpus generation

### Phase 3: Layout convergence

- iterate on Typst layout until the comparison suite passes consistently
- tighten tolerances where possible
- capture approved baselines for CI

### Phase 4: Repo split and app migration

- move the library into its own repo
- update the web app to consume the library as a dependency
- remove duplicated rendering logic from the app repo

## Acceptance Criteria

The standalone library is considered viable when all of the following are true:

- a fresh Python environment can install the package and use the API
- both `.Amd` and `MemoDoc` parse into the same document model
- Typst source generation works from the neutral model
- LaTeX baselines can be regenerated from the same model
- PDF comparison failures are specific and actionable
- curated examples pass equivalence checks
- seeded synthetic cases pass equivalence checks at agreed tolerances

## Current Open Risks

- Typst layout may require several iterations before it can match the established LaTeX output closely enough
- Typst version drift can invalidate layout assumptions
- PDF text extraction is not perfect and may need targeted heuristics for some edge cases
- table rendering is likely to be the least stable area during early migration

## Immediate Next Steps

1. Keep this document as the contract for the standalone library work
2. Align the current `armymemo/` proof of concept to the API and behavior described here
3. Add focused tests around parsing, Typst source generation, corpus determinism, and PDF comparison
4. Start generating paired LaTeX and Typst artifacts for the existing example memos

# Fixed Pipeline Refactor Spec

## Status

Accepted product direction for the next refactor phase.

This document defines the target shape of the product before code-level decomposition.
It is intentionally short, opinionated, and implementation-facing.

## Product decisions

### 1. WebView is removed

- `pywebview_*` is no longer part of the supported product surface.
- Future architecture is **CLI core + PySide GUI shell**.
- WebView-specific orchestration should not receive new work.

### 2. Main pipeline becomes fixed

The primary workflow is:

`DICOM -> segmentation -> CSV -> PNG`

with spine localization included as part of the normal workflow.

This means the product should no longer be framed as:

- segmentation first, then optionally draw
- segmentation with optional spine
- segmentation with many output mode combinations

Instead, the default clinical workflow is treated as the official workflow.

### 3. Fixed behavior in the main workflow

These behaviors should be considered built-in for the primary pipeline:

- CSV export: **always on**
- PNG overlay export: **always on**
- Spine localization / spine-related output: **always on**
- Fast mode: **off by default and removed from normal user flow**

The practical goal is to reduce branching, simplify testing, and make the product easier to explain clinically.

### 4. Still-configurable inputs

The following remain legitimate user-controlled inputs:

- DICOM case / root folder
- modality
- task
- slice range
- erosion iterations
- batch selection / retry / license handling
- compare inputs

### 5. Compare stays independent

AI-vs-manual comparison is still a formal feature, but it is not part of the fixed segmentation pipeline.

It remains a separate flow:

`AI mask + manual mask -> compare metrics`

## Architecture direction

## Core layers

### A. Pipeline core

Responsible for the fixed main workflow:

1. resolve case + modality + task
2. run segmentation
3. export CSV
4. export PNG
5. export spine-related outputs needed for localization
6. return a structured result / status object

### B. Compare core

Responsible only for comparison workflow.

### C. Batch orchestration

Responsible for applying the pipeline across many cases, preserving:

- per-case state
- retry behavior
- session logging
- license recovery
- error classification

### D. PySide GUI shell

Responsible only for:

- collecting inputs
- showing progress / logs / errors
- exposing batch controls
- exposing compare flow

The GUI should not become a second implementation of business logic.

## Responsibilities to remove or reduce

### Remove from product surface

- WebView runtime and WebView shell maintenance
- WebView-specific docs as active architecture guidance

### Reduce in code

- `auto_draw` as a product concept
- spine on/off branching in normal flow
- png on/off branching in normal flow
- fast mode branching in normal flow

## CLI contract direction

The CLI should evolve toward one official segmentation pipeline entry.

Expected direction:

- keep modality / task / range / erosion controls
- remove optional-output thinking from the main path
- make PNG generation part of normal completion semantics
- make spine handling part of normal completion semantics

Whether this is implemented as a single pipeline command or a small orchestrator calling lower-level modules is an implementation detail.
The important part is that the contract is fixed.

## Testing consequences

The refactor should deliberately shrink the test matrix.

We should stop multiplying cases across combinations like:

- spine on/off
- auto_draw on/off
- png on/off
- fast on/off

and focus on:

- pipeline success contract
- slice-range correctness
- CSV / PNG ordering consistency
- batch status and retry behavior
- license recovery
- compare correctness

## Suggested implementation order

1. lock the product contract in docs
2. remove WebView from active architecture docs and tooling scope
3. add code-quality / type-check / test baselines
4. simplify CLI contract
5. extract/clean pipeline orchestration
6. thin the PySide GUI
7. remove dead WebView code once no active references remain

## Not in scope for this document

This spec does not decide:

- exact module names
- whether `seg.py` stays as the top-level pipeline entry
- whether spine artifacts should keep current file names
- whether fast mode is completely deleted or retained as hidden developer-only escape hatch

Those are follow-up implementation decisions.

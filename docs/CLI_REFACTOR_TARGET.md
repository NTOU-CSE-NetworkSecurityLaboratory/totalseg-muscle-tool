# CLI Refactor Target

## Purpose

This document defines the target shape of the non-GUI pipeline after the CLI refactor.

The goal is not to change clinician-facing behavior. The goal is to make the CLI pipeline
easier to reason about, easier to test, and safer to evolve while preserving the current
output contract.

## Product Contract

The official product workflow is fixed:

`DICOM -> segmentation -> spine -> CSV -> PNG`

This means:

- CSV is mandatory.
- PNG is mandatory.
- Spine output is mandatory.
- Fast mode is not part of the normal product workflow.

These are not optional side features. They are built-in stages of the main pipeline.

## Execution Modes

The CLI supports two execution modes, but they do not have equal product status.

### 1. `full`

This is the only official, default, clinician-facing pipeline entry.

It must always perform:

1. primary segmentation
2. spine segmentation
3. CSV generation
4. PNG generation

The GUI should only use this mode.

### 2. `reuse_segmentation`

This is an auxiliary engineering and recovery mode.

It exists to:

- skip the expensive segmentation stage
- validate CSV and PNG logic
- rebuild downstream outputs from existing segmentation folders

It should be supported as a real mode, but it is not the main clinician-facing workflow.

## Design Rules

### Fixed pipeline behavior

- The normal product path must not expose spine on/off.
- The normal product path must not expose PNG on/off.
- The normal product path must not expose fast on/off.
- Legacy flags may exist temporarily for compatibility, but they are normalized internally.

### Output parity

- The refactor must preserve the current output contract.
- The main comparison baseline is the current official workflow behavior.
- Known behavior quirks are preserved first, then fixed later in separate work.

### CSV row direction

This is a hard requirement.

- CSV row 1 must correspond to the head side.
- CSV row ordering is a clinical convention, not just raw array order.
- The refactor must keep this rule explicit and protected by tests.

In other words, the CSV export layer must preserve the current slice-direction contract.

## Target Module Roles

### `python/seg.py`

Thin CLI entrypoint only.

Responsibilities:

- parse CLI args
- choose execution mode
- build request object
- call the fixed pipeline
- emit logs and exit status

It should not continue to own most business logic.

### `python/core/fixed_pipeline.py`

The main non-GUI pipeline orchestrator.

Responsibilities:

- run the official `full` workflow
- run the auxiliary `reuse_segmentation` workflow
- sequence segmentation, spine, CSV, and PNG stages

### `python/core/pipeline_request.py`

Normalize external CLI arguments into an internal request object.

Legitimate inputs include:

- dicom path
- output root
- task
- modality
- slice range
- erosion iterations
- execution mode

### `python/core/output_contract.py`

Centralize output naming and path rules.

Responsibilities:

- output base resolution
- segmentation folder naming
- spine folder naming
- CSV path naming
- PNG path naming

### `python/core/segmentation_service.py`

Run segmentation-related work only.

Responsibilities:

- primary segmentation
- spine segmentation

### `python/core/postprocess_service.py`

Run downstream output generation from existing segmentation artifacts.

Responsibilities:

- rebuild CSV
- rebuild PNG

### `python/core/csv_service.py`

Own CSV generation logic.

Responsibilities:

- slice area export
- HU export
- HU std export
- summary export
- statistics merge
- left/right merge rules
- CSV row direction contract

### `python/core/png_service.py`

Own PNG generation logic.

### `python/core/image_io.py`

Centralize image loading and resampling helpers.

Responsibilities:

- DICOM reading
- mask reading
- ASCII fallback handling
- resampler helpers

### `python/core/mask_metrics.py`

Pure data processing and metric calculation.

Responsibilities:

- slice area
- volume
- erosion-based HU
- HU std

## Done Criteria

The CLI refactor is not done until all of the following are true:

- `seg.py` is a thin entrypoint.
- The fixed pipeline is the central implementation.
- `full` remains the only official default entry.
- `reuse_segmentation` exists as an auxiliary real mode.
- CSV, PNG, and spine remain built-in stages of the official workflow.
- CSV row 1 still corresponds to the head side.
- The pipeline output contract remains stable for the same case.
- GUI does not need architectural rework and continues to use the `full` path.

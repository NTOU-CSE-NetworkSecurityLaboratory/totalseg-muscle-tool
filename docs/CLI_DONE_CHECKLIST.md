# CLI Done Checklist

This checklist defines when the non-GUI pipeline refactor is considered complete.

## Required Gates

### 1. Output parity

The refactor is not done unless the fixed pipeline preserves the current output contract.

Required comparison targets:

- primary CSV
- spine CSV
- `png/`
- `png_eroded/`

Required behavior:

- identical output for the same baseline case
- `row 1` in CSV remains the head side
- reversed slice order is corrected from spine evidence

### 2. Complexity reduction

The refactor is not done unless the code shape is simpler than the legacy CLI.

Required indicators:

- `python/seg.py` remains a thin entrypoint
- request normalization, path rules, orchestration, CSV export, and metrics are no longer all mixed together
- product-level dead branches are removed from the main path

Normal-path decisions that must no longer exist as real product branches:

- CSV on/off
- PNG on/off
- spine on/off
- fast on/off

Allowed remaining decisions:

- `full` vs `reuse_segmentation`
- CT vs MRI
- slice range present vs absent
- explicit error handling

### 3. Risk reduction

The refactor is not done unless behavior-critical rules are centralized and protected.

Required indicators:

- CSV direction logic lives in one place
- spine evidence is the authority for cranial/caudal export order
- fixed pipeline rules are documented
- tests protect the pipeline contract and orientation behavior

## Current Structural Evidence

The legacy `main` branch had a large monolithic `python/seg.py`.

The refactor target is:

- `python/seg.py` as thin entrypoint
- `python/core/fixed_pipeline.py` as orchestrator
- `python/core/pipeline_request.py` for request normalization
- `python/core/output_contract.py` for output naming
- `python/core/csv_service.py` for CSV contract
- `python/core/mask_metrics.py` for pure calculations
- `python/core/image_io.py` for image loading helpers

## GUI Follow-up Rule

GUI work starts only after the CLI gates above are satisfied.

The GUI must continue to use only the official `full` mode.

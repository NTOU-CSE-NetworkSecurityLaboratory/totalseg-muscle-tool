# Refactor From Requirements, Not Legacy Script Shape

## Goal
Reframe this project as a **medical image case reporting pipeline**, not just a segmentation script.

Core outputs are product features, not side effects:
- segmentation masks
- `mask_abdominal_muscles.csv`
- `mask_spine_fast.csv`
- overlay PNGs

## Product Rules That Must Be Explicit

### 1. CSV direction is a product rule
- CSV row order must be **cranial -> caudal**
- `row 1 = head side / cranial`
- `last row = feet side / caudal`
- This must not be hidden as an unexplained `reverse()` in exporter code
- Direction should become an explicit rule/module/test target

### 2. Slice processing order vs exported row order are different concepts
- Internal array index order is an implementation detail
- Exported CSV row order is a product/domain rule
- Code should map internal slice order to required output order explicitly

### 3. Spine is domain evidence, not a hack
- Spine labels can be used to validate cranial/caudal ordering
- Long term, orientation should be validated with anatomical or image-orientation evidence
- Do not rely on a magic final reversal without explanation

## Desired Architecture

### A. Case loading
Responsibilities:
- load DICOM series / volume input
- detect spacing, slice count, orientation metadata
- expose a normalized case-volume object

### B. Segmentation service
Responsibilities:
- run model(s)
- produce masks/statistics artifacts
- do not decide CSV format or row order

### C. Measurement layer
Responsibilities:
- compute per-slice area
- compute HU mean/std
- compute summary volume/pixelcount
- return internal metrics indexed by internal slice order

### D. Ordering layer
Responsibilities:
- define exported order (`cranial_to_caudal`)
- map internal slice indices to product row order
- optionally validate ordering using spine/anatomical evidence

### E. Exporters
Responsibilities:
- write CSV/PNG/JSON from already-ordered data
- never silently redefine product semantics

## Required Tests

### 1. Golden-output test
For a representative case, compare old/new outputs for:
- `mask_abdominal_muscles.csv`
- `mask_spine_fast.csv`
- `statistics.json`
- key PNG naming/content if relevant

### 2. Directionality test
Explicitly verify:
- row 1 is cranial
- final row is caudal
- for spine output, early rows should align with higher vertebral levels than later rows

### 3. Pipeline contract test
Verify:
- which tasks run for CT/MRI
- which outputs are always produced
- naming/location contract

### 4. Regenerate-only test
Verify a mode that reuses existing segmentations can regenerate outputs without rerunning models and without unrelated side effects causing false failure.

## Immediate Practical Direction
1. Preserve legacy-equivalent outputs first
2. Make hidden product rules explicit
3. Separate segmentation / measurement / ordering / export
4. Only then continue deeper refactor work

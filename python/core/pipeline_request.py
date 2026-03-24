from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FIXED_PIPELINE_SPINE = 1
FIXED_PIPELINE_FAST = 0
FIXED_PIPELINE_AUTO_DRAW = 1
EXECUTION_MODE_FULL = "full"
EXECUTION_MODE_REUSE_SEGMENTATION = "reuse_segmentation"


@dataclass(frozen=True)
class PipelineRequest:
    dicom_path: Path
    output_root: Path | None
    task: str
    modality: str
    erosion_iters: int
    slice_start: int | None
    slice_end: int | None
    execution_mode: str
    spine: int = FIXED_PIPELINE_SPINE
    fast: int = FIXED_PIPELINE_FAST
    auto_draw: int = FIXED_PIPELINE_AUTO_DRAW


@dataclass(frozen=True)
class LegacyFlagState:
    requested: dict[str, int]
    normalized: dict[str, int]


def normalize_legacy_flags(
    *,
    spine: int,
    fast: int,
    auto_draw: int,
) -> LegacyFlagState:
    requested = {
        "spine": int(spine),
        "fast": int(fast),
        "auto_draw": int(auto_draw),
    }
    normalized = {
        "spine": FIXED_PIPELINE_SPINE,
        "fast": FIXED_PIPELINE_FAST,
        "auto_draw": FIXED_PIPELINE_AUTO_DRAW,
    }
    return LegacyFlagState(requested=requested, normalized=normalized)


def request_from_args(args) -> tuple[PipelineRequest, LegacyFlagState]:
    legacy_flags = normalize_legacy_flags(
        spine=args.spine,
        fast=args.fast,
        auto_draw=args.auto_draw,
    )
    request = PipelineRequest(
        dicom_path=Path(args.dicom),
        output_root=Path(args.out) if args.out else None,
        task=args.task,
        modality=args.modality,
        erosion_iters=args.erosion_iters,
        slice_start=args.slice_start,
        slice_end=args.slice_end,
        execution_mode=(
            EXECUTION_MODE_REUSE_SEGMENTATION
            if bool(args.skip_segmentation)
            else EXECUTION_MODE_FULL
        ),
        spine=legacy_flags.normalized["spine"],
        fast=legacy_flags.normalized["fast"],
        auto_draw=legacy_flags.normalized["auto_draw"],
    )
    return request, legacy_flags

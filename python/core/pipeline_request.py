from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SegmentRequest:
    """步驟一：分割請求。"""
    dicom_path: Path
    output_root: Path | None
    task: str
    modality: str


@dataclass(frozen=True)
class ExportRequest:
    """步驟二：CSV + PNG 輸出請求。"""
    dicom_path: Path
    output_root: Path | None
    task: str
    erosion_iters: int
    slice_start: int | None
    slice_end: int | None
    hu_min: float | None
    hu_max: float | None


def segment_request_from_args(args) -> SegmentRequest:
    return SegmentRequest(
        dicom_path=Path(args.dicom),
        output_root=Path(args.out) if args.out else None,
        task=args.task,
        modality=args.modality,
    )


def export_request_from_args(args) -> ExportRequest:
    return ExportRequest(
        dicom_path=Path(args.dicom),
        output_root=Path(args.out) if args.out else None,
        task=args.task,
        erosion_iters=args.erosion_iters,
        slice_start=args.slice_start,
        slice_end=args.slice_end,
        hu_min=args.hu_min,
        hu_max=args.hu_max,
    )

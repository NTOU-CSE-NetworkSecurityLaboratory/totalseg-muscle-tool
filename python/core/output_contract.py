from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelinePaths:
    output_base: Path
    primary_seg_dir: Path
    primary_csv: Path
    spine_seg_dir: Path | None
    spine_csv: Path | None


def resolve_output_base(dicom_path: Path, out: Path | None) -> Path:
    return (out if out else dicom_path.parent) / f"{dicom_path.name}_output"


def build_pipeline_paths(*, dicom_path: Path, output_root: Path | None, task: str, export_spine: bool):
    output_base = resolve_output_base(dicom_path, output_root)
    primary_seg_dir = output_base / f"segmentation_{task}"
    primary_csv = output_base / f"mask_{task}.csv"
    if export_spine:
        spine_seg_dir = output_base / "segmentation_spine_fast"
        spine_csv = output_base / "mask_spine_fast.csv"
    else:
        spine_seg_dir = None
        spine_csv = None
    return PipelinePaths(
        output_base=output_base,
        primary_seg_dir=primary_seg_dir,
        primary_csv=primary_csv,
        spine_seg_dir=spine_seg_dir,
        spine_csv=spine_csv,
    )

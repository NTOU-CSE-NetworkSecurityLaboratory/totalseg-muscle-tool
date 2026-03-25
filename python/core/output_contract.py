from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SegmentPaths:
    """步驟一（分割）產生與使用的路徑。"""
    output_base: Path
    primary_seg_dir: Path
    spine_seg_dir: Path
    spine_json: Path


@dataclass(frozen=True)
class ExportPaths:
    """步驟二（CSV + PNG 輸出）使用的路徑。"""
    output_base: Path
    primary_seg_dir: Path
    spine_json: Path
    volume_csv: Path
    hu_csv: Path
    png_dir: Path
    png_eroded_dir: Path
    png_nolabel_dir: Path
    png_eroded_nolabel_dir: Path


def resolve_output_base(dicom_path: Path, out: Path | None) -> Path:
    return (out if out else dicom_path.parent) / f"{dicom_path.name}_output"


def build_segment_paths(*, dicom_path: Path, output_root: Path | None, task: str) -> SegmentPaths:
    output_base = resolve_output_base(dicom_path, output_root)
    return SegmentPaths(
        output_base=output_base,
        primary_seg_dir=output_base / f"segmentation_{task}",
        spine_seg_dir=output_base / "segmentation_spine_fast",
        spine_json=output_base / "spine.json",
    )


def build_export_paths(*, dicom_path: Path, output_root: Path | None, task: str) -> ExportPaths:
    output_base = resolve_output_base(dicom_path, output_root)
    primary_seg_dir = output_base / f"segmentation_{task}"
    return ExportPaths(
        output_base=output_base,
        primary_seg_dir=primary_seg_dir,
        spine_json=output_base / "spine.json",
        volume_csv=primary_seg_dir / f"volume_{task}.csv",
        hu_csv=primary_seg_dir / f"hu_{task}.csv",
        png_dir=primary_seg_dir / "png",
        png_eroded_dir=primary_seg_dir / "png_eroded",
        png_nolabel_dir=primary_seg_dir / "png_nolabel",
        png_eroded_nolabel_dir=primary_seg_dir / "png_eroded_nolabel",
    )

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    import SimpleITK as sitk
except ImportError:
    sitk = None


def filter_tasks_by_modality(tasks: list[str], modality: str) -> list[str]:
    if str(modality).upper() == "MRI":
        return [t for t in tasks if t.endswith("_mr")]
    return [t for t in tasks if not t.endswith("_mr")]


def folder_numeric_sort_key(path_value: str | Path):
    parts = []
    for token in re.split(r"(\d+)", str(path_value).lower()):
        parts.append(int(token) if token.isdigit() else token)
    return parts


def has_dicom_files(folder: Path) -> bool:
    if any(folder.glob("*.dcm")):
        return True
    if sitk:
        try:
            reader = sitk.ImageSeriesReader()
            names = reader.GetGDCMSeriesFileNames(str(folder))
            return bool(names)
        except Exception:
            return False
    return False


def get_dicom_slice_count(folder: Path) -> int | None:
    if sitk:
        try:
            reader = sitk.ImageSeriesReader()
            names = reader.GetGDCMSeriesFileNames(str(folder))
            if names:
                return len(names)
        except Exception:
            pass
    files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        return None
    dcm_count = len([f for f in files if f.suffix.lower() == ".dcm"])
    return dcm_count if dcm_count > 0 else len(files)


def normalize_slice_range(
    start_str: str | None,
    end_str: str | None,
    slice_count: int | None,
) -> tuple[int | None, int | None, str | None]:
    start_text = (start_str or "1").strip()
    end_text = (end_str or "").strip()
    if not start_text.isdigit() or (end_text and not end_text.isdigit()):
        return None, None, "Slice range must be integer values"
    start_val = int(start_text)
    if start_val < 1:
        return None, None, "Slice start must be >= 1"
    end_val = int(end_text) if end_text else None
    if end_val is not None and start_val > end_val:
        return None, None, "Slice start must be <= slice end"
    if slice_count and slice_count > 0:
        if start_val > slice_count:
            return None, None, f"Slice start {start_val} exceeds case slices {slice_count}"
        if end_val is None:
            end_val = slice_count
        elif end_val > slice_count:
            end_val = slice_count
        if start_val > end_val:
            return None, None, "Slice range is invalid after clamping"
    return start_val, end_val, None


@dataclass
class CaseItem:
    folder: Path
    label: str
    slice_count: int | None


_SCAN_SKIP = ("_output", "TotalSeg_Backend")


def scan_dicom_cases(root_path: str | Path) -> list[CaseItem]:
    root = Path(root_path)
    valid_folders: list[Path] = []
    if has_dicom_files(root):
        valid_folders.append(root)
    else:
        for dirpath, dirs, _ in os.walk(root, topdown=True):
            dirs[:] = [d for d in dirs if not any(s in d for s in _SCAN_SKIP)]
            p = Path(dirpath)
            if p == root:
                continue
            if has_dicom_files(p):
                valid_folders.append(p)
    valid_folders.sort(key=folder_numeric_sort_key)

    items: list[CaseItem] = []
    for folder in valid_folders:
        count = get_dicom_slice_count(folder)
        try:
            display = str(folder.relative_to(root)) if folder != root else folder.name
        except ValueError:
            display = str(folder)
        items.append(CaseItem(folder=folder, label=display, slice_count=count))
    return items



def build_step1_command(
    *,
    dicom_path: str,
    out_path: str,
    task: str,
    modality: str,
) -> list[str]:
    return [
        "run", "--no-sync", "python", "-u", "seg.py",
        "--dicom", str(dicom_path),
        "--out", str(out_path),
        "--task", str(task),
        "--modality", str(modality),
    ]


def build_step2_command(
    *,
    dicom_path: str,
    out_path: str,
    task: str,
    erosion_iters: int | str = 2,
    slice_start: int | None = None,
    slice_end: int | None = None,
    hu_min: float | None = None,
    hu_max: float | None = None,
) -> list[str]:
    cmd = [
        "run", "--no-sync", "python", "-u", "export.py",
        "--dicom", str(dicom_path),
        "--out", str(out_path),
        "--task", str(task),
        "--erosion_iters", str(erosion_iters),
    ]
    if slice_start is not None:
        cmd.extend(["--slice_start", str(slice_start)])
    if slice_end is not None:
        cmd.extend(["--slice_end", str(slice_end)])
    if hu_min is not None:
        cmd.extend(["--hu_min", str(hu_min)])
    if hu_max is not None:
        cmd.extend(["--hu_max", str(hu_max)])
    return cmd


def compare_masks(ai_path: str, manual_path: str) -> dict[str, Any]:
    if not sitk:
        raise RuntimeError("SimpleITK is not installed")

    ai_img = sitk.ReadImage(ai_path)
    manual_img = sitk.ReadImage(manual_path)
    if ai_img.GetSize() != manual_img.GetSize() or ai_img.GetSpacing() != manual_img.GetSpacing():
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(manual_img)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        ai_img = resampler.Execute(ai_img)

    ai_arr = sitk.GetArrayFromImage(ai_img) > 0
    manual_arr = sitk.GetArrayFromImage(manual_img) > 0
    spacing = manual_img.GetSpacing()

    slice_idx = -1
    for i in range(manual_arr.shape[0]):
        if np.any(manual_arr[i]):
            slice_idx = i
            break
    if slice_idx == -1:
        raise ValueError("Manual mask has no positive slice")

    ai_slice = ai_arr[slice_idx]
    manual_slice = manual_arr[slice_idx]
    intersection = np.logical_and(ai_slice, manual_slice).sum()
    total = ai_slice.sum() + manual_slice.sum()
    dice = (2.0 * intersection / total) if total > 0 else 0.0

    pixel_cm2 = (spacing[0] * spacing[1]) / 100.0
    ai_area = float(ai_slice.sum() * pixel_cm2)
    manual_area = float(manual_slice.sum() * pixel_cm2)
    quality = "Excellent" if dice >= 0.9 else "Good" if dice >= 0.8 else "Needs Review"
    return {
        "slice_index_1based": slice_idx + 1,
        "dice": float(dice),
        "ai_area_cm2": ai_area,
        "manual_area_cm2": manual_area,
        "quality": quality,
    }

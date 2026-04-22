from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any


def is_ascii_path(path: str | Path) -> bool:
    return str(path).isascii()


def read_image_with_ascii_fallback(
    image_path: str | Path,
    *,
    sitk_module: Any,
    log_info,
):
    image_path = Path(image_path)
    try:
        return sitk_module.ReadImage(str(image_path))
    except RuntimeError as first_error:
        if is_ascii_path(image_path):
            log_info(f"[ERROR] Failed to read mask: {image_path} (ASCII path, no fallback).")
            raise

        exists = image_path.exists()
        size = image_path.stat().st_size if exists else -1
        log_info(
            f"[WARN] ReadImage failed on non-ASCII path. "
            f"path={image_path} exists={exists} size={size} bytes. "
            "Trying ASCII temp fallback..."
        )
        with tempfile.TemporaryDirectory(prefix="sitk_ascii_") as tmp_dir:
            tmp_path = Path(tmp_dir) / image_path.name
            shutil.copy2(image_path, tmp_path)
            try:
                return sitk_module.ReadImage(str(tmp_path))
            except RuntimeError:
                log_info(f"[ERROR] Fallback read also failed for: {image_path}")
                raise first_error


def read_ct_via_dicom2nifti(
    dicom_dir: str | Path,
    *,
    sitk_module: Any,
    log_info,
):
    """Read DICOM CT using dicom2nifti so geometry matches totalsegmentator masks.

    totalsegmentator preprocesses DICOM with dicom2nifti (reorient_nifti=True) and
    writes masks in the resulting LAS/RAS space. If Step 2 reads the same DICOM
    via sitk.ImageSeriesReader, scanners with non-identity Z direction (feet-first
    or reversed-Z acquisitions) produce a CT image whose origin/direction does not
    match the mask, and resampling silently yields all-zero arrays inside the mask.
    """
    import dicom2nifti  # noqa: PLC0415

    dicom_dir = Path(dicom_dir)
    with tempfile.TemporaryDirectory(prefix="ct_d2n_") as td:
        tmp_nii = Path(td) / "ct.nii.gz"
        try:
            dicom2nifti.dicom_series_to_nifti(str(dicom_dir), str(tmp_nii), reorient_nifti=True)
        except Exception as exc:
            log_info(f"[ERROR] dicom2nifti failed on {dicom_dir}: {exc}")
            raise
        ct = sitk_module.ReadImage(str(tmp_nii))
    return sitk_module.Cast(ct, sitk_module.sitkInt16)

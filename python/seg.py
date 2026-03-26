"""步驟一 CLI：DICOM → segmentation + spine.json"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import SimpleITK as sitk
from totalsegmentator.python_api import totalsegmentator

from core.app_version import read_local_app_version
from core.fixed_pipeline import execute_step1_segmentation
from core.output_contract import build_segment_paths
from core.pipeline_request import segment_request_from_args

APP_VERSION = read_local_app_version()


def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_ct_image(dicom_path: Path):
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(dicom_path))
    if not files:
        raise RuntimeError(f"No DICOM found in: {dicom_path}")
    reader.SetFileNames(files)
    return sitk.Cast(reader.Execute(), sitk.sitkInt16)


def run_task(dicom_path, out_dir, task, fast=False, roi_subset=None):
    params = dict(
        input=str(dicom_path),
        output=str(out_dir),
        task=task,
        fast=fast,
        statistics=True,
        verbose=True,
        statistics_exclude_masks_at_border=False,
    )
    if roi_subset:
        params["roi_subset"] = roi_subset

    t0 = time.perf_counter()
    log_info(f"totalsegmentator started (task={task}, fast={fast})")
    totalsegmentator(**params)
    log_info(f"totalsegmentator completed in {time.perf_counter() - t0:.2f}s (task={task})")


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 1: Segmentation v{APP_VERSION}"
    )
    parser.add_argument("--dicom", type=str, required=True, help="DICOM folder path")
    parser.add_argument("--out", type=str, default=None, help="Output root folder")
    parser.add_argument(
        "--task", type=str, default="abdominal_muscles", help="Segmentation task name"
    )
    parser.add_argument(
        "--modality", type=str, default="CT", help="Imaging modality (CT or MRI)"
    )

    args = parser.parse_args()
    request = segment_request_from_args(args)
    paths = build_segment_paths(
        dicom_path=request.dicom_path,
        output_root=request.output_root,
        task=request.task,
    )

    t0 = time.perf_counter()
    log_info(
        f"Step 1 started (dicom={request.dicom_path}, task={request.task}, "
        f"modality={request.modality}, output={paths.output_base})"
    )

    execute_step1_segmentation(
        request=request,
        paths=paths,
        log_info=log_info,
        run_task=run_task,
        load_ct_image=load_ct_image,
    )

    log_info(f"Step 1 completed in {time.perf_counter() - t0:.2f}s")


if __name__ == "__main__":
    main()

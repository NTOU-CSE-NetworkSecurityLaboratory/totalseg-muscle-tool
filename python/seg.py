import argparse
import os
import subprocess
import time
from datetime import datetime

import SimpleITK as sitk
from totalsegmentator.python_api import totalsegmentator

from auto_draw_cmd import build_auto_draw_command
from core.app_version import read_local_app_version
from core.csv_service import (
    export_areas_and_volumes_to_csv as export_areas_and_volumes_to_csv_impl,
)
from core.csv_service import (
    merge_bilateral_hu_data as merge_bilateral_hu_data_impl,
)
from core.csv_service import (
    merge_bilateral_std_data as merge_bilateral_std_data_impl,
)
from core.csv_service import (
    merge_statistics_to_csv as merge_statistics_to_csv_impl,
)
from core.fixed_pipeline import (
    FIXED_PIPELINE_AUTO_DRAW,
    FIXED_PIPELINE_FAST,
    FIXED_PIPELINE_SPINE,
    build_pipeline_paths,
    execute_fixed_pipeline,
    normalize_legacy_flags,
    request_from_args,
)
from core.image_io import read_image_with_ascii_fallback as read_image_with_ascii_fallback_impl
from core.mask_metrics import (
    calculate_slice_hu_with_erosion as calculate_slice_hu_with_erosion_impl,
)
from core.mask_metrics import (
    get_mask_area_volume_and_hu as get_mask_area_volume_and_hu_impl,
)

VERTEBRAE_LABELS = (
    [f"vertebrae_C{i}" for i in range(1, 8)]
    + [f"vertebrae_T{i}" for i in range(1, 13)]
    + [f"vertebrae_L{i}" for i in range(1, 6)]
)
APP_VERSION = read_local_app_version()


def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def apply_fixed_pipeline_defaults(args):
    legacy_flags = normalize_legacy_flags(
        spine=args.spine,
        fast=args.fast,
        auto_draw=args.auto_draw,
    )
    args.spine = legacy_flags.normalized["spine"]
    args.fast = legacy_flags.normalized["fast"]
    args.auto_draw = legacy_flags.normalized["auto_draw"]
    return legacy_flags.requested


def read_image_with_ascii_fallback(image_path):
    return read_image_with_ascii_fallback_impl(
        image_path,
        sitk_module=sitk,
        log_info=log_info,
    )


def calculate_slice_hu_with_erosion(slice_mask, slice_ct, erosion_iters=2):
    return calculate_slice_hu_with_erosion_impl(slice_mask, slice_ct, erosion_iters)


def get_mask_area_volume_and_hu(
    nii_path, ct_arr, spacing, resampler, erosion_iters=2, slice_start=None, slice_end=None
):
    return get_mask_area_volume_and_hu_impl(
        nii_path,
        ct_arr,
        spacing,
        resampler,
        sitk_module=sitk,
        image_reader=read_image_with_ascii_fallback,
        erosion_iters=erosion_iters,
        slice_start=slice_start,
        slice_end=slice_end,
    )


def merge_bilateral_hu_data(area_results, hu_results):
    return merge_bilateral_hu_data_impl(area_results, hu_results)


def merge_bilateral_std_data(area_results, hu_results, std_results):
    return merge_bilateral_std_data_impl(area_results, hu_results, std_results)


def export_areas_and_volumes_to_csv(
    mask_dir, output_csv, dicom_dir, erosion_iters=2, slice_start=None, slice_end=None
):
    return export_areas_and_volumes_to_csv_impl(
        mask_dir,
        output_csv,
        dicom_dir,
        sitk_module=sitk,
        listdir=os.listdir,
        load_mask_metrics=get_mask_area_volume_and_hu,
        image_reader=read_image_with_ascii_fallback,
        log_info=log_info,
        erosion_iters=erosion_iters,
        slice_start=slice_start,
        slice_end=slice_end,
    )


def merge_statistics_to_csv(mask_dir, output_csv):
    return merge_statistics_to_csv_impl(
        mask_dir,
        output_csv,
        log_info=log_info,
    )


def run_task(dicom_path, out_dir, task, fast=False, roi_subset=None):
    """
    執行 TotalSegmentator 分割任務
    """
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
    log_info(
        "Stage: totalsegmentator started "
        f"(task={task}, fast={fast}, out_dir={out_dir}, roi_subset={'yes' if roi_subset else 'no'})"
    )
    totalsegmentator(**params)
    log_info(
        f"Stage: totalsegmentator completed in {time.perf_counter()-t0:.2f}s "
        f"(task={task}, out_dir={out_dir})"
    )


def run_draw_command(draw_cmd, *, check):
    draw_t0 = time.perf_counter()
    log_info("Stage: auto_draw started")
    subprocess.run(draw_cmd, check=check)
    log_info(f"Stage: auto_draw completed in {time.perf_counter()-draw_t0:.2f}s")



def main():
    parser = argparse.ArgumentParser(
        description=f"Segmentation fixed pipeline v{APP_VERSION}"
    )
    parser.add_argument("--dicom", type=str, default="test", help="DICOM folder path")
    parser.add_argument("--out", type=str, default=None, help="Output folder")
    parser.add_argument(
        "--task", type=str, default="abdominal_muscles", help="Segmentation task name"
    )
    parser.add_argument(
        "--spine", type=int, default=0, help="Legacy compatibility flag; fixed pipeline always enables spine"
    )
    parser.add_argument(
        "--fast", type=int, default=0, help="Legacy compatibility flag; fixed pipeline always disables fast"
    )
    parser.add_argument(
        "--auto_draw",
        type=int,
        default=0,
        help="Legacy compatibility flag; fixed pipeline always exports PNG",
    )
    parser.add_argument(
        "--erosion_iters",
        type=int,
        default=2,
        help="Erosion iterations for HU calculation (default: 2)",
    )
    parser.add_argument("--modality", type=str, default="CT", help="Imaging modality (CT or MRI)")
    parser.add_argument("--slice_start", type=int, default=None, help="Start slice (1-indexed)")
    parser.add_argument("--slice_end", type=int, default=None, help="End slice (1-indexed)")
    parser.add_argument(
        "--skip_segmentation",
        action="store_true",
        help="Auxiliary mode: reuse existing segmentation folders and regenerate CSV/PNG outputs only",
    )

    args = parser.parse_args()
    request, legacy_flags = request_from_args(args)
    pipeline_t0 = time.perf_counter()

    if legacy_flags.requested != {
        "spine": FIXED_PIPELINE_SPINE,
        "fast": FIXED_PIPELINE_FAST,
        "auto_draw": FIXED_PIPELINE_AUTO_DRAW,
    }:
        log_info(
            "Fixed pipeline active: overriding requested flags "
            f"from {legacy_flags.requested} to {legacy_flags.normalized}"
        )

    paths = build_pipeline_paths(request)
    log_info(
        "Pipeline started "
        f"(dicom={request.dicom_path}, output_base={paths.output_base}, task={request.task}, "
        f"spine={request.spine}, fast={request.fast}, auto_draw={request.auto_draw}, "
        f"erosion_iters={request.erosion_iters}, modality={request.modality}, "
        f"range={request.slice_start}-{request.slice_end})"
    )

    execute_fixed_pipeline(
        request=request,
        paths=paths,
        log_info=log_info,
        run_task=run_task,
        export_csv=export_areas_and_volumes_to_csv,
        merge_statistics=merge_statistics_to_csv,
        build_auto_draw_command=build_auto_draw_command,
        run_subprocess=run_draw_command,
        vertebrae_labels=VERTEBRAE_LABELS,
    )

    log_info(f"Pipeline completed in {time.perf_counter()-pipeline_t0:.2f}s")


if __name__ == "__main__":
    main()

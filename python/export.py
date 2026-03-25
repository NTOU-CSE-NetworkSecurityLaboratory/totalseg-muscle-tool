"""步驟二 CLI：segmentation → volume CSV + HU CSV + PNG"""
import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import SimpleITK as sitk

from core.app_version import read_local_app_version
from core.csv_service import export_csvs as export_csvs_impl
from core.fixed_pipeline import execute_step2_export
from core.image_io import read_image_with_ascii_fallback as read_image_impl
from core.mask_metrics import get_mask_area_volume_and_hu as get_mask_metrics_impl
from core.output_contract import build_export_paths
from core.pipeline_request import ExportRequest, export_request_from_args

APP_VERSION = read_local_app_version()


def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def read_image(path):
    return read_image_impl(path, sitk_module=sitk, log_info=log_info)


def make_load_mask_metrics(erosion_iters, slice_start, slice_end, hu_min, hu_max):
    """回傳已綁定參數的 mask metrics 函式，供 export_csvs 使用。"""
    def _load(nii_path, ct_arr, spacing, resampler, *_args, **_kwargs):
        return get_mask_metrics_impl(
            nii_path,
            ct_arr,
            spacing,
            resampler,
            sitk_module=sitk,
            image_reader=read_image,
            erosion_iters=erosion_iters,
            slice_start=slice_start,
            slice_end=slice_end,
            hu_min=hu_min,
            hu_max=hu_max,
        )
    return _load


def make_export_csvs(request: ExportRequest):
    load_mask_metrics = make_load_mask_metrics(
        request.erosion_iters,
        request.slice_start,
        request.slice_end,
        request.hu_min,
        request.hu_max,
    )

    def _export(mask_dir, volume_csv, hu_csv, dicom_dir, spine_json_path,
                erosion_iters, slice_start, slice_end, hu_min, hu_max,
                write_volume, write_hu):
        export_csvs_impl(
            mask_dir,
            volume_csv,
            hu_csv,
            dicom_dir,
            spine_json_path,
            sitk_module=sitk,
            listdir=os.listdir,
            load_mask_metrics=load_mask_metrics,
            image_reader=read_image,
            log_info=log_info,
            erosion_iters=erosion_iters,
            slice_start=slice_start,
            slice_end=slice_end,
            hu_min=hu_min,
            hu_max=hu_max,
            write_volume=write_volume,
            write_hu=write_hu,
        )
    return _export


def run_png(dicom_dir, png_dir, png_eroded_dir, png_nolabel_dir,
            png_eroded_nolabel_dir, mask_dir, spine_json_path,
            slice_start, slice_end, erosion_iters):
    import draw  # noqa: PLC0415
    draw.dicom_to_overlay_png(
        Path(dicom_dir),
        Path(png_dir) if png_dir is not None else None,
        eroded_out_dir=Path(png_eroded_dir) if png_eroded_dir is not None else None,
        nolabel_out_dir=Path(png_nolabel_dir) if png_nolabel_dir is not None else None,
        eroded_nolabel_out_dir=(
            Path(png_eroded_nolabel_dir) if png_eroded_nolabel_dir is not None else None
        ),
        masks_dir=Path(mask_dir),
        spine_json=Path(spine_json_path),
        erosion_iters=erosion_iters,
        slice_start=slice_start,
        slice_end=slice_end,
    )


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 2: Export CSV + PNG v{APP_VERSION}"
    )
    parser.add_argument("--dicom", type=str, required=True, help="DICOM folder path")
    parser.add_argument("--out", type=str, default=None, help="Output root folder")
    parser.add_argument(
        "--task", type=str, default="abdominal_muscles", help="Segmentation task name"
    )
    parser.add_argument(
        "--erosion_iters", type=int, default=2,
        help="Erosion iterations for HU calculation (default: 2)"
    )
    parser.add_argument("--slice_start", type=int, default=None, help="Start slice (1-indexed)")
    parser.add_argument("--slice_end", type=int, default=None, help="End slice (1-indexed)")
    parser.add_argument(
        "--hu_min", type=float, default=None,
        help="HU threshold lower bound (blank = no filter)"
    )
    parser.add_argument(
        "--hu_max", type=float, default=None,
        help="HU threshold upper bound (blank = no filter)"
    )

    args = parser.parse_args()
    request = export_request_from_args(args)
    paths = build_export_paths(
        dicom_path=request.dicom_path,
        output_root=request.output_root,
        task=request.task,
    )

    t0 = time.perf_counter()
    log_info(
        f"Step 2 started (dicom={request.dicom_path}, task={request.task}, "
        f"erosion_iters={request.erosion_iters}, range={request.slice_start}-{request.slice_end}, "
        f"hu=[{request.hu_min}, {request.hu_max}], output={paths.output_base})"
    )

    execute_step2_export(
        request=request,
        paths=paths,
        log_info=log_info,
        export_csvs=make_export_csvs(request),
        run_png=run_png,
    )

    log_info(f"Step 2 completed in {time.perf_counter() - t0:.2f}s")


if __name__ == "__main__":
    main()

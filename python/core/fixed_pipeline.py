from __future__ import annotations

from collections.abc import Callable

from core.csv_service import build_spine_meta, write_spine_json
from core.output_contract import ExportPaths, SegmentPaths
from core.pipeline_request import ExportRequest, SegmentRequest

VERTEBRAE_LABELS = (
    [f"vertebrae_C{i}" for i in range(1, 8)]
    + [f"vertebrae_T{i}" for i in range(1, 13)]
    + [f"vertebrae_L{i}" for i in range(1, 6)]
)


def resolve_task_for_modality(task: str, modality: str) -> str:
    modality_upper = str(modality).upper()
    if modality_upper != "MRI":
        return task
    if task == "total":
        return "total_mr"
    if task == "spine":
        return "vertebrae_mr"
    return task


def resolve_spine_task(modality: str) -> str:
    return "vertebrae_mr" if str(modality).upper() == "MRI" else "total"


# ---------------------------------------------------------------------------
# 步驟一：分割（spine 先跑，已存在則跳過）
# ---------------------------------------------------------------------------

def execute_step1_segmentation(
    *,
    request: SegmentRequest,
    paths: SegmentPaths,
    log_info: Callable[[str], None],
    run_task: Callable[..., None],
) -> None:
    """
    執行 spine 分割（已存在則跳過），再執行主任務分割。
    spine.json 改在步驟二產生。
    """
    paths.output_base.mkdir(parents=True, exist_ok=True)
    paths.primary_seg_dir.mkdir(exist_ok=True)

    # --- spine 先跑 ---
    spine_task = resolve_spine_task(request.modality)
    spine_roi_subset = None if spine_task == "vertebrae_mr" else list(VERTEBRAE_LABELS)
    paths.spine_seg_dir.mkdir(exist_ok=True)
    log_info(f"Step 1: spine segmentation task={spine_task}")
    run_task(
        request.dicom_path,
        paths.spine_seg_dir,
        spine_task,
        fast=True,
        roi_subset=spine_roi_subset,
    )

    # --- 主任務分割 ---
    task_to_run = resolve_task_for_modality(request.task, request.modality)
    log_info(f"Step 1: primary segmentation task={task_to_run}, modality={request.modality}")
    run_task(request.dicom_path, paths.primary_seg_dir, task_to_run, fast=False)


# ---------------------------------------------------------------------------
# 步驟二：CSV + PNG（不覆蓋原則）
# ---------------------------------------------------------------------------

def execute_step2_export(
    *,
    request: ExportRequest,
    paths: ExportPaths,
    log_info: Callable[[str], None],
    export_csvs: Callable[..., None],
    run_png: Callable[..., None],
) -> None:
    """
    步驟二：先做 spine export → 產生 spine.json → 再做主任務 export。

    export_csvs(mask_dir, volume_csv, hu_csv, dicom_dir, spine_json_path,
                erosion_iters, slice_start, slice_end, hu_min, hu_max,
                write_volume, write_hu)

    run_png(dicom_dir, png_dir, png_eroded_dir, png_nolabel_dir,
            png_eroded_nolabel_dir, mask_dir, spine_json_path,
            slice_start, slice_end, erosion_iters)
    """
    # --- 防呆檢查 ---
    if not paths.primary_seg_dir.exists():
        raise RuntimeError(
            f"分割資料夾不存在：{paths.primary_seg_dir}\n"
            "請先執行自動分割（Mode 1）。"
        )
    if not any(paths.primary_seg_dir.glob("*.nii.gz")):
        raise RuntimeError(
            f"分割資料夾內沒有 .nii.gz 檔案：{paths.primary_seg_dir}\n"
            "請確認分割是否完成，或重新執行自動分割。"
        )
    if not request.dicom_path.exists():
        raise RuntimeError(
            f"DICOM 資料夾不存在：{request.dicom_path}"
        )
    if not request.dicom_path.is_dir() or not any(request.dicom_path.iterdir()):
        raise RuntimeError(
            f"DICOM 資料夾是空的：{request.dicom_path}"
        )

    # --- 產生 spine.json（orientation only，步驟二開始時產生）---
    spine_files = list(paths.spine_seg_dir.glob("vertebrae_*.nii.gz")) if paths.spine_seg_dir.is_dir() else []
    if spine_files:
        log_info("Step 2: building spine.json from spine segmentation")
        try:
            import SimpleITK as sitk  # noqa: PLC0415
            reader = sitk.ImageSeriesReader()
            names = reader.GetGDCMSeriesFileNames(str(request.dicom_path))
            reader.SetFileNames(names)
            ct_image = reader.Execute()
            meta = build_spine_meta(paths.spine_seg_dir, ct_image, sitk)
            write_spine_json(paths.spine_json, meta)
            log_info(f"Step 2: spine.json saved ({meta['orientation']}, {len(meta.get('slice_labels', {}))} slice labels)")
        except Exception as exc:
            log_info(f"Step 2: spine.json build failed ({exc}), using default orientation")
            write_spine_json(paths.spine_json, {"orientation": "cranial_to_caudal", "slice_labels": {}})
    else:
        log_info("Step 2: no spine segmentation found, using default orientation")
        write_spine_json(paths.spine_json, {"orientation": "cranial_to_caudal", "slice_labels": {}})

    # --- spine export（CSV + PNG）---
    if spine_files:
        log_info("Step 2: exporting spine CSV + PNG")
        export_csvs(
            paths.spine_seg_dir,
            paths.spine_volume_csv,
            paths.spine_hu_csv,
            request.dicom_path,
            paths.spine_json,
            erosion_iters=request.erosion_iters,
            slice_start=request.slice_start,
            slice_end=request.slice_end,
            hu_min=request.hu_min,
            hu_max=request.hu_max,
            write_volume=True,
            write_hu=True,
        )
        run_png(
            request.dicom_path,
            paths.spine_png_dir,
            paths.spine_png_eroded_dir,
            paths.spine_png_nolabel_dir,
            paths.spine_png_eroded_nolabel_dir,
            paths.spine_seg_dir,
            paths.spine_json,
            request.slice_start,
            request.slice_end,
            request.erosion_iters,
        )

    # --- 主任務 export（CSV + PNG）---
    log_info(f"Step 2: exporting {request.task} CSV + PNG")
    export_csvs(
        paths.primary_seg_dir,
        paths.volume_csv,
        paths.hu_csv,
        request.dicom_path,
        paths.spine_json,
        erosion_iters=request.erosion_iters,
        slice_start=request.slice_start,
        slice_end=request.slice_end,
        hu_min=request.hu_min,
        hu_max=request.hu_max,
        write_volume=True,
        write_hu=True,
    )

    run_png(
        request.dicom_path,
        paths.png_dir,
        paths.png_eroded_dir,
        paths.png_nolabel_dir,
        paths.png_eroded_nolabel_dir,
        paths.primary_seg_dir,
        paths.spine_json,
        request.slice_start,
        request.slice_end,
        request.erosion_iters,
    )

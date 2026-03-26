from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

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
# 步驟一：分割 + 產生 spine.json
# ---------------------------------------------------------------------------

def execute_step1_segmentation(
    *,
    request: SegmentRequest,
    paths: SegmentPaths,
    log_info: Callable[[str], None],
    run_task: Callable[..., None],
    load_ct_image: Callable[[Path], object],
) -> None:
    """
    執行主分割、spine 分割，並產生 spine.json。

    load_ct_image(dicom_path) → SimpleITK Image
    """
    paths.output_base.mkdir(parents=True, exist_ok=True)
    paths.primary_seg_dir.mkdir(exist_ok=True)

    task_to_run = resolve_task_for_modality(request.task, request.modality)
    log_info(f"Step 1: primary segmentation task={task_to_run}, modality={request.modality}")
    run_task(request.dicom_path, paths.primary_seg_dir, task_to_run, fast=False)

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

    log_info("Step 1: building spine.json")
    ct_image = load_ct_image(request.dicom_path)
    import SimpleITK as sitk  # noqa: PLC0415  imported here to keep step1 testable
    meta = build_spine_meta(paths.spine_seg_dir, ct_image, sitk)
    write_spine_json(paths.spine_json, meta)
    log_info(f"Step 1: spine.json saved ({meta['orientation']}, {len(meta['slice_labels'])} slice labels)")


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
    產生 volume CSV、HU CSV 和 PNG overlay。永遠覆蓋既有輸出。

    export_csvs(mask_dir, volume_csv, hu_csv, dicom_dir, spine_json_path,
                erosion_iters, slice_start, slice_end, hu_min, hu_max,
                write_volume, write_hu)

    run_png(dicom_dir, png_dir, png_eroded_dir, png_nolabel_dir,
            png_eroded_nolabel_dir, mask_dir, spine_json_path,
            slice_start, slice_end, erosion_iters)
    """
    if not paths.primary_seg_dir.exists():
        raise RuntimeError(
            f"分割資料夾不存在：{paths.primary_seg_dir}\n"
            "請先執行步驟一（分割）。"
        )
    if not paths.spine_json.exists():
        spine_seg_dir = paths.output_base / "segmentation_spine_fast"
        if spine_seg_dir.is_dir() and any(spine_seg_dir.glob("vertebrae_*.nii.gz")):
            log_info("spine.json 不存在，從既有脊椎分割資料夾重建中…")
            try:
                import SimpleITK as sitk  # noqa: PLC0415
                reader = sitk.ImageSeriesReader()
                names = reader.GetGDCMSeriesFileNames(str(request.dicom_path))
                reader.SetFileNames(names)
                ct_image = reader.Execute()
                meta = build_spine_meta(spine_seg_dir, ct_image, sitk)
                write_spine_json(paths.spine_json, meta)
                log_info(f"spine.json 重建完成（{meta['orientation']}，{len(meta['slice_labels'])} 個標籤）")
            except Exception as exc:
                log_info(f"脊椎資料夾重建失敗（{exc}），使用空白 spine.json")
                write_spine_json(paths.spine_json, {"orientation": "cranial_to_caudal", "slice_labels": {}})
        else:
            log_info("未找到脊椎分割資料夾，使用空白 spine.json（無方向標籤）")
            write_spine_json(paths.spine_json, {"orientation": "cranial_to_caudal", "slice_labels": {}})

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

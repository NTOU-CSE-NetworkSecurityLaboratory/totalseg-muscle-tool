from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from core.output_contract import PipelinePaths
from core.output_contract import build_pipeline_paths as build_pipeline_paths_impl
from core.pipeline_request import (
    EXECUTION_MODE_FULL,
    EXECUTION_MODE_REUSE_SEGMENTATION,
    FIXED_PIPELINE_AUTO_DRAW,
    FIXED_PIPELINE_FAST,
    FIXED_PIPELINE_SPINE,
    LegacyFlagState,
    PipelineRequest,
    normalize_legacy_flags,
    request_from_args,
)

__all__ = [
    "EXECUTION_MODE_FULL",
    "EXECUTION_MODE_REUSE_SEGMENTATION",
    "FIXED_PIPELINE_AUTO_DRAW",
    "FIXED_PIPELINE_FAST",
    "FIXED_PIPELINE_SPINE",
    "LegacyFlagState",
    "PipelinePaths",
    "PipelineRequest",
    "build_pipeline_paths",
    "execute_fixed_pipeline",
    "normalize_legacy_flags",
    "request_from_args",
    "resolve_spine_task",
    "resolve_task_for_modality",
    "should_export_spine",
]


def resolve_task_for_modality(task: str, modality: str) -> str:
    modality_upper = str(modality).upper()
    if modality_upper != "MRI":
        return task
    if task == "total":
        return "total_mr"
    if task == "spine":
        return "vertebrae_mr"
    return task


def should_export_spine(task: str, modality: str) -> bool:
    return resolve_task_for_modality(task, modality) not in {"total", "total_mr"}


def resolve_spine_task(modality: str) -> str:
    return "vertebrae_mr" if str(modality).upper() == "MRI" else "total"


def build_pipeline_paths(request: PipelineRequest) -> PipelinePaths:
    return build_pipeline_paths_impl(
        dicom_path=request.dicom_path,
        output_root=request.output_root,
        task=request.task,
        export_spine=should_export_spine(request.task, request.modality),
    )


def execute_fixed_pipeline(
    *,
    request: PipelineRequest,
    paths: PipelinePaths,
    log_info: Callable[[str], None],
    run_task: Callable[..., None],
    export_csv: Callable[..., None],
    merge_statistics: Callable[[str | Path, str | Path], None],
    build_auto_draw_command: Callable[..., Sequence[str]],
    run_subprocess: Callable[..., None],
    vertebrae_labels: Sequence[str],
) -> None:
    paths.output_base.mkdir(parents=True, exist_ok=True)

    if request.execution_mode == EXECUTION_MODE_REUSE_SEGMENTATION:
        if not paths.primary_seg_dir.exists():
            raise RuntimeError(f"Primary segmentation folder not found: {paths.primary_seg_dir}")
        log_info(f"Skipping segmentation and reusing existing outputs in: {paths.output_base}")
    else:
        paths.primary_seg_dir.mkdir(exist_ok=True)
        log_info(f"Primary segmentation output dir: {paths.primary_seg_dir}")
        task_to_run = resolve_task_for_modality(request.task, request.modality)
        log_info(f"Running segmentation task: {request.task} (Modality: {request.modality})")
        run_task(
            request.dicom_path,
            paths.primary_seg_dir,
            task_to_run,
            fast=bool(request.fast),
        )

        if paths.spine_seg_dir is not None:
            spine_task = resolve_spine_task(request.modality)
            log_info(f"Running spine segmentation task: {spine_task}")
            paths.spine_seg_dir.mkdir(exist_ok=True)
            log_info(f"Spine segmentation output dir: {paths.spine_seg_dir}")
            spine_roi_subset = None if spine_task == "vertebrae_mr" else list(vertebrae_labels)
            run_task(
                request.dicom_path,
                paths.spine_seg_dir,
                spine_task,
                fast=True,
                roi_subset=spine_roi_subset,
            )

    if not paths.primary_seg_dir.exists():
        raise RuntimeError(f"Primary segmentation folder not found: {paths.primary_seg_dir}")

    export_csv(
        paths.primary_seg_dir,
        str(paths.primary_csv),
        request.dicom_path,
        erosion_iters=request.erosion_iters,
        slice_start=request.slice_start,
        slice_end=request.slice_end,
    )
    merge_statistics(paths.primary_seg_dir, str(paths.primary_csv))

    if paths.spine_seg_dir is not None and paths.spine_csv is not None:
        if not paths.spine_seg_dir.exists():
            raise RuntimeError(f"Spine segmentation folder not found: {paths.spine_seg_dir}")
        export_csv(
            paths.spine_seg_dir,
            str(paths.spine_csv),
            request.dicom_path,
            erosion_iters=request.erosion_iters,
            slice_start=request.slice_start,
            slice_end=request.slice_end,
        )
        merge_statistics(paths.spine_seg_dir, str(paths.spine_csv))

    if request.auto_draw:
        draw_cmd = build_auto_draw_command(
            dicom=request.dicom_path,
            out=paths.output_base.parent,
            task=request.task,
            spine=request.spine,
            fast=request.fast,
            erosion_iters=request.erosion_iters,
            slice_start=request.slice_start,
            slice_end=request.slice_end,
        )
        run_subprocess(draw_cmd, check=True)

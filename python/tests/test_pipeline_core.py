from argparse import Namespace
from pathlib import Path

from core.pipeline_core import (
    EXECUTION_MODE_FULL,
    EXECUTION_MODE_REUSE_SEGMENTATION,
    FIXED_PIPELINE_AUTO_DRAW,
    FIXED_PIPELINE_FAST,
    FIXED_PIPELINE_SPINE,
    build_pipeline_paths,
    request_from_args,
)


def test_request_from_args_normalizes_legacy_flags():
    args = Namespace(
        dicom="SER00005",
        out="/tmp/out",
        task="abdominal_muscles",
        modality="CT",
        erosion_iters=2,
        slice_start=3,
        slice_end=9,
        skip_segmentation=False,
        spine=0,
        fast=1,
        auto_draw=0,
    )

    request, legacy_flags = request_from_args(args)

    assert legacy_flags.requested == {"spine": 0, "fast": 1, "auto_draw": 0}
    assert legacy_flags.normalized == {
        "spine": FIXED_PIPELINE_SPINE,
        "fast": FIXED_PIPELINE_FAST,
        "auto_draw": FIXED_PIPELINE_AUTO_DRAW,
    }
    assert request.dicom_path == Path("SER00005")
    assert request.output_root == Path("/tmp/out")
    assert request.execution_mode == EXECUTION_MODE_FULL
    assert request.spine == FIXED_PIPELINE_SPINE
    assert request.fast == FIXED_PIPELINE_FAST
    assert request.auto_draw == FIXED_PIPELINE_AUTO_DRAW


def test_build_pipeline_paths_omits_spine_outputs_for_total_mri():
    request, _ = request_from_args(
        Namespace(
            dicom="SER00005",
            out=None,
            task="total",
            modality="MRI",
            erosion_iters=2,
            slice_start=None,
            slice_end=None,
            skip_segmentation=False,
            spine=1,
            fast=0,
            auto_draw=1,
        )
    )

    paths = build_pipeline_paths(request)

    assert paths.output_base == Path("SER00005_output")
    assert paths.primary_seg_dir == Path("SER00005_output/segmentation_total")
    assert paths.primary_csv == Path("SER00005_output/mask_total.csv")
    assert paths.spine_seg_dir is None
    assert paths.spine_csv is None


def test_request_from_args_maps_skip_segmentation_to_reuse_mode():
    request, _ = request_from_args(
        Namespace(
            dicom="SER00005",
            out=None,
            task="abdominal_muscles",
            modality="CT",
            erosion_iters=2,
            slice_start=None,
            slice_end=None,
            skip_segmentation=True,
            spine=1,
            fast=0,
            auto_draw=1,
        )
    )

    assert request.execution_mode == EXECUTION_MODE_REUSE_SEGMENTATION

"""
Mode 2 防呆 + corrupt mask 跳過 測試
"""
from __future__ import annotations

import unittest.mock as mock
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.fixed_pipeline import execute_step2_export
from core.output_contract import build_export_paths
from core.pipeline_request import ExportRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(dicom_path: Path) -> ExportRequest:
    return ExportRequest(
        dicom_path=dicom_path,
        output_root=None,
        task="abdominal_muscles",
        erosion_iters=2,
        slice_start=None,
        slice_end=None,
        hu_min=None,
        hu_max=None,
    )


def _make_paths(dicom_path: Path):
    return build_export_paths(
        dicom_path=dicom_path,
        output_root=None,
        task="abdominal_muscles",
    )


def _noop_export_csvs(*_args, **_kwargs) -> None:
    pass


def _noop_run_png(*_args, **_kwargs) -> None:
    pass


# ---------------------------------------------------------------------------
# 防呆：分割資料夾不存在
# ---------------------------------------------------------------------------

def test_missing_seg_dir_raises(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT"
    dicom_dir.mkdir()
    (dicom_dir / "slice.dcm").write_bytes(b"fake")

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)

    with pytest.raises(RuntimeError, match="分割資料夾不存在"):
        execute_step2_export(
            request=request,
            paths=paths,
            log_info=lambda _: None,
            export_csvs=_noop_export_csvs,
            run_png=_noop_run_png,
        )


# ---------------------------------------------------------------------------
# 防呆：分割資料夾存在但沒有 .nii.gz
# ---------------------------------------------------------------------------

def test_empty_seg_dir_raises(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT"
    dicom_dir.mkdir()
    (dicom_dir / "slice.dcm").write_bytes(b"fake")

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)
    paths.primary_seg_dir.mkdir(parents=True)

    with pytest.raises(RuntimeError, match=".nii.gz"):
        execute_step2_export(
            request=request,
            paths=paths,
            log_info=lambda _: None,
            export_csvs=_noop_export_csvs,
            run_png=_noop_run_png,
        )


# ---------------------------------------------------------------------------
# 防呆：DICOM 資料夾不存在
# ---------------------------------------------------------------------------

def test_missing_dicom_dir_raises(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT_nonexistent"

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)
    paths.primary_seg_dir.mkdir(parents=True)
    (paths.primary_seg_dir / "muscle.nii.gz").write_bytes(b"fake")

    with pytest.raises(RuntimeError, match="DICOM 資料夾不存在"):
        execute_step2_export(
            request=request,
            paths=paths,
            log_info=lambda _: None,
            export_csvs=_noop_export_csvs,
            run_png=_noop_run_png,
        )


# ---------------------------------------------------------------------------
# 防呆：DICOM 資料夾是空的
# ---------------------------------------------------------------------------

def test_empty_dicom_dir_raises(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT"
    dicom_dir.mkdir()

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)
    paths.primary_seg_dir.mkdir(parents=True)
    (paths.primary_seg_dir / "muscle.nii.gz").write_bytes(b"fake")

    with pytest.raises(RuntimeError, match="DICOM 資料夾是空的"):
        execute_step2_export(
            request=request,
            paths=paths,
            log_info=lambda _: None,
            export_csvs=_noop_export_csvs,
            run_png=_noop_run_png,
        )


# ---------------------------------------------------------------------------
# 防呆：沒有 spine → 警示但繼續，export_csvs 只被呼叫一次（主任務）
# ---------------------------------------------------------------------------

def test_no_spine_warns_and_continues(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT"
    dicom_dir.mkdir()
    (dicom_dir / "slice.dcm").write_bytes(b"fake")

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)
    paths.primary_seg_dir.mkdir(parents=True)
    (paths.primary_seg_dir / "muscle.nii.gz").write_bytes(b"fake")
    # spine_seg_dir 不存在

    logs: list[str] = []
    export_calls: list[int] = []

    def counting_export(*_args, **_kwargs) -> None:
        export_calls.append(1)

    execute_step2_export(
        request=request,
        paths=paths,
        log_info=logs.append,
        export_csvs=counting_export,
        run_png=_noop_run_png,
    )

    assert any("no spine" in m.lower() or "spine" in m.lower() for m in logs)
    assert len(export_calls) == 1  # 只跑主任務，沒有 spine


# ---------------------------------------------------------------------------
# 防呆：有 spine → export_csvs 被呼叫兩次（spine + 主任務）
# ---------------------------------------------------------------------------

def test_with_spine_exports_twice(tmp_path: Path) -> None:
    dicom_dir = tmp_path / "CT"
    dicom_dir.mkdir()
    (dicom_dir / "slice.dcm").write_bytes(b"fake")

    request = _make_request(dicom_dir)
    paths = _make_paths(dicom_dir)
    paths.primary_seg_dir.mkdir(parents=True)
    (paths.primary_seg_dir / "muscle.nii.gz").write_bytes(b"fake")
    paths.spine_seg_dir.mkdir(parents=True)
    (paths.spine_seg_dir / "vertebrae_L1.nii.gz").write_bytes(b"fake")

    export_calls: list[int] = []

    def counting_export(*_args, **_kwargs) -> None:
        export_calls.append(1)

    # spine.json 產生需要 SimpleITK，這裡 mock 掉 fixed_pipeline 的 sitk
    fake_sitk = MagicMock()
    fake_sitk.ImageSeriesReader.return_value.GetGDCMSeriesFileNames.return_value = ["f1"]
    fake_sitk.ImageSeriesReader.return_value.Execute.return_value = MagicMock()

    with mock.patch("core.fixed_pipeline.build_spine_meta", return_value={"orientation": "cranial_to_caudal", "slice_labels": {}}):
        with mock.patch("core.fixed_pipeline.write_spine_json"):
            with mock.patch("builtins.__import__", side_effect=lambda name, *a, **k: fake_sitk if name == "SimpleITK" else __import__(name, *a, **k)):
                execute_step2_export(
                    request=request,
                    paths=paths,
                    log_info=lambda _: None,
                    export_csvs=counting_export,
                    run_png=_noop_run_png,
                )

    assert len(export_calls) == 2  # spine + 主任務

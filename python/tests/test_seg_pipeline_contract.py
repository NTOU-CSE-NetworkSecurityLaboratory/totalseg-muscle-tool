import sys
from pathlib import Path

import seg


def test_main_fixed_pipeline_preserves_expected_output_contract(monkeypatch, tmp_path):
    case_dir = tmp_path / "SER00005"
    case_dir.mkdir()

    recorded = {
        "run_task": [],
        "export_csv": [],
        "merge_csv": [],
        "draw": None,
    }

    def fake_run_task(dicom_path, out_dir, task, fast=False, roi_subset=None):
        recorded["run_task"].append(
            {
                "dicom_path": Path(dicom_path),
                "out_dir": Path(out_dir),
                "task": task,
                "fast": fast,
                "roi_subset": roi_subset,
            }
        )

    def fake_export(mask_dir, output_csv, dicom_path, **kwargs):
        recorded["export_csv"].append(
            {
                "mask_dir": Path(mask_dir),
                "output_csv": Path(output_csv),
                "dicom_path": Path(dicom_path),
                "kwargs": kwargs,
            }
        )

    def fake_merge(mask_dir, output_csv):
        recorded["merge_csv"].append((Path(mask_dir), Path(output_csv)))

    def fake_build_auto_draw_command(**kwargs):
        recorded["draw"] = kwargs
        return ["fake-draw"]

    monkeypatch.setattr(seg, "run_task", fake_run_task)
    monkeypatch.setattr(seg, "export_areas_and_volumes_to_csv", fake_export)
    monkeypatch.setattr(seg, "merge_statistics_to_csv", fake_merge)
    monkeypatch.setattr(seg, "build_auto_draw_command", fake_build_auto_draw_command)
    monkeypatch.setattr(seg.subprocess, "run", lambda cmd, check: None)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seg.py",
            "--dicom",
            str(case_dir),
            "--out",
            str(tmp_path),
            "--task",
            "abdominal_muscles",
            "--modality",
            "CT",
            "--spine",
            "0",
            "--fast",
            "1",
            "--auto_draw",
            "0",
            "--slice_start",
            "3",
            "--slice_end",
            "9",
        ],
    )

    seg.main()

    output_base = tmp_path / "SER00005_output"

    assert [item["task"] for item in recorded["run_task"]] == ["abdominal_muscles", "total"]
    assert recorded["run_task"][0]["out_dir"] == output_base / "segmentation_abdominal_muscles"
    assert recorded["run_task"][0]["fast"] is False
    assert recorded["run_task"][1]["out_dir"] == output_base / "segmentation_spine_fast"
    assert recorded["run_task"][1]["fast"] is True

    exported_csvs = [item["output_csv"].name for item in recorded["export_csv"]]
    assert exported_csvs == ["mask_abdominal_muscles.csv", "mask_spine_fast.csv"]

    merged_csvs = [csv_path.name for _, csv_path in recorded["merge_csv"]]
    assert merged_csvs == ["mask_abdominal_muscles.csv", "mask_spine_fast.csv"]

    assert recorded["draw"] is not None
    assert recorded["draw"]["task"] == "abdominal_muscles"
    assert recorded["draw"]["spine"] == 1
    assert recorded["draw"]["fast"] == 0
    assert recorded["draw"]["slice_start"] == 3
    assert recorded["draw"]["slice_end"] == 9

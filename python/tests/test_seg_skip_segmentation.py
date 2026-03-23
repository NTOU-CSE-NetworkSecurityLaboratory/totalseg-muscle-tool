import sys
from pathlib import Path

import seg


def test_skip_segmentation_reuses_existing_outputs(monkeypatch, tmp_path):
    case_dir = tmp_path / "SER00005"
    case_dir.mkdir()

    output_base = tmp_path / "SER00005_output"
    (output_base / "segmentation_abdominal_muscles").mkdir(parents=True)
    (output_base / "segmentation_spine_fast").mkdir(parents=True)

    called = {
        "run_task": 0,
        "export": [],
        "merge": [],
        "draw": None,
    }

    monkeypatch.setattr(seg, "run_task", lambda *args, **kwargs: called.__setitem__("run_task", called["run_task"] + 1))
    monkeypatch.setattr(
        seg,
        "export_areas_and_volumes_to_csv",
        lambda mask_dir, output_csv, dicom_path, **kwargs: called["export"].append((Path(mask_dir), Path(output_csv), kwargs)),
    )
    monkeypatch.setattr(
        seg,
        "merge_statistics_to_csv",
        lambda mask_dir, output_csv: called["merge"].append((Path(mask_dir), Path(output_csv))),
    )
    monkeypatch.setattr(
        seg,
        "build_auto_draw_command",
        lambda **kwargs: called.__setitem__("draw", kwargs) or ["fake-draw"],
    )
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
            "--skip_segmentation",
        ],
    )

    seg.main()

    assert called["run_task"] == 0
    assert [item[1].name for item in called["export"]] == [
        "mask_abdominal_muscles.csv",
        "mask_spine_fast.csv",
    ]
    assert [item[1].name for item in called["merge"]] == [
        "mask_abdominal_muscles.csv",
        "mask_spine_fast.csv",
    ]
    assert called["draw"] is not None
    assert called["draw"]["fast"] == 0
    assert called["draw"]["spine"] == 1

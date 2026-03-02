import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QTableWidgetItem, QWidget

from gui_pyside import TotalSegApp


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def window(qapp):
    win = TotalSegApp()
    try:
        yield win
    finally:
        win.close()


def _set_checked_task_row(win: TotalSegApp, row: int, dicom_path: str) -> None:
    checkbox_wrap = QWidget()
    checkbox_layout = QHBoxLayout(checkbox_wrap)
    checkbox_layout.setContentsMargins(0, 0, 0, 0)
    checkbox = QCheckBox()
    checkbox.setChecked(True)
    checkbox_layout.addWidget(checkbox)
    win.task_table.setCellWidget(row, 0, checkbox_wrap)

    path_item = QTableWidgetItem(f"case_{row}")
    path_item.setData(Qt.UserRole, dicom_path)
    win.task_table.setItem(row, 1, path_item)
    win.task_table.setItem(row, 2, QTableWidgetItem("待處理"))


def test_gui_defaults(window):
    assert window.erosion_input.text() == "2"
    assert not window.out_group.isVisible()
    assert window.log_area.minimumHeight() == 320
    # No fixed max height cap after layout update.
    assert window.log_area.maximumHeight() > 100000


def test_compare_copy_updated(window):
    assert window.btn_mode_compare.text() == "\u5f71\u50cf\u6bd4\u5c0d\u5206\u6790"
    assert window.btn_run_compare.text() == "\u958b\u59cb\u57f7\u884c\u5f71\u50cf\u6bd4\u5c0d\u5206\u6790"
    assert window.btn_select_compare_ai.text() == "\u9078\u53d6 AI \u6bd4\u5c0d\u6a94\u6848 (.nii.gz)"
    assert window.btn_select_compare_manual.text() == "\u9078\u53d6\u4eba\u5de5\u6bd4\u5c0d\u6a94\u6848 (NIfTI/NRRD)"


def test_batch_queue_uses_parent_output_root(window):
    paths = [r"C:\cases\A001", r"D:\data\B002"]
    window.folder_slice_counts = {p: 100 for p in paths}
    window.task_table.setRowCount(len(paths))
    for row, dicom_path in enumerate(paths):
        _set_checked_task_row(window, row, dicom_path)

    window.start_unified_process()

    expected_out_roots = [str(Path(p).parent) for p in paths]
    actual_out_roots = [item[2] for item in window.batch_queue]
    assert actual_out_roots == expected_out_roots


def test_normalize_slice_range_clamps_to_patient_limit(window):
    start, end, warn, err = window.normalize_slice_range("3", "999", 120)
    assert err is None
    assert start == 3
    assert end == 120
    assert warn is not None


def test_normalize_slice_range_rejects_start_over_limit(window):
    start, end, warn, err = window.normalize_slice_range("130", "140", 120)
    assert start is None
    assert end is None
    assert warn is None
    assert err is not None

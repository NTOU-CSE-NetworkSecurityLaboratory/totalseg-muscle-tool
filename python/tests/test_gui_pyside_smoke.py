import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QTableWidgetItem, QWidget

from core.update_service import UpdateStatus
from gui_pyside import TotalSegApp, filter_tasks_by_modality, parse_license_input


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


def _set_checked_task_row(
    win: TotalSegApp, row: int, dicom_path: str, checked: bool = True
) -> QCheckBox:
    checkbox_wrap = QWidget()
    checkbox_layout = QHBoxLayout(checkbox_wrap)
    checkbox_layout.setContentsMargins(0, 0, 0, 0)
    checkbox = QCheckBox()
    checkbox.setChecked(checked)
    checkbox_layout.addWidget(checkbox)
    win.task_table.setCellWidget(row, 0, checkbox_wrap)

    path_item = QTableWidgetItem(f"case_{row}")
    path_item.setData(Qt.UserRole, dicom_path)
    win.task_table.setItem(row, 1, path_item)
    win.task_table.setItem(row, 2, QTableWidgetItem("Ready"))
    return checkbox


def test_gui_defaults(window):
    assert window.erosion_input.text() == "2"
    assert not window.out_group.isVisible()
    assert window.log_area.minimumHeight() == 320
    assert window.log_area.maximumHeight() > 100000
    assert window.update_status_lbl.text().startswith("目前版本：v")
    assert window.btn_install_update.isEnabled() is False


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
    window.run_setup_and_segmentation = lambda: None

    window.start_unified_process()

    expected_out_roots = [str(Path(p).parent) for p in paths]
    actual_out_roots = [item[2] for item in window.batch_queue]
    assert actual_out_roots == expected_out_roots


def test_sort_key_uses_numeric_prefix(window):
    names = ["10.a", "2.b", "100.c", "1.d", "x_no_prefix"]
    ordered = sorted(names, key=lambda n: window._folder_numeric_sort_key(Path(n)))
    assert ordered[:4] == ["1.d", "2.b", "10.a", "100.c"]
    assert ordered[-1] == "x_no_prefix"


def test_select_all_header_checks_and_unchecks_rows(window):
    window.task_table.setRowCount(3)
    _set_checked_task_row(window, 0, r"C:\cases\A001", checked=False)
    _set_checked_task_row(window, 1, r"C:\cases\A002", checked=False)
    _set_checked_task_row(window, 2, r"C:\cases\A003", checked=False)
    window.update_ui_state()

    window.chk_select_all_header.setCheckState(Qt.CheckState.Checked)
    for row in range(3):
        chk = window.task_table.cellWidget(row, 0).layout().itemAt(0).widget()
        assert chk.isChecked()

    window.chk_select_all_header.setCheckState(Qt.CheckState.Unchecked)
    for row in range(3):
        chk = window.task_table.cellWidget(row, 0).layout().itemAt(0).widget()
        assert not chk.isChecked()


def test_select_all_header_becomes_partially_checked(window):
    window.task_table.setRowCount(2)
    first = _set_checked_task_row(window, 0, r"C:\cases\A001", checked=True)
    _set_checked_task_row(window, 1, r"C:\cases\A002", checked=True)
    window.update_ui_state()
    assert window.chk_select_all_header.checkState() == Qt.CheckState.Checked

    first.setChecked(False)
    window.on_row_checkbox_state_changed(0)
    assert window.chk_select_all_header.checkState() == Qt.CheckState.PartiallyChecked


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


def test_filter_tasks_by_modality():
    tasks = ["total", "total_mr", "body", "body_mr"]
    assert filter_tasks_by_modality(tasks, "CT") == ["total", "body"]
    assert filter_tasks_by_modality(tasks, "MRI") == ["total_mr", "body_mr"]


def test_modality_switch_updates_task_options(window):
    window.modality_combo.setCurrentText("CT")
    ct_tasks = [window.task_combo.itemText(i) for i in range(window.task_combo.count())]
    assert ct_tasks
    assert all(not t.endswith("_mr") for t in ct_tasks)

    window.modality_combo.setCurrentText("MRI")
    mr_tasks = [window.task_combo.itemText(i) for i in range(window.task_combo.count())]
    assert mr_tasks
    assert all(t.endswith("_mr") for t in mr_tasks)


def test_tqdm_like_carriage_return_overwrites_single_line(window):
    window.log_area.clear()
    window.append_stream_log("progress 10%")
    window.append_stream_log("\rprogress 20%")
    window.append_stream_log("\rprogress 30%")
    window.append_stream_log("\n")
    text = window.log_area.toPlainText()
    assert "progress 10%" not in text
    assert "progress 20%" not in text
    assert text.endswith("progress 30%\n")


def test_classify_totalseg_license_error(window):
    log_text = "In contrast to the other tasks this task is not openly available. It requires a license."
    assert window._classify_totalseg_error(log_text) == "license_missing_or_invalid"


def test_process_finished_prompts_for_license_issue(window, monkeypatch):
    class FakeProcess:
        def exitCode(self):
            return 1

        def state(self):
            return 0

    window.process = FakeProcess()
    window.process_state = "seg"
    window.current_batch_index = 0
    window.batch_queue = [(0, "/tmp/case", "/tmp/out", 12, "SER00005")]
    window.task_table.setRowCount(1)
    _set_checked_task_row(window, 0, "/tmp/case")
    window._current_case_log_excerpt = "This task is not openly available. It requires a license."
    window.process_error_message = ""
    window.case_started_at = None
    window.completed_case_durations = []
    window.failed_cases = []
    window._stream_buffer = ""
    window._stream_line_buffer = ""
    window._ephemeral_active = False

    prompted = {"called": False}

    def fake_prompt():
        prompted["called"] = True
        return True

    monkeypatch.setattr(window, "drain_process_output", lambda: None)
    monkeypatch.setattr(window, "append_stream_log", lambda _text: None)
    monkeypatch.setattr(window, "_commit_stream_line", lambda _text: None)
    monkeypatch.setattr(window.stream_timer, "stop", lambda: None)
    monkeypatch.setattr(window, "diagnose_error", lambda _text: None)
    monkeypatch.setattr(window, "_record_case_failure", lambda **_kwargs: None)
    monkeypatch.setattr(window, "_update_progress_eta", lambda: None)
    monkeypatch.setattr(window, "run_next_batch_task", lambda: (_ for _ in ()).throw(AssertionError("should not continue batch")))
    monkeypatch.setattr(window, "prompt_totalseg_license_and_maybe_retry", fake_prompt)

    window.process_finished()

    assert prompted["called"] is True


def test_classify_totalseg_broken_config_error(window):
    log_text = "json.decoder.JSONDecodeError ... totalsegmentator\\config.py"
    assert window._classify_totalseg_error(log_text) == "totalseg_config_json_broken"


def test_mask_license_key(window):
    masked = window._mask_license_key("aca_T9Z5DWL7XWRMT2")
    assert masked.startswith("aca_")
    assert masked.endswith("RMT2")


def test_refresh_update_status_blocks_git_checkout(window, monkeypatch):
    status = UpdateStatus(
        current_version="0.0.1",
        latest_version="0.0.2",
        update_available=True,
        install_supported=False,
        install_block_reason="GUI 更新器不支援直接覆蓋開發中的 git 工作目錄。",
        release_page_url="https://example.com/release",
        release=None,
    )
    monkeypatch.setattr("core.gui_update_controller.build_update_status", lambda **_kwargs: status)

    window.refresh_update_status()

    assert "git 工作目錄" in window.update_hint_lbl.text()
    assert window.btn_install_update.isEnabled() is False


def test_parse_license_input_raw_key():
    assert parse_license_input("aca_7ZON8A6GHQOVRD") == "aca_7ZON8A6GHQOVRD"


def test_parse_license_input_short_flag_command():
    cmd = "totalseg_set_license -l aca_7ZON8A6GHQOVRD"
    assert parse_license_input(cmd) == "aca_7ZON8A6GHQOVRD"


def test_parse_license_input_long_flag_command():
    cmd = "totalseg_set_license --license_number aca_7ZON8A6GHQOVRD"
    assert parse_license_input(cmd) == "aca_7ZON8A6GHQOVRD"

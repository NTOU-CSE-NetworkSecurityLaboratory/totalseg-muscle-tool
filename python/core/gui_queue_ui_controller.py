from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt


class GuiQueueUiController:
    def __init__(self, window):
        self.window = window

    def set_all_row_checks(self, checked: bool) -> None:
        self.window._bulk_check_updating = True
        try:
            for i in range(self.window.task_table.rowCount()):
                chk_widget = self.window.task_table.cellWidget(i, 0)
                if not chk_widget or not chk_widget.layout():
                    continue
                chk = chk_widget.layout().itemAt(0).widget()
                if chk is not None:
                    chk.setChecked(checked)
        finally:
            self.window._bulk_check_updating = False
        self.window.update_ui_state()

    def on_select_all_state_changed(self, state) -> None:
        if self.window._bulk_check_updating:
            return
        if state in (Qt.CheckState.PartiallyChecked, Qt.CheckState.PartiallyChecked.value):
            return
        should_check = state in (Qt.CheckState.Checked, Qt.CheckState.Checked.value)
        self.set_all_row_checks(should_check)

    def on_row_checkbox_state_changed(self, _state) -> None:
        if self.window._bulk_check_updating:
            return
        self.window.update_ui_state()

    def update_select_all_state_from_rows(self) -> None:
        if not hasattr(self.window, "chk_select_all_header"):
            return

        row_count = self.window.task_table.rowCount()
        self.window.chk_select_all_header.setEnabled(row_count > 0)
        if row_count == 0:
            self.window.chk_select_all_header.blockSignals(True)
            self.window.chk_select_all_header.setCheckState(Qt.CheckState.Unchecked)
            self.window.chk_select_all_header.blockSignals(False)
            return

        checked_count = 0
        for i in range(row_count):
            chk_widget = self.window.task_table.cellWidget(i, 0)
            if not chk_widget or not chk_widget.layout():
                continue
            chk = chk_widget.layout().itemAt(0).widget()
            if chk is not None and chk.isChecked():
                checked_count += 1

        if checked_count == 0:
            state = Qt.CheckState.Unchecked
        elif checked_count == row_count:
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        self.window.chk_select_all_header.blockSignals(True)
        self.window.chk_select_all_header.setCheckState(state)
        self.window.chk_select_all_header.blockSignals(False)

    def format_seconds(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        hh = seconds // 3600
        mm = (seconds % 3600) // 60
        ss = seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    def update_progress_eta(self) -> None:
        total = len(self.window.batch_queue)
        current = self.window.current_batch_index + 1 if self.window.current_batch_index >= 0 else 0
        if total <= 0:
            self.window.prog_bar_lbl.setText("目前項目中共有 0 個待處理任務")
            return

        if self.window.completed_case_durations:
            avg_seconds = sum(self.window.completed_case_durations) / len(
                self.window.completed_case_durations
            )
            remaining_cases = max(0, total - len(self.window.completed_case_durations))
            remaining_seconds = int(avg_seconds * remaining_cases)
            eta_at = (datetime.now() + timedelta(seconds=remaining_seconds)).strftime("%H:%M")
            self.window.prog_bar_lbl.setText(
                f"目前進度：第 {current} / {total} 個任務 | "
                f"預估剩餘 {self.format_seconds(remaining_seconds)} | "
                f"預計完成 {eta_at}"
            )
            return
        self.window.prog_bar_lbl.setText(f"目前進度：第 {current} / {total} 個任務")

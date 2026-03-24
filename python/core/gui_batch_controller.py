from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor


class GuiBatchController:
    def __init__(self, window):
        self.window = window

    def start_unified_process(self) -> None:
        self.window.log_area.clear()
        self.window.is_running = True
        self.window._retry_same_task = False
        self.window.btn_start.setEnabled(False)
        self.window.btn_start.setText("初始化 AI 環境中...")
        self.window.batch_started_at = datetime.now()
        self.window.case_started_at = None
        self.window.completed_case_durations = []
        self.window.failed_cases = []
        self.window.session_log_path = None
        self.window.process_error_message = ""
        self.window._current_case_log_excerpt = ""

        self.window.batch_queue = []
        for i in range(self.window.task_table.rowCount()):
            chk_widget = self.window.task_table.cellWidget(i, 0)
            if not chk_widget or not chk_widget.layout():
                continue
            chk = chk_widget.layout().itemAt(0).widget()
            if chk is not None and chk.isChecked():
                dicom_path = self.window.task_table.item(i, 1).data(self.window.qt_user_role)
                case_label = self.window.task_table.item(i, 1).text()
                slice_count = self.window.folder_slice_counts.get(str(dicom_path))
                out_path = str(Path(dicom_path).parent)
                self.window.batch_queue.append((i, dicom_path, out_path, slice_count, case_label))

        if not self.window.batch_queue:
            self.window.append_log("[警示] 尚未勾選任何病人，無法開始批次。\n")
            self.reset_ui()
            return

        self.window._prepare_session_log()
        self.window._write_session_log(
            f"BATCH_START | total_cases={len(self.window.batch_queue)} | source={self.window.source_root_path}"
        )
        self.window.current_batch_index = -1
        QTimer.singleShot(100, self.run_setup_and_segmentation)

    def run_setup_and_segmentation(self) -> None:
        try:
            if shutil.which("uv") is None:
                self.window.append_log("[錯誤] 找不到 uv，請先執行啟動器完成環境同步。\n")
                self.reset_ui()
                return
            self.window.append_log("環境檢查完成，開始執行分割任務...\n")
            self.run_next_batch_task()
        except Exception as exc:
            self.window.append_log(f"[異常中斷] {str(exc)}\n")
            self.reset_ui()

    def handle_process_error(self, _error) -> None:
        self.window.process_error_message = self.window.process.errorString()
        if self.window.process_error_message:
            self.window.append_log(f"[錯誤] 子程序異常：{self.window.process_error_message}\n")

    def process_finished(self) -> None:
        self.window.log_stream.flush_pending()
        self.window.stream_timer.stop()
        if self.window.process_state == "sync":
            if self.window.process.exitCode() == 0:
                if sys.platform == "darwin":
                    self.window.fix_macos_torch_perms()
                self.run_next_batch_task()
            else:
                self.reset_ui()
            return

        if self.window.process_state != "seg":
            return

        if self.window.current_batch_index >= 0:
            row, dicom_path, _out_path, _slice_count, case_label = self.window.batch_queue[
                self.window.current_batch_index
            ]
            elapsed = 0.0
            if self.window.case_started_at is not None:
                elapsed = max(0.0, (datetime.now() - self.window.case_started_at).total_seconds())
            self.window.completed_case_durations.append(elapsed)
            if self.window.process.exitCode() == 0:
                self.window.task_table.item(row, 2).setText("處理完成")
                self.window.task_table.item(row, 2).setForeground(QColor("#198754"))
                self.window._record_case_success(case_label, dicom_path, elapsed)
            else:
                should_continue = self._handle_failed_case(row, dicom_path, case_label, elapsed)
                if not should_continue:
                    return

        self.window._update_progress_eta()
        self.run_next_batch_task()

    def _handle_failed_case(self, row, dicom_path, case_label, elapsed) -> bool:
        self.window.task_table.item(row, 2).setText("處理失敗")
        self.window.task_table.item(row, 2).setForeground(QColor("#dc3545"))
        log_text = self.window._current_case_log_excerpt or self.window.log_area.toPlainText()
        self.window.diagnose_error(log_text)
        issue = self.window._classify_totalseg_error(log_text)
        reason = f"exit_code={self.window.process.exitCode()}"
        if self.window.process_error_message:
            reason += f", qprocess={self.window.process_error_message}"
        if issue == "totalseg_config_json_broken":
            _, msg = self.window.repair_totalseg_config_if_broken()
            if msg:
                self.window.append_log(msg)
            reason += ", issue=totalseg_config_json_broken"
        elif issue == "license_missing_or_invalid":
            reason += ", issue=license_missing_or_invalid"
        self.window._record_case_failure(
            case_label=case_label,
            dicom_path=dicom_path,
            reason=reason,
            excerpt=log_text,
        )
        self.window.append_log(f"[錯誤] {case_label} 失敗，已記錄至批次 log。\n")
        if issue == "license_missing_or_invalid":
            self.window.prompt_totalseg_license_and_maybe_retry()
            return False
        return True

    def run_next_batch_task(self) -> None:
        if self.window._retry_same_task:
            self.window._retry_same_task = False
        else:
            self.window.current_batch_index += 1

        if self.window.current_batch_index >= len(self.window.batch_queue):
            self._finish_batch()
            return

        row, dicom_path, out_path, slice_count, case_label = self.window.batch_queue[
            self.window.current_batch_index
        ]
        self.window.task_table.item(row, 2).setText("執行分割中...")
        self.window.task_table.item(row, 2).setForeground(QColor("#0d6efd"))
        self.window.case_started_at = datetime.now()
        self.window.process_error_message = ""
        self.window._current_case_log_excerpt = ""
        self.window._write_session_log(
            f"CASE_START | index={self.window.current_batch_index + 1}/{len(self.window.batch_queue)} "
            f"| case={case_label} | dicom={dicom_path}"
        )
        self.window._update_progress_eta()
        self.window.pbar.setValue(self.window.current_batch_index)

        slice_start, slice_end = self._resolve_slice_range(row, case_label, dicom_path, slice_count)
        if slice_start is False:
            return

        cmd_args = self.window._build_seg_command(
            dicom_path=dicom_path,
            out_path=out_path,
            task=self.window.task_combo.currentText(),
            modality=self.window.modality_combo.currentText(),
            spine=True,
            fast=False,
            auto_draw=True,
            erosion_iters=self.window.erosion_input.text(),
            slice_start=slice_start,
            slice_end=slice_end,
        )

        self.window.process_state = "seg"
        self.window._stream_buffer = ""
        self.window._stream_line_buffer = ""
        self.window._ephemeral_active = False
        self.window.stream_timer.start()
        self.window.process.start("uv", cmd_args)

    def _resolve_slice_range(self, row, case_label, dicom_path, slice_count):
        if not self.window.range_box_widget.isChecked():
            return None, None

        start_val, end_val, warn_message, error_message = self.window.normalize_slice_range(
            start_str=self.window.slice_start_input.text(),
            end_str=self.window.slice_end_input.text(),
            slice_count=slice_count,
        )

        if error_message:
            self.window.task_table.item(row, 2).setText("切片範圍錯誤")
            self.window.task_table.item(row, 2).setForeground(QColor("#dc3545"))
            self.window.append_log(f"[錯誤] {case_label}: {error_message}\n")
            self.window.completed_case_durations.append(0.0)
            self.window._record_case_failure(
                case_label=case_label,
                dicom_path=dicom_path,
                reason=f"slice_range_error: {error_message}",
                excerpt=error_message,
            )
            self.window._update_progress_eta()
            QTimer.singleShot(0, self.run_next_batch_task)
            return False, False

        if warn_message:
            self.window.append_log(f"[??] {case_label}: {warn_message}\n")

        return start_val, end_val

    def _finish_batch(self) -> None:
        total = len(self.window.batch_queue)
        failed = len(self.window.failed_cases)
        succeeded = total - failed
        elapsed = 0.0
        if self.window.batch_started_at is not None:
            elapsed = max(0.0, (datetime.now() - self.window.batch_started_at).total_seconds())
        self.window.append_log("\n[完成] 所有自動分割任務已處理完畢。\n")
        self.window.append_log(
            f"[統計] 成功 {succeeded} / 失敗 {failed} / 總數 {total}，總耗時 {self.window._format_seconds(elapsed)}。\n"
        )
        if self.window.session_log_path:
            self.window.append_log(f"[系統] 批次 log：{self.window.session_log_path}\n")
        self.window._write_session_log(
            f"BATCH_END | total={total} | success={succeeded} | failed={failed} | elapsed_sec={elapsed:.2f}"
        )
        self.window.pbar.setValue(len(self.window.batch_queue))
        self.reset_ui()

    def reset_ui(self) -> None:
        self.window.is_running = False
        self.window.stream_timer.stop()
        self.window._stream_buffer = ""
        self.window._stream_line_buffer = ""
        self.window._ephemeral_active = False
        self.window.btn_start.setText("啟動 AI 自動分割任務")
        self.window.btn_start.setEnabled(True)
        self.window.btn_select_src.setEnabled(True)

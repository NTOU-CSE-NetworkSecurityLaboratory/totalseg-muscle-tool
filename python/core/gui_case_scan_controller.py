from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QTableWidgetItem, QWidget


class GuiCaseScanController:
    def __init__(self, window, *, scan_dicom_cases, sitk_module):
        self.window = window
        self.scan_dicom_cases = scan_dicom_cases
        self.sitk = sitk_module

    def select_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self.window, "請選取 DICOM 資料夾或病患根目錄")
        if path:
            self.window.source_root_path = path
            self.window.src_label.setText(path)
            parent_dir = Path(path).parent
            self.window.out_label.setText(str(parent_dir / (Path(path).name + "_output")))
            self.scan_directory(path)

    def select_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self.window, "請選取輸出資料存放根目錄")
        if folder:
            self.window.out_label.setText(folder)

    def scan_directory(self, root_path: str) -> None:
        self.window.task_table.setRowCount(0)
        self.window.folder_slice_counts = {}
        root = Path(root_path)
        case_items = self.scan_dicom_cases(root)
        valid_folders = [item.folder for item in case_items]

        if not valid_folders:
            self.window.append_log("[警示] 未在所選路徑偵測到 DICOM 影像檔。\n")
            self.window.btn_start.setEnabled(False)
            self.window.update_select_all_state_from_rows()
            return

        self.window.task_table.setRowCount(len(valid_folders))
        for i, item in enumerate(case_items):
            folder = item.folder
            slice_count = item.slice_count
            self.window.folder_slice_counts[str(folder)] = slice_count

            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.window.task_table.setCellWidget(i, 0, chk_widget)
            chk.stateChanged.connect(self.window.on_row_checkbox_state_changed)

            display_name = item.label
            if slice_count and slice_count > 0:
                display_name = f"{display_name} ({slice_count} 張)"

            path_item = QTableWidgetItem(display_name)
            path_item.setData(Qt.UserRole, str(folder))
            self.window.task_table.setItem(i, 1, path_item)

            status_text = (
                f"待處理 (共 {slice_count} 張)"
                if slice_count and slice_count > 0
                else "待處理 (Ready)"
            )
            self.window.task_table.setItem(i, 2, QTableWidgetItem(status_text))

        self.window.update_ui_state()
        self._update_slice_range_display(valid_folders)
        self._update_spacing(valid_folders)
        self.window.calc_erosion()

    def update_ui_state(self) -> None:
        checked_count = 0
        for i in range(self.window.task_table.rowCount()):
            chk_widget = self.window.task_table.cellWidget(i, 0)
            if not chk_widget or not chk_widget.layout():
                continue
            chk = chk_widget.layout().itemAt(0).widget()
            if chk is not None and chk.isChecked():
                checked_count += 1

        self.window.btn_start.setEnabled(checked_count > 0)
        self.window.prog_bar_lbl.setText(f"目前項目中共有 {checked_count} 個待處理任務")
        self.window.pbar.setMaximum(checked_count if checked_count > 0 else 1)
        self.window.pbar.setValue(0)
        self.window.update_select_all_state_from_rows()

    def _update_slice_range_display(self, valid_folders: list[Path]) -> None:
        if len(valid_folders) == 1:
            only_key = str(valid_folders[0])
            only_count = self.window.folder_slice_counts.get(only_key)
            if only_count and only_count > 0:
                self.window.slice_start_input.setText("1")
                self.window.slice_end_input.setText(str(only_count))
                self.window.range_box_widget.setTitle(
                    f"切片範圍計算 (選填)｜單一病患共 {only_count} 張"
                )
                self.window.append_log(
                    f"[系統] 已載入單一病患，共 {only_count} 張切片，切片範圍已預填為 1 ~ {only_count}。\n"
                )
            else:
                self.window.range_box_widget.setTitle("切片範圍計算 (選填)")
            return

        self.window.range_box_widget.setTitle("切片範圍計算 (選填)｜多病患將逐案自動夾限")
        self.window.slice_end_input.setText("")
        self.window.slice_end_input.setPlaceholderText("依各病患上限自動夾限")
        self.window.append_log("[系統] 多病患模式：切片範圍會依每位病患切片上限自動限制。\n")

    def _update_spacing(self, valid_folders: list[Path]) -> None:
        if not self.sitk or not valid_folders:
            return
        try:
            reader = self.sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(str(valid_folders[0]))
            if dicom_names:
                first_img = self.sitk.ReadImage(dicom_names[0])
                spacing = first_img.GetSpacing()
                self.window.spacing_xy = (spacing[0], spacing[1])
                self.window.append_log(
                    f"[系統] 成功識別影像解析度: {spacing[0]:.2f} x {spacing[1]:.2f} mm\n"
                )
            else:
                self.window.spacing_xy = None
        except Exception:
            self.window.spacing_xy = None

import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QEventLoop, QProcess, QProcessEnvironment, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QIntValidator, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.app_version import read_local_app_version
from core.shared_core import (
    build_seg_command,
)
from core.shared_core import (
    compare_masks as core_compare_masks,
)
from core.shared_core import (
    filter_tasks_by_modality as core_filter_tasks_by_modality,
)
from core.shared_core import (
    get_dicom_slice_count as core_get_dicom_slice_count,
)
from core.shared_core import (
    has_dicom_files as core_has_dicom_files,
)
from core.shared_core import (
    normalize_slice_range as core_normalize_slice_range,
)
from core.shared_core import (
    scan_dicom_cases as core_scan_dicom_cases,
)
from core.update_service import (
    build_update_status,
    download_release_zip,
    extract_release_payload,
    spawn_release_update,
)

# Try importing SimpleITK for erosion calculation
try:
    import SimpleITK as sitk
except ImportError:
    sitk = None

# Determine if running as a bundled PyInstaller EXE
IS_BUNDLED = getattr(sys, 'frozen', False)

if IS_BUNDLED:
    EXE_DIR = Path(sys.executable).parent
    BASE_DIR = EXE_DIR / "TotalSeg_Backend"
    MEIPASS_DIR = Path(sys._MEIPASS)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    required_files = ["pyproject.toml", "uv.lock", "seg.py", "draw.py"]
    for f in required_files:
        src = MEIPASS_DIR / f
        dst = BASE_DIR / f
        if src.exists():
            shutil.copy2(src, dst)
else:
    BASE_DIR = Path(__file__).parent
APP_ROOT = BASE_DIR.parent if BASE_DIR.name == "python" else BASE_DIR
APP_VERSION = read_local_app_version(BASE_DIR)


def resolve_app_icon_path():
    """
    自動尋找應用程式 icon。
    可放置於：
    - 專案根目錄：app_icon.ico / app_icon.png
    - python 目錄：app_icon.ico / app_icon.png
    - 打包後 EXE 同層：app_icon.ico / app_icon.png
    """
    candidates = []
    if IS_BUNDLED:
        exe_dir = Path(sys.executable).parent
        candidates.extend(
            [
                exe_dir / "app_icon.ico",
                exe_dir / "app_icon.png",
                BASE_DIR / "app_icon.ico",
                BASE_DIR / "app_icon.png",
            ]
        )
    else:
        python_dir = BASE_DIR
        repo_root = python_dir.parent
        candidates.extend(
            [
                repo_root / "app_icon.ico",
                repo_root / "app_icon.png",
                python_dir / "app_icon.ico",
                python_dir / "app_icon.png",
            ]
        )

    for path in candidates:
        if path.exists():
            return path
    return None

# Modern QSS Style for a premium look
MODERN_STYLE = """
QMainWindow {
    background-color: #ffffff;
}
QWidget {
    font-size: 13px;
    color: #333;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    margin-top: 15px;
    background-color: #fcfcfc;
    padding-top: 25px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    color: #495057;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #f8f9fa;
    border-color: #adb5bd;
}
QPushButton:pressed {
    background-color: #e9ecef;
}
QPushButton#primary_btn {
    background-color: #0d6efd;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#primary_btn:hover {
    background-color: #0b5ed7;
}
QPushButton#primary_btn:disabled {
    background-color: #e9ecef;
    color: #adb5bd;
}

/* Header Switcher Buttons */
QPushButton#mode_btn {
    border: none;
    background-color: transparent;
    border-radius: 0px;
    border-bottom: 3px solid transparent;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
    color: #6c757d;
}
QPushButton#mode_btn:hover {
    color: #0d6efd;
}
QPushButton#mode_btn[active="true"] {
    color: #0d6efd;
    border-bottom: 3px solid #0d6efd;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    gridline-color: #f8f9fa;
}
/* Fix for Black Bar Selection */
QTableWidget::item:selected {
    background-color: #e7f1ff;
    color: #0d6efd;
}
QTableWidget::item {
    padding: 8px;
    color: #333333;
}
QHeaderView::section {
    background-color: #f8f9fa;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e9ecef;
    font-weight: bold;
    color: #495057;
}
QProgressBar {
    border: none;
    background-color: #f1f3f5;
    height: 8px;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #0d6efd;
    border-radius: 4px;
}
QPlainTextEdit {
    background-color: #fafbfc;
    color: #444;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 12px;
}
QLineEdit {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 8px;
    background-color: white;
}
"""

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

TASK_OPTIONS = [
    "abdominal_muscles",
    "aortic_sinuses",
    "appendicular_bones",
    "appendicular_bones_mr",
    "body",
    "body_mr",
    "brain_structures",
    "breasts",
    "cerebral_bleed",
    "coronary_arteries",
    "craniofacial_structures",
    "face",
    "face_mr",
    "head_glands_cavities",
    "head_muscles",
    "headneck_bones_vessels",
    "headneck_muscles",
    "heartchambers_highres",
    "hip_implant",
    "kidney_cysts",
    "liver_segments",
    "liver_segments_mr",
    "lung_nodules",
    "lung_vessels",
    "oculomotor_muscles",
    "pleural_pericard_effusion",
    "thigh_shoulder_muscles",
    "thigh_shoulder_muscles_mr",
    "tissue_4_types",
    "tissue_types",
    "tissue_types_mr",
    "ventricle_parts",
    "vertebrae_body",
    "vertebrae_mr",
    "total_mr",
    "total",
]


def filter_tasks_by_modality(tasks, modality):
    return core_filter_tasks_by_modality(tasks, modality)


LICENSE_APPLY_URL = "https://backend.totalsegmentator.com/license-academic/"


class LicenseInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TotalSegmentator 授權設定")
        self.setModal(True)
        self.resize(560, 220)

        layout = QVBoxLayout(self)
        info = QLabel(
            "這個分割任務需要 TotalSegmentator 授權。<br>"
            f"請先到官方頁面申請授權：<br>"
            f"<a href='{LICENSE_APPLY_URL}'>{LICENSE_APPLY_URL}</a>"
        )
        info.setOpenExternalLinks(True)
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText(
            "可貼金鑰或指令，例如: aca_XXXX 或 totalseg_set_license -l aca_XXXX"
        )
        form.addRow("授權金鑰:", self.license_input)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_cancel = QPushButton("取消")
        self.btn_apply = QPushButton("套用金鑰")
        self.btn_apply.setObjectName("primary_btn")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self._on_apply)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_apply)
        layout.addLayout(buttons)

    def _on_apply(self):
        if not self.license_input.text().strip():
            QMessageBox.warning(self, "輸入錯誤", "請先輸入授權金鑰。")
            return
        self.accept()

    def get_license_key(self):
        return self.license_input.text().strip()


def parse_license_input(raw_text):
    text = (raw_text or "").strip()
    if not text:
        return ""

    # Accept command style:
    #   totalseg_set_license -l aca_XXXX
    #   totalseg_set_license --license_number aca_XXXX
    m = re.search(r"(?:^|\s)(?:-l|--license_number)\s+([^\s\"']+)", text)
    if m:
        return m.group(1).strip()

    # Accept wrapped command string with quotes.
    m = re.search(
        r"(?:^|\s)(?:-l|--license_number)\s+[\"']([^\"']+)[\"']",
        text,
    )
    if m:
        return m.group(1).strip()

    # Fallback: treat input as raw key.
    return text

class TotalSegApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TotalSegmentator AI 影像管理系統 v{APP_VERSION}")
        self.resize(1150, 850)
        self.setStyleSheet(MODERN_STYLE)
        icon_path = resolve_app_icon_path()
        if icon_path:
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
            if QApplication.instance() is not None:
                QApplication.instance().setWindowIcon(app_icon)

        # State Variables
        self.spacing_xy = None
        self.folder_slice_counts = {}
        self.batch_queue = []
        self.current_batch_index = -1
        self.is_running = False
        self._retry_same_task = False
        self._bulk_check_updating = False
        self._max_log_chars = 200000
        self._max_case_excerpt_chars = 16000
        self.source_root_path = ""
        self.batch_started_at = None
        self.case_started_at = None
        self.completed_case_durations = []
        self.failed_cases = []
        self.session_log_path = None
        self.process_state = ""
        self.process_error_message = ""
        self._current_case_log_excerpt = ""
        
        self.compare_ai_mask = ""
        self.compare_manual_mask = ""
        self.update_status = None
        self.latest_release = None

        # 智慧解決方案引擎 (Solution Engine)
        self.solutions = {
            "CUDA out of memory": "【建議解決方案】顯卡記憶體不足。請關閉其他佔用顯卡的程式，或改以較小批次重新執行。",
            "No Series can be found": "【建議解決方案】找不到影像。請確認資料夾內包含標準 DICOM 檔案，或嘗試掃描更深層的目錄。",
            "UnicodeEncodeError": "【建議解決方案】檔案路徑包含特殊字元。請將資料夾移動至僅包含英文與數字的路徑。",
            "Permission denied": "【建議解決方案】存取被拒。請檢查資料夾權限，或暫時關閉可能攔截程式的防毒軟體。",
            "torch_shm_manager": "【macOS 專用修復】偵測到 PyTorch 權限問題。系統已嘗試自動修復，請再次按下「啟動 AI 自動分割任務」。",
            "mach port for IMKCFRunLoopWakeUpReliable": "【系統提示】這是 macOS 的輸入法相容性警告，不影響程式執行，請放心使用。",
            "ModuleNotFoundError": "【技術提示】環境組件遺失。請重新執行 `uv sync` 以確保所有依賴項已正確安裝。"
        }

        # Central Widget & Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_v_layout = QVBoxLayout(self.central_widget)
        self.main_v_layout.setContentsMargins(0, 0, 0, 0)
        self.main_v_layout.setSpacing(0)

        # --- Top Navigation Bar ---
        self.nav_bar = QFrame()
        self.nav_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #e9ecef;")
        self.nav_bar.setFixedHeight(65)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(30, 0, 30, 0)

        brand_lbl = QLabel("TotalSeg AI")
        brand_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0d6efd; margin-right: 30px;")
        nav_layout.addWidget(brand_lbl)

        # Mode Selector Buttons
        self.btn_mode_seg = QPushButton("AI 自動分割 (Segmentation)")
        self.btn_mode_seg.setObjectName("mode_btn")
        self.btn_mode_seg.setProperty("active", True)
        self.btn_mode_seg.clicked.connect(lambda: self.switch_mode("seg"))
        nav_layout.addWidget(self.btn_mode_seg)

        self.btn_mode_compare = QPushButton("影像比對分析")
        self.btn_mode_compare.setObjectName("mode_btn")
        self.btn_mode_compare.setProperty("active", False)
        self.btn_mode_compare.clicked.connect(lambda: self.switch_mode("compare"))
        nav_layout.addWidget(self.btn_mode_compare)

        nav_layout.addStretch()

        self.version_lbl = QLabel(f"版本 v{APP_VERSION}")
        self.version_lbl.setStyleSheet("color: #6c757d; font-size: 11px; margin-right: 12px;")
        nav_layout.addWidget(self.version_lbl)
        
        # Detected Device Label
        self.device_lbl = QLabel("後端推論引擎準備中...")
        self.device_lbl.setStyleSheet("color: #6c757d; font-size: 11px;")
        nav_layout.addWidget(self.device_lbl)
        
        self.main_v_layout.addWidget(self.nav_bar)

        # --- Content Area (Stacked) ---
        self.content_stack = QStackedWidget()
        self.main_v_layout.addWidget(self.content_stack, 3)

        # PAGE 1: Segmentation
        self.page_seg = QWidget()
        self.setup_seg_page()
        self.content_stack.addWidget(self.page_seg)

        # PAGE 2: Comparison
        self.page_compare = QWidget()
        self.setup_compare_page()
        self.content_stack.addWidget(self.page_compare)

        # --- Bottom Log Area ---
        self.log_container = QWidget()
        self.log_container.setStyleSheet("background-color: white; padding: 10px 30px 30px 30px;")
        log_layout = QVBoxLayout(self.log_container)
        
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Monaco", 9)) if sys.platform == "darwin" else self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setMinimumHeight(320)
        self.log_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_area.setPlaceholderText("系統執行日誌將顯示於此...")
        log_layout.addWidget(self.log_area)
        
        self.main_v_layout.addWidget(self.log_container, 4)

        # QProcess
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(BASE_DIR))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        proc_env = QProcessEnvironment.systemEnvironment()
        proc_env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(proc_env)
        self._stream_buffer = ""
        self._stream_line_buffer = ""
        self._ephemeral_active = False
        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(30)
        self.stream_timer.timeout.connect(self.drain_process_output)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyRead.connect(self.drain_process_output)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.handle_process_error)

    def switch_mode(self, mode):
        if mode == "seg":
            self.content_stack.setCurrentIndex(0)
            self.btn_mode_seg.setProperty("active", True)
            self.btn_mode_compare.setProperty("active", False)
        else:
            self.content_stack.setCurrentIndex(1)
            self.btn_mode_seg.setProperty("active", False)
            self.btn_mode_compare.setProperty("active", True)
        
        # Refresh styles
        self.btn_mode_seg.style().unpolish(self.btn_mode_seg)
        self.btn_mode_seg.style().polish(self.btn_mode_seg)
        self.btn_mode_compare.style().unpolish(self.btn_mode_compare)
        self.btn_mode_compare.style().polish(self.btn_mode_compare)

    def _extract_numeric_prefix(self, folder_name):
        m = re.match(r"^\s*(\d+)\.", folder_name or "")
        if not m:
            return None
        return int(m.group(1))

    def _folder_numeric_sort_key(self, folder):
        prefix_num = self._extract_numeric_prefix(folder.name)
        if prefix_num is None:
            return (1, float("inf"), folder.name.lower())
        return (0, prefix_num, folder.name.lower())

    def _set_all_row_checks(self, checked):
        self._bulk_check_updating = True
        try:
            for i in range(self.task_table.rowCount()):
                chk_widget = self.task_table.cellWidget(i, 0)
                if not chk_widget or not chk_widget.layout():
                    continue
                chk = chk_widget.layout().itemAt(0).widget()
                if chk is not None:
                    chk.setChecked(checked)
        finally:
            self._bulk_check_updating = False
        self.update_ui_state()

    def on_select_all_state_changed(self, state):
        if self._bulk_check_updating:
            return
        if state in (Qt.CheckState.PartiallyChecked, Qt.CheckState.PartiallyChecked.value):
            return
        should_check = state in (Qt.CheckState.Checked, Qt.CheckState.Checked.value)
        self._set_all_row_checks(should_check)

    def on_row_checkbox_state_changed(self, _state):
        if self._bulk_check_updating:
            return
        self.update_ui_state()

    def update_select_all_state_from_rows(self):
        if not hasattr(self, "chk_select_all_header"):
            return

        row_count = self.task_table.rowCount()
        self.chk_select_all_header.setEnabled(row_count > 0)
        if row_count == 0:
            self.chk_select_all_header.blockSignals(True)
            self.chk_select_all_header.setCheckState(Qt.CheckState.Unchecked)
            self.chk_select_all_header.blockSignals(False)
            return

        checked_count = 0
        for i in range(row_count):
            chk_widget = self.task_table.cellWidget(i, 0)
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
        self.chk_select_all_header.blockSignals(True)
        self.chk_select_all_header.setCheckState(state)
        self.chk_select_all_header.blockSignals(False)

    def _trim_log_area_if_needed(self):
        content = self.log_area.toPlainText()
        if len(content) <= self._max_log_chars:
            return
        self.log_area.setPlainText(content[-self._max_log_chars :])
        self.log_area.moveCursor(QTextCursor.End)

    def _append_case_excerpt(self, text):
        if not text:
            return
        self._current_case_log_excerpt += text
        if len(self._current_case_log_excerpt) > self._max_case_excerpt_chars:
            self._current_case_log_excerpt = self._current_case_log_excerpt[
                -self._max_case_excerpt_chars :
            ]

    def _format_seconds(self, seconds):
        seconds = max(0, int(seconds))
        hh = seconds // 3600
        mm = (seconds % 3600) // 60
        ss = seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    def _update_progress_eta(self):
        total = len(self.batch_queue)
        current = self.current_batch_index + 1 if self.current_batch_index >= 0 else 0
        if total <= 0:
            self.prog_bar_lbl.setText("目前項目中共有 0 個待處理任務")
            return

        if self.completed_case_durations:
            avg_seconds = sum(self.completed_case_durations) / len(self.completed_case_durations)
            remaining_cases = max(0, total - len(self.completed_case_durations))
            remaining_seconds = int(avg_seconds * remaining_cases)
            eta_at = (datetime.now() + timedelta(seconds=remaining_seconds)).strftime("%H:%M")
            eta_text = (
                f"目前進度：第 {current} / {total} 個任務 | "
                f"預估剩餘 {self._format_seconds(remaining_seconds)} | "
                f"預計完成 {eta_at}"
            )
            self.prog_bar_lbl.setText(eta_text)
            return
        self.prog_bar_lbl.setText(f"目前進度：第 {current} / {total} 個任務")

    def _prepare_session_log(self):
        if not self.source_root_path:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(self.source_root_path) / "totalseg_batch_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.session_log_path = log_dir / f"batch_{ts}.log"
        self.session_log_path.write_text("", encoding="utf-8")

    def _write_session_log(self, message):
        if not self.session_log_path:
            return
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.session_log_path.open("a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            # Logging should not break the batch flow.
            pass

    def _record_case_success(self, case_label, dicom_path, seconds):
        self._write_session_log(
            f"SUCCESS | case={case_label} | dicom={dicom_path} | seconds={seconds:.2f}"
        )

    def _record_case_failure(self, case_label, dicom_path, reason, excerpt):
        entry = {
            "case_label": case_label,
            "dicom_path": dicom_path,
            "reason": reason,
        }
        self.failed_cases.append(entry)
        self._write_session_log(
            f"FAIL | case={case_label} | dicom={dicom_path} | reason={reason}"
        )
        if excerpt:
            self._write_session_log("ERROR_SNIPPET_START")
            self._write_session_log(excerpt[-6000:])
            self._write_session_log("ERROR_SNIPPET_END")

    def handle_process_error(self, _error):
        self.process_error_message = self.process.errorString()
        if self.process_error_message:
            self.append_log(f"[錯誤] 子程序異常：{self.process_error_message}\n")

    def setup_seg_page(self):
        layout = QHBoxLayout(self.page_seg)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Left Column: Config
        left_col = QFrame()
        left_col.setFixedWidth(350)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Input Selection
        io_group = QGroupBox("1. 影像資料來源")
        io_layout = QVBoxLayout(io_group)
        
        self.btn_select_src = QPushButton("選擇 DICOM 資料夾")
        self.btn_select_src.setMinimumHeight(48)
        self.btn_select_src.clicked.connect(self.select_source)
        io_layout.addWidget(self.btn_select_src)

        self.src_label = QLabel("尚未選擇來源路徑")
        self.src_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        self.src_label.setWordWrap(True)
        io_layout.addWidget(self.src_label)
        
        left_layout.addWidget(io_group)

        # AI Settings
        cfg_group = QGroupBox("2. AI 分割參數設定")
        cfg_layout = QVBoxLayout(cfg_group)
        
        grid_layout = QFormLayout()
        grid_layout.setSpacing(10)
        
        self.modality_combo = QComboBox()
        self.modality_combo.addItems(["CT", "MRI"])
        self.modality_combo.setMaxVisibleItems(12)
        self.modality_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        grid_layout.addRow("影像類別:", self.modality_combo)
        
        self.task_combo = QComboBox()
        self.task_combo.setMaxVisibleItems(12)
        self.task_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        grid_layout.addRow("分割任務:", self.task_combo)
        
        self.modality_combo.currentTextChanged.connect(self.apply_modality_filter)
        self.apply_modality_filter(self.modality_combo.currentText())
        cfg_layout.addLayout(grid_layout)

        self.chk_spine = QCheckBox("標註脊椎層級（固定啟用）")
        self.chk_spine.setChecked(True)
        self.chk_spine.setEnabled(False)
        self.chk_fast = QCheckBox("快速推論模式（已移出主流程）")
        self.chk_fast.setChecked(False)
        self.chk_fast.setEnabled(False)
        self.chk_fast.setVisible(False)
        self.chk_draw = QCheckBox("自動產生影像疊加圖（固定啟用）")
        self.chk_draw.setChecked(True)
        self.chk_draw.setEnabled(False)
        
        cfg_layout.addWidget(self.chk_spine)
        cfg_layout.addWidget(self.chk_draw)

        erosion_box = QHBoxLayout()
        erosion_box.addWidget(QLabel("肌肉收縮迭代 (Erosion):"))
        self.erosion_input = QLineEdit("2")
        self.erosion_input.setFixedWidth(40)
        self.erosion_input.textChanged.connect(self.calc_erosion)
        erosion_box.addWidget(self.erosion_input)
        cfg_layout.addLayout(erosion_box)
        
        self.erosion_mm_label = QLabel("預估邊緣收縮: N/A")
        self.erosion_mm_label.setStyleSheet("color: #198754; font-size: 11px;")
        cfg_layout.addWidget(self.erosion_mm_label)

        # Slice Range Selection
        range_box = QGroupBox("切片範圍計算 (選填)")
        range_box.setCheckable(True)
        range_box.setChecked(False)
        range_layout = QHBoxLayout(range_box)
        range_layout.addWidget(QLabel("從"))
        self.slice_start_input = QLineEdit("1")
        self.slice_start_input.setFixedWidth(40)
        self.slice_start_input.setValidator(QIntValidator(1, 999999, self))
        range_layout.addWidget(self.slice_start_input)
        range_layout.addWidget(QLabel("至"))
        self.slice_end_input = QLineEdit("")
        self.slice_end_input.setPlaceholderText("末")
        self.slice_end_input.setFixedWidth(40)
        self.slice_end_input.setValidator(QIntValidator(1, 999999, self))
        range_layout.addWidget(self.slice_end_input)
        range_layout.addWidget(QLabel("張"))
        cfg_layout.addWidget(range_box)
        self.range_box_widget = range_box

        left_layout.addWidget(cfg_group)
        
        # Output Group (Optional/Hidden)
        self.out_group = QGroupBox("3. 輸出路徑設定 (選填)")
        self.out_group.setCheckable(True)
        self.out_group.setChecked(False)
        out_layout = QVBoxLayout(self.out_group)
        self.btn_select_out = QPushButton("修改輸出存放目錄")
        self.btn_select_out.clicked.connect(self.select_output)
        out_layout.addWidget(self.btn_select_out)
        self.out_label = QLabel("預設：於來源路徑旁產生 _output 檔案夾")
        self.out_label.setStyleSheet("font-size: 10px; color: #666;")
        out_layout.addWidget(self.out_label)
        left_layout.addWidget(self.out_group)
        self.out_group.setVisible(False)

        update_group = QGroupBox("4. 版本與更新")
        update_layout = QVBoxLayout(update_group)

        self.update_status_lbl = QLabel(f"目前版本：v{APP_VERSION}")
        self.update_status_lbl.setWordWrap(True)
        self.update_status_lbl.setStyleSheet("color: #495057; font-size: 11px;")
        update_layout.addWidget(self.update_status_lbl)

        self.update_hint_lbl = QLabel("可在此檢查最新正式版並更新。")
        self.update_hint_lbl.setWordWrap(True)
        self.update_hint_lbl.setStyleSheet("color: #6c757d; font-size: 11px;")
        update_layout.addWidget(self.update_hint_lbl)

        update_button_row = QHBoxLayout()
        self.btn_check_update = QPushButton("檢查更新")
        self.btn_check_update.clicked.connect(self.refresh_update_status)
        update_button_row.addWidget(self.btn_check_update)

        self.btn_install_update = QPushButton("更新到最新正式版")
        self.btn_install_update.clicked.connect(self.install_latest_release_update)
        self.btn_install_update.setEnabled(False)
        update_button_row.addWidget(self.btn_install_update)
        update_layout.addLayout(update_button_row)

        self.btn_open_releases = QPushButton("開啟 Releases 頁面")
        self.btn_open_releases.clicked.connect(self.open_releases_page)
        update_layout.addWidget(self.btn_open_releases)

        left_layout.addWidget(update_group)
        
        left_layout.addStretch()
        layout.addWidget(left_col)

        # Right Column: Queue
        right_col = QFrame()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)

        queue_header_layout = QHBoxLayout()
        self.chk_select_all_header = QCheckBox("全選")
        self.chk_select_all_header.setTristate(True)
        self.chk_select_all_header.setCheckState(Qt.CheckState.Unchecked)
        self.chk_select_all_header.setEnabled(False)
        self.chk_select_all_header.stateChanged.connect(self.on_select_all_state_changed)
        queue_header_layout.addWidget(self.chk_select_all_header)
        queue_header_layout.addStretch()
        right_layout.addLayout(queue_header_layout)
        
        # Task Table
        self.task_table = QTableWidget(0, 3)
        self.task_table.setHorizontalHeaderLabels(["", "病患 / 影像路徑", "處理狀態"])
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.task_table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Table Styling
        self.task_table.setShowGrid(False)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet("alternate-background-color: #fafbfc; selection-background-color: #e7f1ff;")
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.task_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.task_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        right_layout.addWidget(self.task_table)

        # Progress
        self.prog_bar_lbl = QLabel("待處理任務清單")
        right_layout.addWidget(self.prog_bar_lbl)
        self.pbar = QProgressBar()
        right_layout.addWidget(self.pbar)

        self.btn_start = QPushButton("啟動 AI 自動分割任務")
        self.btn_start.setObjectName("primary_btn")
        self.btn_start.setMinimumHeight(65)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_unified_process)
        right_layout.addWidget(self.btn_start)

        layout.addWidget(right_col)

    def setup_compare_page(self):
        layout = QVBoxLayout(self.page_compare)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header_lbl = QLabel("人工標註與 AI 自動分割比對分析")
        header_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        layout.addWidget(header_lbl)
        
        desc_lbl = QLabel(
            "請選取 AI 與人工標註的單一 NIfTI (.nii/.nii.gz) 或 NRRD (.nrrd) 檔案，"
            "系統將計算 Dice 系數與面積差異。"
        )
        desc_lbl.setStyleSheet("color: #6c757d;")
        layout.addWidget(desc_lbl)
        
        comp_group = QGroupBox("比對檔案選取")
        comp_layout = QFormLayout(comp_group)
        comp_layout.setSpacing(15)
        
        # AI Mask Path
        self.ai_mask_path_lbl = QLabel("尚未選取檔案")
        self.ai_mask_path_lbl.setWordWrap(True)
        self.btn_select_compare_ai = QPushButton("選取 AI 比對檔案 (.nii.gz)")
        self.btn_select_compare_ai.clicked.connect(self.select_compare_ai)
        comp_layout.addRow(self.btn_select_compare_ai, self.ai_mask_path_lbl)
        
        # Manual Mask Path
        self.manual_mask_path_lbl = QLabel("尚未選取檔案")
        self.manual_mask_path_lbl.setWordWrap(True)
        self.btn_select_compare_manual = QPushButton("選取人工比對檔案 (NIfTI/NRRD)")
        self.btn_select_compare_manual.clicked.connect(self.select_compare_manual)
        comp_layout.addRow(self.btn_select_compare_manual, self.manual_mask_path_lbl)
        
        layout.addWidget(comp_group)

        # Action
        self.btn_run_compare = QPushButton("開始執行影像比對分析")
        self.btn_run_compare.setObjectName("primary_btn")
        self.btn_run_compare.setMinimumHeight(55)
        self.btn_run_compare.setEnabled(False)
        self.btn_run_compare.clicked.connect(self.run_compare_analysis)
        layout.addWidget(self.btn_run_compare)
        
        layout.addStretch()

    # --- Comparison Methods ---
    def select_compare_ai(self):
        path, _ = QFileDialog.getOpenFileName(self, "選取 AI 比對檔案 (.nii.gz)", "", "NIfTI GZ (*.nii.gz)")
        if path:
            self.compare_ai_mask = path
            self.ai_mask_path_lbl.setText(path)
            self.check_compare_ready()

    def select_compare_manual(self):
        path, _ = QFileDialog.getOpenFileName(self, "選取人工比對檔案 (NIfTI/NRRD)", "", "Medical Images (*.nii *.nii.gz *.nrrd)")
        if path:
            self.compare_manual_mask = path
            self.manual_mask_path_lbl.setText(path)
            self.check_compare_ready()

    def check_compare_ready(self):
        self.btn_run_compare.setEnabled(bool(self.compare_ai_mask and self.compare_manual_mask))

    def run_compare_analysis(self):
        self.log_area.clear()
        self.append_log("[INFO] Starting compare analysis...\n")
        self.btn_run_compare.setEnabled(False)

        try:
            result = core_compare_masks(self.compare_ai_mask, self.compare_manual_mask)
            slice_idx = int(result["slice_index_1based"])
            dice = float(result["dice"])
            ai_area = float(result["ai_area_cm2"])
            manual_area = float(result["manual_area_cm2"])

            self.append_log(f"[INFO] Slice: {slice_idx}\n")
            self.append_log("-" * 40 + "\n")
            self.append_log(f"AI area: {ai_area:.2f} cm2\n")
            self.append_log(f"Manual area: {manual_area:.2f} cm2\n")
            self.append_log(f"Dice: {dice:.4f} (max 1.0)\n")
            self.append_log("-" * 40 + "\n")

            if dice >= 0.9:
                self.append_log("<span style='color: #198754; font-weight: bold;'>Excellent overlap (Dice >= 0.9)</span><br>", is_html=True)
            elif dice >= 0.8:
                self.append_log("<span style='color: #0d6efd; font-weight: bold;'>Good overlap (Dice >= 0.8)</span><br>", is_html=True)
            else:
                self.append_log("<span style='color: #dc3545; font-weight: bold;'>Low overlap. Please review masks.</span><br>", is_html=True)

        except Exception as e:
            self.append_log(f"[ERROR] Compare failed: {str(e)}\n")
        finally:
            self.btn_run_compare.setEnabled(True)

    def select_source(self):
        path = QFileDialog.getExistingDirectory(self, "請選取 DICOM 資料夾或病患根目錄")
        if path:
            self.source_root_path = path
            self.src_label.setText(path)
            parent_dir = Path(path).parent
            self.out_label.setText(str(parent_dir / (Path(path).name + "_output")))
            self.scan_directory(path)

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "請選取輸出資料存放根目錄")
        if folder:
            self.out_label.setText(folder)

    def has_dicom_files(self, folder):
        return core_has_dicom_files(folder)

    def get_dicom_slice_count(self, folder):
        return core_get_dicom_slice_count(folder)

    def normalize_slice_range(self, start_str, end_str, slice_count):
        start_val, end_val, err = core_normalize_slice_range(start_str, end_str, slice_count)
        warn_message = None
        end_text = (end_str or "").strip()
        if (
            err is None
            and slice_count
            and slice_count > 0
            and end_text.isdigit()
            and int(end_text) > slice_count
        ):
            warn_message = (
                f"?????? {int(end_text)} ??????????????{slice_count}???????????{slice_count}??"
            )
        if err:
            return None, None, None, err
        return start_val, end_val, warn_message, None

    def scan_directory(self, root_path):
        self.task_table.setRowCount(0)
        self.folder_slice_counts = {}
        root = Path(root_path)
        case_items = core_scan_dicom_cases(root)
        valid_folders = [item.folder for item in case_items]

        if not valid_folders:
            self.append_log("[警示] 未在所選路徑偵測到 DICOM 影像檔。\n")
            self.btn_start.setEnabled(False)
            self.update_select_all_state_from_rows()
            return

        self.task_table.setRowCount(len(valid_folders))
        for i, item in enumerate(case_items):
            folder = item.folder
            slice_count = item.slice_count
            self.folder_slice_counts[str(folder)] = slice_count
            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.task_table.setCellWidget(i, 0, chk_widget)
            chk.stateChanged.connect(self.on_row_checkbox_state_changed)

            display_name = item.label

            if slice_count and slice_count > 0:
                display_name = f"{display_name} ({slice_count} 張)"
                
            path_item = QTableWidgetItem(display_name)
            path_item.setData(Qt.UserRole, str(folder))
            self.task_table.setItem(i, 1, path_item)
            
            if slice_count and slice_count > 0:
                status_text = f"待處理 (共 {slice_count} 張)"
            else:
                status_text = "待處理 (Ready)"
            status_item = QTableWidgetItem(status_text)
            self.task_table.setItem(i, 2, status_item)
            
        self.update_ui_state()

        if len(valid_folders) == 1:
            only_key = str(valid_folders[0])
            only_count = self.folder_slice_counts.get(only_key)
            if only_count and only_count > 0:
                self.slice_start_input.setText("1")
                self.slice_end_input.setText(str(only_count))
                self.range_box_widget.setTitle(f"切片範圍計算 (選填)｜單一病患共 {only_count} 張")
                self.append_log(f"[系統] 已載入單一病患，共 {only_count} 張切片，切片範圍已預填為 1 ~ {only_count}。\n")
            else:
                self.range_box_widget.setTitle("切片範圍計算 (選填)")
        else:
            self.range_box_widget.setTitle("切片範圍計算 (選填)｜多病患將逐案自動夾限")
            self.slice_end_input.setText("")
            self.slice_end_input.setPlaceholderText("依各病患上限自動夾限")
            self.append_log("[系統] 多病患模式：切片範圍會依每位病患切片上限自動限制。\n")

        # 精進 Spacing 偵測邏輯，解決 ITK 無法識別單一檔案導致 N/A 的問題
        if sitk:
            try:
                reader = sitk.ImageSeriesReader()
                # 使用 SeriesReader 抓取 DICOM 系列檔案通常比 ReadImage(單檔) 更穩定
                dicom_names = reader.GetGDCMSeriesFileNames(str(valid_folders[0]))
                if dicom_names:
                    # 讀取系列中的第一張圖來獲取中繼資料
                    first_img = sitk.ReadImage(dicom_names[0])
                    spacing = first_img.GetSpacing()
                    self.spacing_xy = (spacing[0], spacing[1])
                    self.append_log(f"[系統] 成功識別影像解析度: {spacing[0]:.2f} x {spacing[1]:.2f} mm\n")
                else:
                    self.spacing_xy = None
            except Exception:
                self.spacing_xy = None
                # 不在 Log 顯示冗長的錯誤，保持介面簡潔
        self.calc_erosion()

    def update_ui_state(self):
        checked_count = 0
        for i in range(self.task_table.rowCount()):
            chk_widget = self.task_table.cellWidget(i, 0)
            if not chk_widget or not chk_widget.layout():
                continue
            chk = chk_widget.layout().itemAt(0).widget()
            if chk is not None and chk.isChecked():
                checked_count += 1
        
        self.btn_start.setEnabled(checked_count > 0)
        self.prog_bar_lbl.setText(f"目前項目中共有 {checked_count} 個待處理任務")
        self.pbar.setMaximum(checked_count if checked_count > 0 else 1)
        self.pbar.setValue(0)
        self.update_select_all_state_from_rows()

    def calc_erosion(self):
        text = self.erosion_input.text()
        try:
            iters = int(text)
            if self.spacing_xy and iters >= 0:
                avg_spacing = (self.spacing_xy[0] + self.spacing_xy[1]) / 2.0
                approx_mm = iters * avg_spacing
                self.erosion_mm_label.setText(f"預估邊緣收縮: {approx_mm:.2f} mm")
            else:
                self.erosion_mm_label.setText("預估邊緣收縮: N/A")
        except ValueError:
            self.erosion_mm_label.setText("迭代數值錯誤")

    def apply_modality_filter(self, modality):
        current_task = self.task_combo.currentText()
        filtered_tasks = filter_tasks_by_modality(TASK_OPTIONS, modality)
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItems(filtered_tasks)
        if current_task in filtered_tasks:
            self.task_combo.setCurrentText(current_task)
        self.task_combo.blockSignals(False)

    def append_log(self, text, is_html=False):
        if self._ephemeral_active:
            self.log_area.moveCursor(QTextCursor.End)
            self.log_area.insertPlainText("\n")
            self._ephemeral_active = False
        self.log_area.moveCursor(QTextCursor.End)
        if is_html and hasattr(self.log_area, "appendHtml"):
            self.log_area.appendHtml(text)
        else:
            # QPlainTextEdit does not support appendHtml; fall back to plain text.
            self.log_area.insertPlainText(text)
        self.log_area.moveCursor(QTextCursor.End)
        self._trim_log_area_if_needed()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def refresh_update_status(self):
        self.btn_check_update.setEnabled(False)
        try:
            status = build_update_status(app_root=APP_ROOT, python_base_dir=BASE_DIR)
            self.update_status = status
            self.latest_release = status.release

            if status.latest_version is None:
                self.update_status_lbl.setText(f"目前版本：v{status.current_version}")
                self.update_hint_lbl.setText("目前無法取得最新正式版資訊。")
                self.btn_install_update.setEnabled(False)
                return

            self.update_status_lbl.setText(
                f"目前版本：v{status.current_version}｜最新正式版：v{status.latest_version}"
            )

            if not status.install_supported:
                self.update_hint_lbl.setText(status.install_block_reason or "目前環境不支援 GUI 更新。")
                self.btn_install_update.setEnabled(False)
                return

            if status.update_available:
                self.update_hint_lbl.setText("偵測到較新正式版，可更新到最新 release。")
                self.btn_install_update.setEnabled(True)
            else:
                self.update_hint_lbl.setText("目前已是最新正式版。")
                self.btn_install_update.setEnabled(False)
        except Exception as e:
            self.update_status = None
            self.latest_release = None
            self.update_status_lbl.setText(f"目前版本：v{APP_VERSION}")
            self.update_hint_lbl.setText(f"檢查更新失敗：{e}")
            self.btn_install_update.setEnabled(False)
        finally:
            self.btn_check_update.setEnabled(True)

    def open_releases_page(self):
        target_url = "https://github.com/proadress/totalseg-muscle-tool/releases"
        if self.update_status is not None:
            target_url = self.update_status.release_page_url
        webbrowser.open(target_url)

    def install_latest_release_update(self):
        self.refresh_update_status()
        status = self.update_status
        if status is None or status.release is None:
            QMessageBox.warning(self, "更新失敗", "目前無法取得最新 release 資訊。")
            return
        if not status.install_supported:
            QMessageBox.information(
                self,
                "目前環境不支援 GUI 更新",
                status.install_block_reason or "這個安裝型態不支援 GUI 更新。",
            )
            return
        if not status.update_available:
            QMessageBox.information(self, "已是最新版本", "目前已是最新正式版。")
            return

        confirm = QMessageBox.question(
            self,
            "確認更新",
            (
                f"目前版本：v{status.current_version}\n"
                f"最新正式版：v{status.latest_version}\n\n"
                "程式會下載最新 release，關閉目前視窗後完成更新並重新啟動。"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            release = status.release
            work_dir = Path(tempfile.mkdtemp(prefix="totalseg_release_gui_"))
            zip_path = download_release_zip(release, work_dir / f"{release.tag_name}.zip")
            payload_root = extract_release_payload(zip_path, work_dir / "extract")
            spawn_release_update(
                app_root=APP_ROOT,
                payload_root=payload_root,
                current_pid=os.getpid(),
                launcher_path=APP_ROOT / "START 啟動.bat",
            )
        except Exception as e:
            QMessageBox.critical(self, "更新失敗", str(e))
            self.append_log(f"[錯誤] 更新失敗：{e}\n")
            return

        QMessageBox.information(
            self,
            "開始更新",
            "已啟動更新程序。主視窗關閉後會套用最新正式版並重新開啟。",
        )
        self.close()

    def start_unified_process(self):
        self.log_area.clear()
        self.is_running = True
        self._retry_same_task = False
        self.btn_start.setEnabled(False)
        self.btn_start.setText("初始化 AI 環境中...")
        self.batch_started_at = datetime.now()
        self.case_started_at = None
        self.completed_case_durations = []
        self.failed_cases = []
        self.session_log_path = None
        self.process_error_message = ""
        self._current_case_log_excerpt = ""
        
        self.batch_queue = []
        for i in range(self.task_table.rowCount()):
            chk_widget = self.task_table.cellWidget(i, 0)
            if not chk_widget or not chk_widget.layout():
                continue
            chk = chk_widget.layout().itemAt(0).widget()
            if chk is not None and chk.isChecked():
                dicom_path = self.task_table.item(i, 1).data(Qt.UserRole)
                case_label = self.task_table.item(i, 1).text()
                slice_count = self.folder_slice_counts.get(str(dicom_path))
                # seg.py 會自行組成 <dicom_name>_output；這裡只傳入父層根目錄
                out_path = str(Path(dicom_path).parent)

                self.batch_queue.append((i, dicom_path, out_path, slice_count, case_label))

        if not self.batch_queue:
            self.append_log("[警示] 尚未勾選任何病人，無法開始批次。\n")
            self.reset_ui()
            return

        self._prepare_session_log()
        self._write_session_log(
            f"BATCH_START | total_cases={len(self.batch_queue)} | source={self.source_root_path}"
        )

        self.current_batch_index = -1
        QTimer.singleShot(100, self.run_setup_and_segmentation)

    def run_setup_and_segmentation(self):
        try:
            if shutil.which("uv") is None:
                self.append_log("[錯誤] 找不到 uv，請先執行啟動器完成環境同步。\n")
                self.reset_ui()
                return
            self.append_log("環境檢查完成，開始執行分割任務...\n")
            self.run_next_batch_task()
        except Exception as e:
            self.append_log(f"[異常中斷] {str(e)}\n")
            self.reset_ui()

    def handle_stdout(self):
        self.drain_process_output()

    def handle_stderr(self):
        # MergedChannels mode routes stderr into stdout.
        return

    def append_stream_log(self, text):
        clean = ANSI_ESCAPE_RE.sub("", text)
        if not clean:
            return
        self._append_case_excerpt(clean)
        self._consume_stream_text(clean)

    def _consume_stream_text(self, text):
        for ch in text:
            if ch == "\r":
                if self._stream_line_buffer:
                    self._render_ephemeral_line(self._stream_line_buffer)
                    self._stream_line_buffer = ""
                continue
            if ch == "\n":
                self._commit_stream_line(self._stream_line_buffer)
                self._stream_line_buffer = ""
                continue
            self._stream_line_buffer += ch

    def _replace_last_line(self, text):
        content = self.log_area.toPlainText()
        if not content:
            new_content = text
        elif content.endswith("\n"):
            new_content = content + text
        else:
            parts = content.rsplit("\n", 1)
            prefix = parts[0] + "\n" if len(parts) == 2 else ""
            new_content = prefix + text
        self.log_area.setPlainText(new_content)
        self.log_area.moveCursor(QTextCursor.End)
        self._trim_log_area_if_needed()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def _render_ephemeral_line(self, text):
        if not text:
            return
        if self._ephemeral_active:
            self._replace_last_line(text)
            return

        existing = self.log_area.toPlainText()
        if existing and not existing.endswith("\n"):
            self.log_area.moveCursor(QTextCursor.End)
            self.log_area.insertPlainText("\n")
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.insertPlainText(text)
        self.log_area.moveCursor(QTextCursor.End)
        self._ephemeral_active = True
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def _commit_stream_line(self, text):
        if self._ephemeral_active:
            if text:
                self._replace_last_line(text)
            self.log_area.moveCursor(QTextCursor.End)
            self.log_area.insertPlainText("\n")
            self.log_area.moveCursor(QTextCursor.End)
            self._ephemeral_active = False
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)
            return
        self.log_area.moveCursor(QTextCursor.End)
        if text:
            self.log_area.insertPlainText(text)
        self.log_area.insertPlainText("\n")
        self.log_area.moveCursor(QTextCursor.End)
        self._trim_log_area_if_needed()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def drain_process_output(self):
        chunk = bytes(self.process.readAll()).decode("utf8", errors="replace")
        if not chunk:
            return
        self._stream_buffer += chunk
        self.append_stream_log(self._stream_buffer)
        self._stream_buffer = ""

    def fix_macos_torch_perms(self):
        """自動修復 macOS 上 torch_shm_manager 的執行權限"""
        try:
            # 尋找 venv 中的 torch bin 目錄
            torch_bin = BASE_DIR / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "torch" / "bin" / "torch_shm_manager"
            if torch_bin.exists():
                subprocess.run(["chmod", "+x", str(torch_bin)], check=True)
                self.append_log("[系統] 已自動修復 macOS PyTorch 核心執行權限。\n")
        except Exception as e:
            self.append_log(f"[警告] 自動修復權限失敗: {str(e)}\n")

    def diagnose_error(self, log_text):
        """掃描 Log 內容並提供白話解決建議"""
        suggestions = []
        for key, advice in self.solutions.items():
            if key in log_text:
                suggestions.append(advice)
        
        if suggestions:
            self.append_log("\n" + "─"*30)
            self.append_log("\n<span style='font-size: 14px; font-weight: bold;'>智慧診斷報告：</span>\n", is_html=True)
            for s in suggestions:
                # 使用 HTML 呈現黃色強調背景
                self.append_log(f"<div style='background-color: #fff3cd; color: #856404; padding: 5px; border-radius: 5px;'>{s}</div><br>", is_html=True)
            self.append_log("─"*30 + "\n")

    def _classify_totalseg_error(self, log_text):
        text = (log_text or "").lower()
        if (
            "jsondecodeerror" in text
            and "totalsegmentator" in text
            and "config.py" in text
        ):
            return "totalseg_config_json_broken"
        if (
            "requires a license" in text
            or "not openly available" in text
            or "missing_license" in text
            or "invalid_license" in text
            or "license number" in text
        ):
            return "license_missing_or_invalid"
        return None

    def _totalseg_config_path(self):
        return Path.home() / ".totalsegmentator" / "config.json"

    def _build_default_totalseg_config(self):
        return {
            "totalseg_id": "totalseg_" + "".join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            ),
            "send_usage_stats": True,
            "prediction_counter": 0,
        }

    def repair_totalseg_config_if_broken(self):
        cfg_path = self._totalseg_config_path()
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

        if not cfg_path.exists():
            cfg = self._build_default_totalseg_config()
            cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            return True, f"[系統] 已建立 TotalSegmentator 設定檔: {cfg_path}\n"

        try:
            json.loads(cfg_path.read_text(encoding="utf-8"))
            return True, ""
        except Exception:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = cfg_path.parent / f"config.broken_{ts}.json"
            try:
                backup.write_text(cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

            cfg = self._build_default_totalseg_config()
            cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            return True, (
                f"[系統] 偵測到損壞設定檔，已重建: {cfg_path}\n"
                f"[系統] 損壞檔案備份於: {backup}\n"
            )

    def _mask_license_key(self, key):
        if not key:
            return ""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    def apply_totalseg_license(self, license_key):
        if shutil.which("uv") is None:
            return False, "找不到 uv，無法寫入授權金鑰。"

        script = (
            "import os; "
            "from totalsegmentator.config import set_license_number; "
            "set_license_number(os.environ['TOTALSEG_LICENSE_KEY'])"
        )
        env = {k: v for k, v in os.environ.items()}
        env["TOTALSEG_LICENSE_KEY"] = license_key

        try:
            result = subprocess.run(
                ["uv", "run", "--no-sync", "python", "-c", script],
                cwd=str(BASE_DIR),
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout:
                self.append_log(result.stdout + ("" if result.stdout.endswith("\n") else "\n"))
            if result.stderr:
                self.append_log(result.stderr + ("" if result.stderr.endswith("\n") else "\n"))
            return True, ""
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            return False, (stderr or stdout or "授權寫入失敗。")

    def prompt_totalseg_license_and_maybe_retry(self):
        dialog = LicenseInputDialog(self)
        if dialog.exec() != QDialog.Accepted:
            self.append_log("[系統] 已取消授權設定，停止本次任務。\n")
            self.reset_ui()
            return True

        key = parse_license_input(dialog.get_license_key())
        if not key:
            QMessageBox.warning(self, "輸入錯誤", "請輸入有效的授權金鑰或指令。")
            self.reset_ui()
            return True
        ok, message = self.apply_totalseg_license(key)
        if not ok:
            QMessageBox.critical(self, "授權設定失敗", message)
            self.append_log(f"[錯誤] 授權設定失敗: {message}\n")
            self.reset_ui()
            return True

        self.append_log(f"[系統] 授權金鑰已設定: {self._mask_license_key(key)}\n")

        retry = QMessageBox.question(
            self,
            "授權設定完成",
            "授權已更新。要立即重跑剛剛失敗的任務嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if retry == QMessageBox.Yes:
            self.retry_current_failed_task()
        else:
            self.append_log("[系統] 授權已更新，請手動重新啟動任務。\n")
            self.reset_ui()
        return True

    def retry_current_failed_task(self):
        if self.current_batch_index < 0 or self.current_batch_index >= len(self.batch_queue):
            self.append_log("[錯誤] 找不到可重跑的任務索引。\n")
            self.reset_ui()
            return
        self._retry_same_task = True
        self.btn_start.setEnabled(False)
        self.append_log("[系統] 授權已更新，重新執行上一個失敗任務...\n")
        QTimer.singleShot(0, self.run_next_batch_task)

    def process_finished(self):
        self.drain_process_output()
        if self._stream_buffer:
            self.append_stream_log(self._stream_buffer)
            self._stream_buffer = ""
        if self._stream_line_buffer:
            self._commit_stream_line(self._stream_line_buffer)
            self._stream_line_buffer = ""
        self._ephemeral_active = False
        self.stream_timer.stop()
        if self.process_state == "sync":
            if self.process.exitCode() == 0:
                # macOS 特殊處理：修復 torch_shm_manager 權限
                if sys.platform == "darwin":
                    self.fix_macos_torch_perms()
                self.run_next_batch_task()
            else:
                self.reset_ui()
        elif self.process_state == "seg":
            if self.current_batch_index >= 0:
                row, dicom_path, _out_path, _slice_count, case_label = self.batch_queue[self.current_batch_index]
                elapsed = 0.0
                if self.case_started_at is not None:
                    elapsed = max(0.0, (datetime.now() - self.case_started_at).total_seconds())
                self.completed_case_durations.append(elapsed)
                if self.process.exitCode() == 0:
                    status = "處理完成"
                    self.task_table.item(row, 2).setText(status)
                    self.task_table.item(row, 2).setForeground(QColor("#198754"))
                    self._record_case_success(case_label, dicom_path, elapsed)
                else:
                    status = "處理失敗"
                    self.task_table.item(row, 2).setText(status)
                    self.task_table.item(row, 2).setForeground(QColor("#dc3545"))
                    log_text = self._current_case_log_excerpt or self.log_area.toPlainText()
                    self.diagnose_error(log_text)
                    issue = self._classify_totalseg_error(log_text)
                    reason = f"exit_code={self.process.exitCode()}"
                    if self.process_error_message:
                        reason += f", qprocess={self.process_error_message}"
                    if issue == "totalseg_config_json_broken":
                        _, msg = self.repair_totalseg_config_if_broken()
                        if msg:
                            self.append_log(msg)
                        reason += ", issue=totalseg_config_json_broken"
                    elif issue == "license_missing_or_invalid":
                        reason += ", issue=license_missing_or_invalid"
                    self._record_case_failure(
                        case_label=case_label,
                        dicom_path=dicom_path,
                        reason=reason,
                        excerpt=log_text,
                    )
                    self.append_log(f"[錯誤] {case_label} 失敗，已記錄至批次 log。\n")
                    if issue == "license_missing_or_invalid":
                        self.prompt_totalseg_license_and_maybe_retry()
                        return
            self._update_progress_eta()
            
            self.run_next_batch_task()

    def run_next_batch_task(self):
        if self._retry_same_task:
            self._retry_same_task = False
        else:
            self.current_batch_index += 1
        if self.current_batch_index < len(self.batch_queue):
            row, dicom_path, out_path, slice_count, case_label = self.batch_queue[self.current_batch_index]
            self.task_table.item(row, 2).setText("執行分割中...")
            self.task_table.item(row, 2).setForeground(QColor("#0d6efd"))
            self.case_started_at = datetime.now()
            self.process_error_message = ""
            self._current_case_log_excerpt = ""
            self._write_session_log(
                f"CASE_START | index={self.current_batch_index + 1}/{len(self.batch_queue)} "
                f"| case={case_label} | dicom={dicom_path}"
            )
            self._update_progress_eta()
            self.pbar.setValue(self.current_batch_index)
            
            slice_start = None
            slice_end = None

            # 1. 切片範圍防呆 (Slice Range Guard)
            if self.range_box_widget.isChecked():
                start_str = self.slice_start_input.text()
                end_str = self.slice_end_input.text()
                start_val, end_val, warn_message, error_message = self.normalize_slice_range(
                    start_str=start_str,
                    end_str=end_str,
                    slice_count=slice_count,
                )

                if error_message:
                    self.task_table.item(row, 2).setText("切片範圍錯誤")
                    self.task_table.item(row, 2).setForeground(QColor("#dc3545"))
                    self.append_log(f"[錯誤] {case_label}: {error_message}\n")
                    self.completed_case_durations.append(0.0)
                    self._record_case_failure(
                        case_label=case_label,
                        dicom_path=dicom_path,
                        reason=f"slice_range_error: {error_message}",
                        excerpt=error_message,
                    )
                    self._update_progress_eta()
                    QTimer.singleShot(0, self.run_next_batch_task)
                    return

                if warn_message:
                    self.append_log(f"[??] {case_label}: {warn_message}\n")

                slice_start = start_val
                slice_end = end_val

            cmd_args = build_seg_command(
                dicom_path=dicom_path,
                out_path=out_path,
                task=self.task_combo.currentText(),
                modality=self.modality_combo.currentText(),
                spine=self.chk_spine.isChecked(),
                fast=self.chk_fast.isChecked(),
                auto_draw=self.chk_draw.isChecked(),
                erosion_iters=self.erosion_input.text(),
                slice_start=slice_start,
                slice_end=slice_end,
            )

            self.process_state = "seg"
            self._stream_buffer = ""
            self._stream_line_buffer = ""
            self._ephemeral_active = False
            self.stream_timer.start()
            self.process.start("uv", cmd_args)
        else:
            total = len(self.batch_queue)
            failed = len(self.failed_cases)
            succeeded = total - failed
            elapsed = 0.0
            if self.batch_started_at is not None:
                elapsed = max(0.0, (datetime.now() - self.batch_started_at).total_seconds())
            self.append_log("\n[完成] 所有自動分割任務已處理完畢。\n")
            self.append_log(
                f"[統計] 成功 {succeeded} / 失敗 {failed} / 總數 {total}，總耗時 {self._format_seconds(elapsed)}。\n"
            )
            if self.session_log_path:
                self.append_log(f"[系統] 批次 log：{self.session_log_path}\n")
            self._write_session_log(
                f"BATCH_END | total={total} | success={succeeded} | failed={failed} | elapsed_sec={elapsed:.2f}"
            )
            self.pbar.setValue(len(self.batch_queue))
            self.reset_ui()

    def reset_ui(self):
        self.is_running = False
        self.stream_timer.stop()
        self._stream_buffer = ""
        self._stream_line_buffer = ""
        self._ephemeral_active = False
        self.btn_start.setText("啟動 AI 自動分割任務")
        self.btn_start.setEnabled(True)
        self.btn_select_src.setEnabled(True)

    def closeEvent(self, event):
        if self.process.state() == QProcess.Running:
            self.process.kill()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TotalSegApp()
    window.show()
    sys.exit(app.exec())

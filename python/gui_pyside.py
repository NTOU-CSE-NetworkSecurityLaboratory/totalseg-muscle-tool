import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEventLoop, QProcess, QProcessEnvironment, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.app_version import read_local_app_version
from core.gui_batch_controller import GuiBatchController
from core.gui_case_scan_controller import GuiCaseScanController
from core.gui_compare_controller import GuiCompareController
from core.gui_license_service import (
    apply_totalseg_license as apply_totalseg_license_impl,
)
from core.gui_license_service import (
    classify_totalseg_error as classify_totalseg_error_impl,
)
from core.gui_license_service import (
    parse_license_input,
)
from core.gui_license_service import (
    repair_totalseg_config_if_broken as repair_totalseg_config_if_broken_impl,
)
from core.gui_log_stream import GuiLogStreamController
from core.gui_page_builders import build_compare_page, build_seg_page
from core.gui_queue_ui_controller import GuiQueueUiController
from core.gui_update_controller import GuiUpdateController
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


class SettingsDialog(QDialog):
    def __init__(self, parent=None, *, app_version: str):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setModal(True)
        self.resize(520, 260)

        layout = QVBoxLayout(self)

        header = QLabel("版本與更新")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057;")
        layout.addWidget(header)

        self.update_status_lbl = QLabel(f"目前版本：v{app_version}")
        self.update_status_lbl.setWordWrap(True)
        self.update_status_lbl.setStyleSheet("color: #495057; font-size: 11px;")
        layout.addWidget(self.update_status_lbl)

        self.update_hint_lbl = QLabel("可在此檢查最新正式版並更新。")
        self.update_hint_lbl.setWordWrap(True)
        self.update_hint_lbl.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(self.update_hint_lbl)

        update_button_row = QHBoxLayout()
        self.btn_check_update = QPushButton("檢查更新")
        update_button_row.addWidget(self.btn_check_update)
        self.btn_install_update = QPushButton("更新到最新正式版")
        self.btn_install_update.setEnabled(False)
        update_button_row.addWidget(self.btn_install_update)
        layout.addLayout(update_button_row)

        self.btn_open_releases = QPushButton("開啟 Releases 頁面")
        layout.addWidget(self.btn_open_releases)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("關閉")
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

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
        self.app_version = APP_VERSION
        self.ansi_escape_re = ANSI_ESCAPE_RE
        self.text_cursor_end = QTextCursor.End
        self.qt_user_role = Qt.UserRole
        self._build_seg_command = build_seg_command

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
        self.log_stream = GuiLogStreamController(self)
        self.batch_controller = GuiBatchController(self)
        self.case_scan_controller = GuiCaseScanController(
            self,
            scan_dicom_cases=core_scan_dicom_cases,
            sitk_module=sitk,
        )
        self.queue_ui_controller = GuiQueueUiController(self)
        self.compare_controller = GuiCompareController(
            self,
            compare_masks=core_compare_masks,
        )
        self.settings_dialog = SettingsDialog(self, app_version=APP_VERSION)
        self.update_status_lbl = self.settings_dialog.update_status_lbl
        self.update_hint_lbl = self.settings_dialog.update_hint_lbl
        self.btn_check_update = self.settings_dialog.btn_check_update
        self.btn_install_update = self.settings_dialog.btn_install_update
        self.btn_open_releases = self.settings_dialog.btn_open_releases
        self.btn_check_update.clicked.connect(self.refresh_update_status)
        self.btn_install_update.clicked.connect(self.install_latest_release_update)
        self.btn_open_releases.clicked.connect(self.open_releases_page)
        self.update_controller = GuiUpdateController(
            self,
            app_root=APP_ROOT,
            base_dir=BASE_DIR,
            app_version=APP_VERSION,
        )

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

        self.btn_settings = QPushButton("設定")
        self.btn_settings.setFixedHeight(36)
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        nav_layout.addWidget(self.btn_settings)
        
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

    def open_settings_dialog(self):
        self.refresh_update_status()
        self.settings_dialog.exec()

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
        self.queue_ui_controller.set_all_row_checks(checked)

    def on_select_all_state_changed(self, state):
        self.queue_ui_controller.on_select_all_state_changed(state)

    def on_row_checkbox_state_changed(self, _state):
        self.queue_ui_controller.on_row_checkbox_state_changed(_state)

    def update_select_all_state_from_rows(self):
        self.queue_ui_controller.update_select_all_state_from_rows()

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
        return self.queue_ui_controller.format_seconds(seconds)

    def _update_progress_eta(self):
        self.queue_ui_controller.update_progress_eta()

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
        self.batch_controller.handle_process_error(_error)

    def setup_seg_page(self):
        build_seg_page(self)

    def setup_compare_page(self):
        build_compare_page(self)

    # --- Comparison Methods ---
    def select_compare_ai(self):
        self.compare_controller.select_compare_ai()

    def select_compare_manual(self):
        self.compare_controller.select_compare_manual()

    def check_compare_ready(self):
        self.compare_controller.check_compare_ready()

    def run_compare_analysis(self):
        self.compare_controller.run_compare_analysis()

    def select_source(self):
        self.case_scan_controller.select_source()

    def select_output(self):
        self.case_scan_controller.select_output()

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
        self.case_scan_controller.scan_directory(root_path)

    def update_ui_state(self):
        self.case_scan_controller.update_ui_state()

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
        self.update_controller.refresh_update_status()

    def open_releases_page(self):
        self.update_controller.open_releases_page()

    def install_latest_release_update(self):
        self.update_controller.install_latest_release_update()

    def start_unified_process(self):
        self.batch_controller.start_unified_process()

    def run_setup_and_segmentation(self):
        self.batch_controller.run_setup_and_segmentation()

    def handle_stdout(self):
        self.drain_process_output()

    def handle_stderr(self):
        # MergedChannels mode routes stderr into stdout.
        return

    def append_stream_log(self, text):
        self.log_stream.append_stream_log(text)

    def _consume_stream_text(self, text):
        self.log_stream._consume_stream_text(text)

    def _replace_last_line(self, text):
        self.log_stream._replace_last_line(text)

    def _render_ephemeral_line(self, text):
        self.log_stream._render_ephemeral_line(text)

    def _commit_stream_line(self, text):
        self.log_stream._commit_stream_line(text)

    def drain_process_output(self):
        self.log_stream.drain_process_output()

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
        return classify_totalseg_error_impl(log_text)

    def _totalseg_config_path(self):
        return Path.home() / ".totalsegmentator" / "config.json"

    def repair_totalseg_config_if_broken(self):
        return repair_totalseg_config_if_broken_impl(self._totalseg_config_path())

    def _mask_license_key(self, key):
        if not key:
            return ""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    def apply_totalseg_license(self, license_key):
        ok, message = apply_totalseg_license_impl(license_key, base_dir=BASE_DIR)
        if ok and message:
            self.append_log(message)
        return ok, ("" if ok else message)

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
        self.batch_controller.process_finished()

    def run_next_batch_task(self):
        self.batch_controller.run_next_batch_task()

    def reset_ui(self):
        self.batch_controller.reset_ui()

    def closeEvent(self, event):
        if self.process.state() == QProcess.Running:
            self.process.kill()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TotalSegApp()
    window.show()
    sys.exit(app.exec())

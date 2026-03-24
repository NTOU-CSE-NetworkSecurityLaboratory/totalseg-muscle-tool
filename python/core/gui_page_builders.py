from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)


def build_seg_page(window) -> None:
    layout = QHBoxLayout(window.page_seg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(30)

    left_col = QFrame()
    left_col.setFixedWidth(350)
    left_layout = QVBoxLayout(left_col)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(15)

    io_group = QGroupBox("1. 影像資料來源")
    io_layout = QVBoxLayout(io_group)
    window.btn_select_src = QPushButton("選擇 DICOM 資料夾")
    window.btn_select_src.setMinimumHeight(48)
    window.btn_select_src.clicked.connect(window.select_source)
    io_layout.addWidget(window.btn_select_src)

    window.src_label = QLabel("尚未選擇來源路徑")
    window.src_label.setStyleSheet("color: #6c757d; font-size: 11px;")
    window.src_label.setWordWrap(True)
    io_layout.addWidget(window.src_label)
    left_layout.addWidget(io_group)

    cfg_group = QGroupBox("2. AI 分割參數設定")
    cfg_layout = QVBoxLayout(cfg_group)
    grid_layout = QFormLayout()
    grid_layout.setSpacing(10)

    window.modality_combo = QComboBox()
    window.modality_combo.addItems(["CT", "MRI"])
    window.modality_combo.setMaxVisibleItems(12)
    window.modality_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    grid_layout.addRow("影像類別:", window.modality_combo)

    window.task_combo = QComboBox()
    window.task_combo.setMaxVisibleItems(12)
    window.task_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    grid_layout.addRow("分割任務:", window.task_combo)
    window.modality_combo.currentTextChanged.connect(window.apply_modality_filter)
    window.apply_modality_filter(window.modality_combo.currentText())
    cfg_layout.addLayout(grid_layout)

    pipeline_summary = QLabel(
        "正式流程固定包含：肌肉分割、脊椎標註、CSV 輸出、PNG 疊圖。"
    )
    pipeline_summary.setWordWrap(True)
    pipeline_summary.setStyleSheet("color: #495057; font-size: 11px;")
    cfg_layout.addWidget(pipeline_summary)

    erosion_box = QHBoxLayout()
    erosion_box.addWidget(QLabel("肌肉收縮迭代 (Erosion):"))
    window.erosion_input = QLineEdit("2")
    window.erosion_input.setFixedWidth(40)
    window.erosion_input.textChanged.connect(window.calc_erosion)
    erosion_box.addWidget(window.erosion_input)
    cfg_layout.addLayout(erosion_box)

    window.erosion_mm_label = QLabel("預估邊緣收縮: N/A")
    window.erosion_mm_label.setStyleSheet("color: #198754; font-size: 11px;")
    cfg_layout.addWidget(window.erosion_mm_label)

    window.range_box_widget = QGroupBox("切片範圍計算 (選填)")
    window.range_box_widget.setCheckable(True)
    window.range_box_widget.setChecked(False)
    range_layout = QHBoxLayout(window.range_box_widget)
    range_layout.addWidget(QLabel("從"))
    window.slice_start_input = QLineEdit("1")
    window.slice_start_input.setFixedWidth(40)
    window.slice_start_input.setValidator(QIntValidator(1, 999999, window))
    range_layout.addWidget(window.slice_start_input)
    range_layout.addWidget(QLabel("至"))
    window.slice_end_input = QLineEdit("")
    window.slice_end_input.setPlaceholderText("末")
    window.slice_end_input.setFixedWidth(40)
    window.slice_end_input.setValidator(QIntValidator(1, 999999, window))
    range_layout.addWidget(window.slice_end_input)
    range_layout.addWidget(QLabel("張"))
    cfg_layout.addWidget(window.range_box_widget)
    left_layout.addWidget(cfg_group)

    window.out_group = QGroupBox("3. 輸出路徑設定 (選填)")
    window.out_group.setCheckable(True)
    window.out_group.setChecked(False)
    out_layout = QVBoxLayout(window.out_group)
    window.btn_select_out = QPushButton("修改輸出存放目錄")
    window.btn_select_out.clicked.connect(window.select_output)
    out_layout.addWidget(window.btn_select_out)
    window.out_label = QLabel("預設：於來源路徑旁產生 _output 檔案夾")
    window.out_label.setStyleSheet("font-size: 10px; color: #666;")
    out_layout.addWidget(window.out_label)
    left_layout.addWidget(window.out_group)
    window.out_group.setVisible(False)

    left_layout.addStretch()
    layout.addWidget(left_col)

    right_col = QFrame()
    right_layout = QVBoxLayout(right_col)
    right_layout.setContentsMargins(0, 0, 0, 0)
    queue_header_layout = QHBoxLayout()
    window.chk_select_all_header = QCheckBox("全選")
    window.chk_select_all_header.setTristate(True)
    window.chk_select_all_header.setCheckState(Qt.CheckState.Unchecked)
    window.chk_select_all_header.setEnabled(False)
    window.chk_select_all_header.stateChanged.connect(window.on_select_all_state_changed)
    queue_header_layout.addWidget(window.chk_select_all_header)
    queue_header_layout.addStretch()
    right_layout.addLayout(queue_header_layout)

    window.task_table = QTableWidget(0, 3)
    window.task_table.setHorizontalHeaderLabels(["", "病患 / 影像路徑", "處理狀態"])
    header = window.task_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.Fixed)
    window.task_table.setColumnWidth(0, 40)
    header.setSectionResizeMode(1, QHeaderView.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    window.task_table.setShowGrid(False)
    window.task_table.setAlternatingRowColors(True)
    window.task_table.setStyleSheet(
        "alternate-background-color: #fafbfc; selection-background-color: #e7f1ff;"
    )
    window.task_table.verticalHeader().setVisible(False)
    window.task_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    window.task_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    window.task_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    right_layout.addWidget(window.task_table)

    window.prog_bar_lbl = QLabel("待處理任務清單")
    right_layout.addWidget(window.prog_bar_lbl)
    window.pbar = QProgressBar()
    right_layout.addWidget(window.pbar)

    window.btn_start = QPushButton("啟動 AI 自動分割任務")
    window.btn_start.setObjectName("primary_btn")
    window.btn_start.setMinimumHeight(65)
    window.btn_start.setEnabled(False)
    window.btn_start.clicked.connect(window.start_unified_process)
    right_layout.addWidget(window.btn_start)
    layout.addWidget(right_col)


def build_compare_page(window) -> None:
    layout = QVBoxLayout(window.page_compare)
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

    window.ai_mask_path_lbl = QLabel("尚未選取檔案")
    window.ai_mask_path_lbl.setWordWrap(True)
    window.btn_select_compare_ai = QPushButton("選取 AI 比對檔案 (.nii.gz)")
    window.btn_select_compare_ai.clicked.connect(window.compare_controller.select_compare_ai)
    comp_layout.addRow(window.btn_select_compare_ai, window.ai_mask_path_lbl)

    window.manual_mask_path_lbl = QLabel("尚未選取檔案")
    window.manual_mask_path_lbl.setWordWrap(True)
    window.btn_select_compare_manual = QPushButton("選取人工比對檔案 (NIfTI/NRRD)")
    window.btn_select_compare_manual.clicked.connect(window.compare_controller.select_compare_manual)
    comp_layout.addRow(window.btn_select_compare_manual, window.manual_mask_path_lbl)

    layout.addWidget(comp_group)

    window.btn_run_compare = QPushButton("開始執行影像比對分析")
    window.btn_run_compare.setObjectName("primary_btn")
    window.btn_run_compare.setMinimumHeight(55)
    window.btn_run_compare.setEnabled(False)
    window.btn_run_compare.clicked.connect(window.compare_controller.run_compare_analysis)
    layout.addWidget(window.btn_run_compare)
    layout.addStretch()

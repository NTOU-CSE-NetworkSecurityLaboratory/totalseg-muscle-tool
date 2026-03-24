# TotalSeg Muscle Tool (v0.1.2)

[English](#english) | [中文](#中文)

---

## English

A medical image segmentation tool based on TotalSegmentator for CT image muscle segmentation analysis.

### Features

#### **Tool 1: Unified AI Analysis (Unified UI)**
- **MRI & CT Support**: Select modality to automatically use `total_mr` or standard CT models.
- **Partial Volume Calculation**: Specify a slice range (e.g., Slices 10-50) for targeted volumetric analysis.
  - Single-patient mode auto-fills total slice count (`1 ~ N`).
  - Multi-patient mode applies per-case slice limit clamping automatically.
- **Smart Detection**: Recursive scanning of nested folders and identification of extension-less DICOMs.
- **Solution Engine**: Professional error diagnosis that translates technical logs into medical-friendly advice.
- **Manual vs AI Comparison**: Integrated DICE coefficient and area difference analysis.
  - AI compare file is constrained to `.nii.gz`.
- **App Icon Support**: Place `app_icon.ico` (or `app_icon.png`) in repo root or `python/` to auto-apply icon.

### Quick Start

#### **Windows**
Double-click `START 啟動.bat` to launch the WebView shell. Background dependencies will be auto-managed on first run via `uv`.

#### **Doctor Quick Guide**
1. Double-click `START 啟動.bat`
2. Select the DICOM folder
3. Choose cases to process
4. Select `CT` or `MRI`
5. Set slice range if needed
6. Click `Start`
7. Review outputs and logs on the right

### System Requirements

- **OS**: Windows 10/11
- **Python**: 3.10
- **GPU**: NVIDIA GPU recommended (CUDA support), CPU also supported
- **Network**: Required for first-time installation

### Output Description

#### **Tool 1: AI Segmentation Output**

Example: Input `SER00005/`, output will be created in `SER00005_output/`:

- `segmentation_<task>/`: One mask per structure (`*.nii.gz`) and `statistics.json`
- `segmentation_spine/`: Spine segmentation masks
- `mask_<task>.csv`: Main analysis CSV (4 sections)
  - Section 1: Area per slice (cm²)
  - Section 2: Average HU per slice (with erosion, weighted by area for L/R muscles)
  - Section 3: HU standard deviation per slice (with erosion, weighted by area)
  - Section 4: Overall summary (pixelcount / volume_cm³ / mean_hu, L/R muscles combined)
- `mask_spine_fast.csv`: Spine CSV
- `png/`: One PNG overlay per slice

#### **Tool 2: Batch Processing Output**

Results displayed in real-time in GUI and saved in root folder:
- `batch_processing_log_YYYYMMDD_HHMMSS.txt` - Detailed log
- `batch_processing_results_YYYYMMDD_HHMMSS.json` - Statistics (JSON format)

#### **Tool 3: Comparison Tool Output**

Results displayed in real-time in GUI:
- Slice Number: Manual annotation slice index
- Manual Area (cm²): Manually annotated muscle area
- AI Area (cm²): TotalSegmentator segmentation area on same slice
- Dice Score: Similarity between masks (formula: `2 * |A ∩ B| / (|A| + |B|)`)

Fixed pipeline behavior:
- spine output is always enabled
- PNG overlay generation is always enabled
- fast mode is removed from the normal workflow

### Calculation Logic

- **Area (cm²)**: Mask pixels per slice × `spacing_x × spacing_y / 100`
- **Volume (cm³)**: Total mask pixels × `spacing_x × spacing_y × spacing_z / 1000`
- **Slice average HU**: Morphological erosion on mask (default 2 iterations, reduced to 3 or none if too few pixels), then average HU of eroded region
- **Slice HU std**: Same erosion process, then standard deviation of HU in eroded region
- **L/R muscle merge (HU)**: Area-weighted average for each slice
- **Summary merge (mean_hu)**: Weighted by pixelcount

### Project Structure

```text
totalseg-muscle-tool/
├── START 啟動.bat
└── python/
    ├── pywebview_tailwind_shell/   # WebView GUI
    ├── seg.py                      # Segmentation core
    ├── draw.py                     # PNG overlay
    └── pyproject.toml              # Dependencies
```

### Testing & Quality Checks

```bash
cd python
uv run pytest -q
uv run ruff check .
uv run basedpyright .
```

Core tests include:
- command assembly (`test_auto_draw_cmd.py`)
- GUI smoke checks for defaults/copy/path rules (`test_gui_pyside_smoke.py`)
- slice ordering / PNG naming behavior (`test_seg_draw_slice_behavior.py`)

### FAQ

#### **Tool 1 (AI Segmentation)**
- **Non-ASCII path causing drawing failure**: `draw.py` checks if path is ASCII. Move project/DICOM to pure English path.
- **Slow on first run**: TotalSegmentator may need to download model weights, and CPU inference is very slow.
- **GPU/CPU detection**: GUI displays detected device (`torch.cuda.is_available()`).
- **License-gated tasks (e.g. `tissue_4_types`)**: GUI now shows a license dialog with a clickable official link (`https://backend.totalsegmentator.com/license-academic/`), supports pasting either a raw key or a command (`totalseg_set_license -l <KEY>`), then can retry the failed case.
- **`JSONDecodeError` from TotalSegmentator config**: GUI auto-repairs broken `~/.totalsegmentator/config.json` and prompts license input again.

#### **Tool 2 (Batch Processing)**
- **No DICOM folders found**: Check max search depth setting or folder structure.
- **Some cases failed**: Check log file for specific error messages.

#### **Tool 3 (Manual vs AI Comparison)**
- **Dice score lower than expected**: (1) Slice mismatch, (2) Different segmentation scope, (3) Poor AI quality. Check overlap in 3D Slicer.
- **Spacing inconsistency warning**: When spacing differs >10%, program auto-resamples. Confirm both files are from same DICOM series.
- **Multi-slice warning**: Program designed for single-slice comparison. If manual annotation has multiple slices, first slice is automatically selected.

### Notes

> This project is for research/development purposes. Do not use for clinical diagnosis.

### License

This project is open source for research and educational purposes.

---

## 中文

基於 TotalSegmentator 的醫學影像分割小工具，用於 CT 影像的肌肉分割分析。

### 功能特色

#### **功能 1：統一 AI 分析介面 (Unified UI)**
- **MRI & CT 雙模態支援**：切換影像類別自動調用 `total_mr` 或 CT 專屬模型。
- **特定切片範圍計算**：可指定張數範圍（如第 20 到 40 張）進行精確的局部體積統計。
  - 單一病患載入時會自動預填 `1 ~ 總張數`。
  - 多病患模式會依每位病患切片上限自動防呆夾限。
- **強健掃描邏輯**：自動識別深層嵌套目錄與無副檔名的 DICOM 檔案。
- **智慧診斷引擎**：發生報錯時自動提供白話文「解決建議」，不需閱讀代碼。
- **手動 vs AI 比較**：整合 DICE 系數與面積差異分析（AI 比對檔案限定 `.nii.gz`）。
- **應用程式圖示支援**：在專案根目錄或 `python/` 放置 `app_icon.ico`（或 `app_icon.png`）即可自動套用。

### 快速開始

#### **Windows**
雙擊執行 `START 啟動.bat` 啟動程式。首次執行會自動完成環境配置。

#### **醫師快速操作**
1. 雙擊 `START 啟動.bat`
2. 按 `選擇 DICOM 資料夾` 載入病例
3. 勾選要處理的病例
4. 選擇 `CT` 或 `MRI`
5. 視需要設定切片範圍
6. 按 `開始` 執行
7. 在右側查看輸出與執行記錄

> **溫馨提示**：若啟動失敗或無法讀取檔案，建議將解壓縮後的資料夾移至 **C 槽或 D 槽等純英文路徑下**執行，以避免 Windows 中文路徑造成的不可預期錯誤。

### 系統需求

- **作業系統**：Windows 10/11
- **Python**：3.10
- **GPU**：建議使用 NVIDIA GPU（支援 CUDA），也支援 CPU
- **網路**：第一次安裝時需要

### 輸出說明

#### **工具 1：AI 分割輸出**

範例：輸入 `SER00005/`，輸出會建立在 `SER00005_output/`：

- `segmentation_<task>/`：每個結構一個遮罩（`*.nii.gz`）與 `statistics.json`
- `segmentation_spine/`：脊椎分割遮罩
- `mask_<task>.csv`：主要分析 CSV（4 個區塊）
  - 區塊 1：每層面積（cm²）
  - 區塊 2：每層平均 HU（經侵蝕處理，左右肌肉按面積加權合併）
  - 區塊 3：每層 HU 標準差（經侵蝕處理，左右肌肉按面積加權合併）
  - 區塊 4：整體摘要（pixelcount / volume_cm³ / mean_hu，左右肌肉合併）
- `mask_spine_fast.csv`：脊椎 CSV
- `png/`：每層一張疊圖 PNG

#### **工具 2：批次處理輸出**

結果即時顯示在 GUI 並儲存於根目錄：
- `batch_processing_log_YYYYMMDD_HHMMSS.txt` - 詳細日誌
- `batch_processing_results_YYYYMMDD_HHMMSS.json` - 結果統計（JSON 格式）

#### **工具 3：比較工具輸出**

結果即時顯示在 GUI：
- 層數（Slice Number）：手動標註的層數索引
- 手動面積（cm²）：醫生手動標註的肌肉面積
- AI 面積（cm²）：TotalSegmentator 在同一層的分割面積
- Dice 分數：兩個遮罩的相似度（公式：`2 * |A ∩ B| / (|A| + |B|)`）

固定流程：
- 一定會做脊椎分割
- 一定會產生 CSV
- 一定會產生 PNG 疊圖
- `fast` 不在正式流程中

### 計算邏輯

- **面積（cm²）**：每層遮罩像素數 × `spacing_x × spacing_y / 100`
- **體積（cm³）**：所有遮罩像素數 × `spacing_x × spacing_y × spacing_z / 1000`
- **層平均 HU**：對該層遮罩做形態學侵蝕（預設 2 次，像素太少會降為 3 次或不侵蝕），取侵蝕後區域的 HU 平均
- **層 HU 標準差**：同上侵蝕流程，取侵蝕後區域的 HU 標準差
- **左右合併（HU）**：以每層的左右面積做加權平均
- **摘要合併（mean_hu）**：以 pixelcount 做加權平均

### 專案結構

```text
totalseg-muscle-tool/
├── START 啟動.bat
└── python/
    ├── pywebview_tailwind_shell/   # WebView 介面
    ├── seg.py                      # 分割核心
    ├── draw.py                     # PNG 疊圖
    └── pyproject.toml              # 依賴套件
```

### 測試

```bash
cd python
uv run pytest -q
```

目前核心測試包含：
- 命令組裝測試（`test_auto_draw_cmd.py`）
- GUI smoke 測試（`test_gui_pyside_smoke.py`，含預設值/文案/路徑規則）

### 常見問題

#### **工具 1（AI 分割）**
- **路徑含中文/特殊字元導致畫圖失敗**：`draw.py` 會檢查路徑是否為 ASCII。請將專案或 DICOM 移到純英文路徑。
- **第一次跑很慢**：TotalSegmentator 可能需要下載模型權重，且 CPU 推論會非常耗時。
- **GPU/CPU 判斷**：GUI 會顯示偵測到的裝置（`torch.cuda.is_available()`）。

#### **工具 2（批次處理）**
- **找不到 DICOM 資料夾**：檢查最大搜尋深度設定或資料夾結構。
- **部分案例失敗**：查看日誌檔案了解具體錯誤訊息。

#### **工具 3（手動 vs AI 比較）**
- **Dice 分數低於預期**：可能原因：(1) 手動標註與 AI 分割的層數不一致、(2) 分割範圍定義不同、(3) AI 分割品質較差。建議在 3D Slicer 中檢視重疊情況。
- **spacing 不一致警告**：當 spacing 差異超過 10% 時會顯示警告。程式會自動重採樣對齊，但仍建議確認兩個檔案是否來自同一個 DICOM series。
- **多層標註警告**：程式設計為只比較單層。如果手動標註包含多層，會自動選擇第一層。

### 注意事項

> 本專案屬研究/開發用途，請勿直接做臨床診斷依據。

### 授權

本專案開源供研究與教育用途使用。

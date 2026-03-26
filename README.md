# TotalSeg Muscle Tool (v0.1.5)

[English](#english) | [中文](#中文)

---

## English

A medical image segmentation tool based on TotalSegmentator for CT/MRI muscle segmentation and analysis.

### Features

- **Three-tab WebView UI**: 自動分割 (Segmentation) / 匯出 CSV/PNG (Export) / 單層面積比對 (Compare)
- **MRI & CT Support**: Select modality to automatically use `total_mr` or standard CT models.
- **Partial Volume Calculation**: Specify a slice range for targeted volumetric analysis.
  - Single-case mode auto-fills total slice count (`1 ~ N`).
  - Multi-case mode applies per-case slice limit clamping automatically.
- **Smart Scanning**: Recursive scan with `_output` folder exclusion; uses GDCM series detection to avoid false positives.
- **Error Diagnosis**: Translates technical errors into actionable advice (license, CUDA OOM, permission denied).
- **Manual vs AI Comparison**: DICE coefficient and area difference for single-slice comparison.
- **Auto Update**: In-app update via GitHub Releases.

### Quick Start

#### **Windows**
Double-click `START 啟動.bat`. Dependencies are auto-managed on first run via `uv`.

#### **Doctor Quick Guide**

**Step 1 — Segmentation (自動分割 tab)**
1. Double-click `START 啟動.bat`
2. Click `選擇來源資料夾` to load DICOM cases
3. Check the cases to process
4. Select `CT` or `MRI` and choose a task
5. Click `開始`

**Step 2 — Export CSV/PNG (匯出 CSV/PNG tab)**
1. Switch to the `匯出 CSV/PNG` tab
2. Select the same folder
3. Choose task and adjust parameters (erosion, slice range, HU threshold) if needed
4. Click `開始` — outputs are always overwritten with current settings

**Compare (單層面積比對 tab)**
1. Switch to the `單層面積比對` tab
2. Select the AI mask file (`.nii.gz`) and manual single-slice mask
3. Click `執行比對`

### System Requirements

- **OS**: Windows 10/11
- **Python**: 3.10
- **GPU**: NVIDIA GPU recommended (CUDA support), CPU also supported
- **Network**: Required for first-time installation

> **Note**: Move the project to a pure ASCII path (e.g. `C:\tools\`) to avoid issues with Chinese/special characters in paths.

### Output Structure

Example: Input `SER00005/`, output created in `SER00005_output/`:

```
SER00005_output/
├── spine.json                          # Spine slice labels
├── segmentation_spine_fast/            # Spine masks (*.nii.gz)
└── segmentation_<task>/
    ├── *.nii.gz                        # One mask per structure
    ├── volume_<task>.csv               # Area (cm²) and volume (cm³) per structure
    ├── hu_<task>.csv                   # HU statistics per structure
    ├── png/                            # Overlay PNGs with legend and spine label
    ├── png_eroded/                     # Same with morphological erosion applied
    ├── png_nolabel/                    # Overlay PNGs without legend
    └── png_eroded_nolabel/             # Eroded PNGs without legend
```

#### CSV Format

`volume_<task>.csv` — Area per slice (cm²) and total volume (cm³) per structure.

`hu_<task>.csv` — Per-slice mean HU and std HU (with erosion), plus summary statistics.

### Calculation Logic

- **Area (cm²)**: Mask pixels per slice × `spacing_x × spacing_y / 100`
- **Volume (cm³)**: Total mask pixels × `spacing_x × spacing_y × spacing_z / 1000`
- **Slice HU**: Morphological erosion on mask (default 2 iterations, auto-reduced if too few pixels remain), then mean/std of the eroded region
- **L/R muscle merge**: Area-weighted average per slice

### Project Structure

```
totalseg-muscle-tool/
├── START 啟動.bat
└── python/
    ├── pywebview_tailwind_shell/   # WebView UI (main entry point)
    ├── core/                       # Shared pipeline logic
    ├── seg.py                      # Step 1: Segmentation CLI
    ├── export.py                   # Step 2: CSV + PNG export CLI
    ├── draw.py                     # PNG overlay generation
    └── pyproject.toml              # Dependencies
```

### Testing & Quality

```bash
cd python
uv run python -m pytest -q
uv run ruff check .
uv run python -m basedpyright
```

### FAQ

- **Non-ASCII path error**: Move project/DICOM to a pure English path.
- **Slow first run**: TotalSegmentator downloads model weights on first use. CPU inference is very slow.
- **License-gated task**: A license dialog appears automatically. Paste raw key or `totalseg_set_license -l <KEY>`, then retry.
- **`JSONDecodeError` from TotalSegmentator config**: Auto-repaired on next run.
- **Re-export with different parameters**: Switch to `匯出 CSV/PNG` tab, adjust params, and click Start — outputs are always overwritten.
- **Compare: Dice lower than expected**: Check for slice mismatch, different segmentation scope, or poor AI quality. Verify in 3D Slicer.

### Notes

> This project is for research/development purposes. Do not use for clinical diagnosis.

### License

Open source for research and educational purposes.

---

## 中文

基於 TotalSegmentator 的醫學影像分割工具，用於 CT/MRI 影像的肌肉分割與分析。

### 功能特色

- **三 Tab WebView 介面**：自動分割 / 匯出 CSV/PNG / 單層面積比對
- **MRI & CT 雙模態**：切換影像類別自動調用 `total_mr` 或 CT 專屬模型
- **特定切片範圍計算**：可指定張數範圍進行精確局部統計
  - 單一病例自動預填 `1 ~ 總張數`
  - 多病例模式依各病例切片上限自動夾限
- **強健掃描邏輯**：自動排除 `_output` 資料夾；使用 GDCM series 偵測避免誤判
- **智慧診斷引擎**：自動將錯誤轉換為可操作的解決建議（授權、GPU OOM、權限問題）
- **手動 vs AI 比較**：單層 DICE 係數與面積差異分析
- **自動更新**：從 GitHub Releases 進行應用程式內更新

### 快速開始

#### **Windows**
雙擊 `START 啟動.bat`。首次執行會透過 `uv` 自動完成環境配置。

#### **醫師快速操作**

**步驟一 — 分割（自動分割 tab）**
1. 雙擊 `START 啟動.bat`
2. 點擊 `選擇來源資料夾` 載入 DICOM 病例
3. 勾選要處理的病例
4. 選擇 `CT` 或 `MRI`，選擇分割任務
5. 點擊 `開始`

**步驟二 — 匯出（匯出 CSV/PNG tab）**
1. 切換到 `匯出 CSV/PNG` tab
2. 選擇同一個資料夾
3. 視需要調整參數（侵蝕次數、切片範圍、HU 閾值）
4. 點擊 `開始` — 輸出結果會依當前參數直接覆蓋

**比對（單層面積比對 tab）**
1. 切換到 `單層面積比對` tab
2. 選擇 AI mask 檔案（`.nii.gz`）與醫師手畫的單層 mask
3. 點擊 `執行比對`

> **注意**：建議將解壓縮後的資料夾移至 **C 槽或 D 槽等純英文路徑**，以避免中文路徑造成的錯誤。

### 系統需求

- **作業系統**：Windows 10/11
- **Python**：3.10
- **GPU**：建議使用 NVIDIA GPU（支援 CUDA），也支援 CPU
- **網路**：第一次安裝時需要

### 輸出結構

範例：輸入 `SER00005/`，輸出建立於 `SER00005_output/`：

```
SER00005_output/
├── spine.json                          # 脊椎切片標籤
├── segmentation_spine_fast/            # 脊椎遮罩（*.nii.gz）
└── segmentation_<task>/
    ├── *.nii.gz                        # 各結構遮罩
    ├── volume_<task>.csv               # 各結構每層面積與總體積
    ├── hu_<task>.csv                   # 各結構 HU 統計
    ├── png/                            # 帶圖例與脊椎標籤的疊圖 PNG
    ├── png_eroded/                     # 同上，套用形態學侵蝕
    ├── png_nolabel/                    # 不含圖例的疊圖 PNG
    └── png_eroded_nolabel/             # 不含圖例的侵蝕版本
```

#### CSV 格式

`volume_<task>.csv` — 各結構每層面積（cm²）與總體積（cm³）。

`hu_<task>.csv` — 各結構每層平均 HU 與 HU 標準差（侵蝕後），以及摘要統計。

### 計算邏輯

- **面積（cm²）**：每層遮罩像素數 × `spacing_x × spacing_y / 100`
- **體積（cm³）**：所有遮罩像素數 × `spacing_x × spacing_y × spacing_z / 1000`
- **層 HU**：對該層遮罩做形態學侵蝕（預設 2 次，像素太少會自動降低），取侵蝕後區域的 HU 均值/標準差
- **左右合併**：以每層左右面積做加權平均

### 專案結構

```
totalseg-muscle-tool/
├── START 啟動.bat
└── python/
    ├── pywebview_tailwind_shell/   # WebView 介面（主入口）
    ├── core/                       # 共用流程邏輯
    ├── seg.py                      # 步驟一：分割 CLI
    ├── export.py                   # 步驟二：CSV + PNG 匯出 CLI
    ├── draw.py                     # PNG 疊圖生成
    └── pyproject.toml              # 依賴套件
```

### 測試與品質檢查

```bash
cd python
uv run python -m pytest -q
uv run ruff check .
uv run python -m basedpyright
```

### 常見問題

- **路徑含中文/特殊字元**：請將專案或 DICOM 移到純英文路徑。
- **第一次跑很慢**：TotalSegmentator 需要下載模型權重，CPU 推論非常耗時。
- **需要授權**：授權對話框會自動出現，貼上金鑰或 `totalseg_set_license -l <KEY>` 指令後重試。
- **TotalSegmentator config 損壞**：下次執行時會自動修復。
- **改參數重跑步驟二**：切換到 `匯出 CSV/PNG` tab，調整參數，點擊開始即可（永遠覆蓋舊結果）。
- **比對 Dice 偏低**：確認層數是否對齊、分割範圍定義是否相同，建議用 3D Slicer 檢視重疊情況。

### 注意事項

> 本專案屬研究/開發用途，請勿直接做臨床診斷依據。

### 授權

本專案開源供研究與教育用途使用。

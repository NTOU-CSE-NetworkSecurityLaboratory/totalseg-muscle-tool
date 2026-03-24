# 功能盤點

這份文件列出目前專案「已存在」的功能，目的是在重構前先把功能範圍講清楚，避免重構時不小心改掉行為。

## 1. DICOM 掃描與病例發現

- 功能：
  - 掃描單一資料夾或根目錄下的 DICOM case
  - 支援 `.dcm` 與部分無副檔名 DICOM
  - 會略過 `_output` 與 `TotalSeg_Backend`
- 入口：
  - `core.shared_core.scan_dicom_cases`
  - PySide / webview 都依賴這個邏輯
- 責任層：
  - `shared_core`

## 2. Task / Modality 選擇

- 功能：
  - 依 modality 過濾可選 task
  - MRI 時會把部分 task 轉成對應 MR task
- 入口：
  - `core.shared_core.filter_tasks_by_modality`
  - `core.shared_core.resolve_task_for_modality`
- 責任層：
  - `shared_core`

## 3. Slice Range 正規化

- 功能：
  - 驗證 `slice_start / slice_end`
  - 自動依病例 slice 上限夾限
  - 可回傳 warning 與 error
- 入口：
  - `core.shared_core.normalize_slice_range`
  - `core.shared_core.normalize_slice_range_with_warning`
- 責任層：
  - `shared_core`

## 4. CLI 分割主流程

- 功能：
  - 讀取 DICOM case
  - 執行 TotalSegmentator
  - 匯出 segmentation masks
  - 匯出 `mask_<task>.csv`
  - 合併 `statistics.json`
  - 視參數觸發 auto-draw
- 入口：
  - `python/seg.py`
- 責任層：
  - `CLI core`

## 5. CLI PNG Overlay 流程

- 功能：
  - 讀取 DICOM 與 segmentation output
  - 為每張 slice 產生 overlay PNG
  - 可輸出 erosion 版本
  - 可限制輸出 slice 範圍
- 入口：
  - `python/draw.py`
- 責任層：
  - `CLI core`

## 6. CSV 匯出

- 功能：
  - 每 slice area
  - 每 slice mean HU
  - 每 slice HU std
  - summary volume / pixelcount / mean_hu
- 入口：
  - `seg.py` 內部 export 邏輯
- 責任層：
  - `CLI core`

## 7. GUI 批次執行

- 功能：
  - 掃描病例
  - 多病例勾選
  - 逐病例執行 CLI
  - 顯示進度、狀態、log
  - TotalSegmentator license prompt / retry
- 入口：
  - `python/gui_pyside.py`
- 責任層：
  - 目前是 `GUI shell + orchestration`
- 理想狀態：
  - 只保留 `GUI shell`

## 8. WebView 批次執行

- 功能：
  - 掃描病例
  - 多病例勾選
  - 逐病例執行 CLI
  - 顯示進度、狀態、log
  - TotalSegmentator license prompt / retry
- 入口：
  - `python/pywebview_tailwind_shell/backend/api.py`
- 責任層：
  - 目前是 `webview shell + orchestration`
- 理想狀態：
  - 只保留 `webview shell`

## 9. Compare 功能

- 功能：
  - AI mask 與 manual mask 比對
  - 計算 Dice
  - 取 manual 第一個有效 slice 做比較
- 入口：
  - `core.shared_core.compare_masks`
  - GUI / webview 使用這個 shared 函式
- 責任層：
  - `shared_core`

## 10. 測試現況

- 已有：
  - command builder 測試
  - GUI smoke tests
  - CLI slice behavior / main smoke tests
- 還缺：
  - 更完整的 CLI 契約測試
  - GUI / webview 薄殼化後的 orchestration contract tests

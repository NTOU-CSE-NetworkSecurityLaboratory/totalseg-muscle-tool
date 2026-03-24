# Developer Changelog

## v0.1.0 (2026-03-25)

- CLI fixed-pipeline refactor landed as the new core structure:
  - `seg.py` slimmed down into a thin CLI entrypoint
  - fixed pipeline orchestration moved into `python/core/`
  - output contract, request normalization, CSV service, and update/version helpers split into reusable modules
- CSV slice ordering no longer relies on a hard-coded reverse step:
  - spine evidence is now used to determine cranial/caudal direction
  - parity against the baseline output case was re-verified for CSV and PNG outputs
- PySide GUI was thinned into a controller-based shell:
  - batch, log stream, license, update, queue UI, and compare logic moved out of the main window file
  - settings now own version/update actions
- WebView shell was revived as an active pilot UI:
  - dashboard-style Chinese UI refresh
  - settings modal includes version, release update, and license actions
  - compare file dialog and license flow issues were fixed
- Version source is now treated consistently from `python/pyproject.toml`, with GUI/CLI/WebView reading the same app version.

## v0.0.2 (2026-03-02)

- GUI 文案統一為「比對分析」，比較頁面按鈕與訊息更新。
- 比對頁 AI 檔案選取改為限定 `.nii.gz`。
- 侵蝕預設值統一調整為 `2`（GUI + `seg.py` + `draw.py`）。
- 分割頁輸出路徑設定改為隱藏，執行時固定預設輸出規則。
- 切片範圍防呆強化：
  - 單一病患自動帶入總張數（`1 ~ N`）。
  - 多病患逐案套用切片上限，自動夾限超界值。
- 系統日誌區高度擴充，提升可視區域。
- 新增 app icon 自動載入邏輯（`app_icon.ico`/`app_icon.png`）。
- 新增 GUI smoke 測試，覆蓋預設值/文案/路徑與切片防呆規則。

## v0.0.1 (2026-02-24)

- 統一 GUI 為 `python/gui_pyside.py`，整合分割/批次/比較。
- 支援 MRI/CT 雙模態與切片範圍參數（`slice_start/slice_end`）。
- CSV 擴充為 4 區塊，加入 HU std 與摘要合併欄位。
- 修復 `draw.py` 語法錯誤與 auto-draw 參數傳遞問題。
- 新增 `pytest` 測試骨架與 `auto_draw_cmd` 參數測試。
- 部署策略改為原始碼 ZIP + `START 啟動.bat`（移除 EXE 打包流程）。

## 目前已知風險

- 摘要 `mean_hu` 與每層 HU 口徑不一致。
- 範圍外切片以 `0` 顯示，臨床解讀有誤解風險。

## 建議下一步（工程）

1. 讓摘要 `mean_hu` 可選擇「依 range 重算」模式。
2. CSV 加 metadata 區塊（range, erosion, modality, task）。
3. 範圍模式新增「只輸出區間切片」選項，避免 0 值誤讀。

## v0.0.4 (2026-03-23)

- Added `docs/REFRACTOR_FIXED_PIPELINE_SPEC.md` to lock the next product direction:
  - WebView removed from target architecture
  - fixed main pipeline becomes `DICOM -> segmentation -> CSV -> PNG`
  - spine / PNG treated as built-in workflow behavior
  - fast mode moved out of the normal product path
- Updated developer docs to point at the new fixed-pipeline direction.
- Added repo quality baseline planning for `ruff`, `basedpyright`, and stable `pytest` discovery.

## v0.0.3 (2026-03-05)

- Added WebView shell hardening and lifecycle cleanup:
  - Window close now triggers process shutdown.
  - Added backend `shutdown()` + `atexit` guard.
- Added license recovery flow in WebView:
  - Detect license-related failure.
  - Open license modal.
  - Apply key and retry failed case.
- Added TotalSegmentator config recovery in WebView backend.
- Added session log persistence (`totalseg_batch_logs/batch_*.log`).
- Improved log stream handling:
  - Keep tqdm-style carriage-return updates.
  - Ignore empty output lines to prevent timestamp-only spam.
- Refined UI structure:
  - Diagnostics moved into Runtime Logs card to reduce layout crowding.
  - Reduced saturation toward PySide-like blue-gray palette.
  - Log panel switched to white background for readability.
- Added/reworked documentation for WebView shell in
  `python/pywebview_tailwind_shell/README.md`.

# Developer Changelog

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
- README 測試指令仍提到舊路徑/舊檔名，需後續整理。

## 建議下一步（工程）

1. 讓摘要 `mean_hu` 可選擇「依 range 重算」模式。
2. CSV 加 metadata 區塊（range, erosion, modality, task）。
3. 範圍模式新增「只輸出區間切片」選項，避免 0 值誤讀。

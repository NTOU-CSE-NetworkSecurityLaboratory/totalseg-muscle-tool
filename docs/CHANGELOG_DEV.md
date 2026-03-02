# Developer Changelog

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

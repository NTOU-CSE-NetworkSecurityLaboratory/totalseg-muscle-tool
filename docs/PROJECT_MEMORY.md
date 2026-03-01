# Project Memory: TotalSeg Muscle Tool (AI Handoff Edition)

## 專案定位

TotalSeg Muscle Tool 是一套以 TotalSegmentator 為核心的醫學影像分割與統計工具。
目前重點是「可部署、可追蹤、可向臨床說明」。

## 技術現況快照

- 版本：`v0.0.1`
- 主要語言：Python 3.10
- 介面：PySide6 (`python/gui_pyside.py`)
- 核心計算：`python/seg.py`
- 視覺化：`python/draw.py`
- 環境管理：`uv`

## 主要架構決策與原因

- 放棄 EXE 打包，改用原始碼 ZIP + `START 啟動.bat`
  - 原因：醫院端資安限制與 SmartScreen/防毒誤判風險高
- 維持單一 GUI 入口
  - 原因：降低多腳本維護成本與使用混亂
- 新增 `slice_start/slice_end`
  - 原因：臨床情境常需局部切片區段分析

## CSV/統計口徑（接手必看）

- `volume_cm3`：非內縮體積
- 每層 HU / HU std：內縮後計算（`erosion_iters`）
- 摘要 `mean_hu`：由 `statistics.json` 來，不等同每層內縮 HU 聚合
- `start-end`：會影響幾乎全部統計欄位；範圍外切片目前以 `0` 呈現

## 已完成品質保證（歷史）

- 修復 `draw.py` 語法錯誤
- 修復 auto-draw 參數傳遞 bug（避免空字串/`None`）
- 建立 `python/tests/` 與 `test_auto_draw_cmd.py`
- 通過基本 `pytest` 與 `py_compile` 驗證（當時版本）

## 目前最重要技術債

1. 統計口徑一致性：摘要 `mean_hu` vs 每層 HU
2. CSV 臨床可讀性：範圍外 `0` 的語意不明
3. 開發文檔長期維護：README 與實際測試指令同步

## 文件重整紀錄

- 2026-03-01：`PROJECT_MEMORY.md` 自 repo root 遷移至 `docs/PROJECT_MEMORY.md`
- 目的：將非 README 文檔統一為 AI/工程師快速接手導向

## 相關文檔

- [INDEX.md](./INDEX.md)
- [MODULE_MAP.md](./MODULE_MAP.md)
- [CSV_LOGIC.md](./CSV_LOGIC.md)
- [CHANGELOG_DEV.md](./CHANGELOG_DEV.md)

# Developer Docs Index

這份索引是給 AI/工程師快速接手用，不是給臨床使用者。

## 90 秒接手

1. 先看 [MODULE_MAP.md](./MODULE_MAP.md)：理解主流程與模組責任。
2. 再看 [CSV_LOGIC.md](./CSV_LOGIC.md)：理解 `start-end` 與 CSV 欄位口徑。
3. 再看 [PROJECT_MEMORY.md](./PROJECT_MEMORY.md)：掌握歷史決策與已知限制。
4. 最後看 [CHANGELOG_DEV.md](./CHANGELOG_DEV.md)：確認近期變更與風險。

## Repo 入口

- GUI 入口：`python/gui_pyside.py`
- 分割與 CSV 入口：`python/seg.py`
- 疊圖輸出：`python/draw.py`
- 測試：`python/tests/test_auto_draw_cmd.py`

## 當前高風險區

- CSV 摘要區塊的 `mean_hu` 與前三區塊 HU 口徑不一致。
- `start-end` 會影響幾乎全部統計，且範圍外切片仍列出為 `0`，容易誤讀。

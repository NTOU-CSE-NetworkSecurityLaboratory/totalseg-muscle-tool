# Module Map

## 一句話架構

`gui_pyside.py` 收參數並呼叫 `seg.py`，`seg.py` 產生 segmentation/CSV，再視需求呼叫 `draw.py` 產生 PNG。

## 模組責任

- `python/gui_pyside.py`
  - 統一 GUI（分割 / 批次 / 比對）
  - 組裝 CLI 參數（包含 `--slice_start` / `--slice_end` / `--erosion_iters`）
  - 呼叫 `uv run seg.py ...`
- `python/seg.py`
  - 呼叫 TotalSegmentator
  - 依 mask + CT 計算面積、體積、每層 HU、HU std
  - 輸出 `mask_<task>.csv`
  - 讀 `statistics.json` 後重寫 CSV 摘要區塊
- `python/draw.py`
  - 把 segmentation mask 疊到 DICOM 切片
  - 輸出 `png/` 視覺化
- `python/auto_draw_cmd.py`
  - 組 auto-draw 子流程命令
- `python/tests/test_auto_draw_cmd.py`
  - 驗證 slice 參數有無正確傳遞

## 主資料流

1. GUI 掃描 DICOM 資料夾並建立任務。
2. 使用者設定 task/modality/fast/spine/auto_draw/erosion/range。
3. GUI 以 `uv run seg.py` 執行分割。
4. `seg.py` 輸出：
   - `segmentation_<task>/`（含 `*.nii.gz` + `statistics.json`）
   - `mask_<task>.csv`
   - 可選 `png/`

## 參數影響矩陣（重點）

- `slice_start/slice_end`
  - 影響：面積、每層 HU、每層 HU std、pixelcount、volume_cm3
  - 風險：摘要 `mean_hu` 不是同路徑重算
- `erosion_iters`
  - 影響：每層 HU / HU std
  - 不影響：volume_cm3
- `fast`
  - 影響：分割品質與速度
- `auto_draw`
  - 影響：是否輸出 PNG，不影響 CSV 數值

## UI Direction

- Supported shell: `python/gui_pyside.py`
- WebView is no longer the target architecture; see `docs/REFRACTOR_FIXED_PIPELINE_SPEC.md`

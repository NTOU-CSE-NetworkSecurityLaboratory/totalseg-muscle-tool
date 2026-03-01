# CSV Logic (Engineer View)

## 檔名

- `mask_<task>.csv`

## 4 個區塊

1. 區塊 1：每層面積（左右分開）
   - Header: `slicenumber,<muscle_1>,<muscle_2>,...`
2. 區塊 2：每層平均 HU（左右按面積合併）
   - Header: `slicenumber,<merged_muscle_1>,...`
3. 區塊 3：每層 HU 標準差（左右按面積合併）
   - Header: `slicenumber,<merged_std_muscle_1>,...`
4. 區塊 4：摘要
   - 初始輸出：`structure,pixelcount,volume_cm3`
   - 若 `statistics.json` 存在，重寫為：`structure,pixelcount,volume_cm3,mean_hu`

## 計算口徑

- `volume_cm3`
  - 來源：原始 mask 體素總和（範圍外切片歸零後再計算）
  - 是否內縮：否
- `slice mean HU` / `slice HU std`
  - 來源：每層 mask 經 `erosion_iters` 侵蝕後計算
  - 是否內縮：是
- `summary mean_hu`
  - 來源：`statistics.json` 的 intensity，再按 pixelcount 合併左右
  - 注意：與「每層內縮 HU」口徑不同

## `start-end` 影響

`slice_start/slice_end` 先把範圍外切片設為 0，再做後續統計，因此影響：

- 區塊 1 面積
- 區塊 2 每層 HU
- 區塊 3 每層 HU std
- 區塊 4 pixelcount / volume_cm3

## 已知語意風險

- CSV 仍列全切片，範圍外數值為 `0`，醫師可能誤以為分割失敗。
- 摘要 `mean_hu` 與前三區塊 HU 不是同一計算口徑，需額外註記。

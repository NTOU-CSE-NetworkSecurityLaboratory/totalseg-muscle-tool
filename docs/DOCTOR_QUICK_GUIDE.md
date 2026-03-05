# TotalSeg 工具快速操作（醫師版 1 頁）

## 1. 開啟程式

- 雙擊 `START WebView Tailwind.bat`
- 開啟後先按 `Select DICOM Folder` 選擇病例資料夾

## 2. 分割流程（Segmentation）

1. 確認病例清單已出現
2. 選擇要處理的病例（可 `Select All`）
3. 選擇 `Modality`（CT 或 MRI）
4. 按 `Start` 開始執行
5. 進度會顯示在 `Progress` 與 `Runtime Logs`

## 3. 比對流程（Compare）

1. 切換到 `Compare`
2. 選 `AI Mask` 與 `Manual Mask`
3. 按 `Run Compare`
4. 檢視 Dice 與面積結果

## 4. 常見狀況

- 授權問題：會自動跳出視窗，可直接貼 key，然後按 `Retry Failed`
- 要中止執行：按 `Stop`
- 直接關閉視窗：會連同執行中的任務一起停止

## 5. 結果與紀錄

- 執行紀錄可在畫面中查看
- 詳細紀錄會自動存到病例資料夾下的 `totalseg_batch_logs`

## 6. 安全提醒

- 本工具僅供研究與流程輔助
- 不可直接作為臨床診斷依據


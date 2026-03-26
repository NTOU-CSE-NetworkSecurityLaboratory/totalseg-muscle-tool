# TotalSeg WebView Shell

主要 UI 入口，使用 PyWebView + Tailwind CSS 建構。

## 結構

```
pywebview_tailwind_shell/
├── backend/
│   └── api.py          # Python API（批次管理、狀態、授權、更新）
├── frontend/
│   ├── index.html      # 三 Tab 介面
│   └── app.js          # UI 狀態管理與 API 呼叫
└── main.py             # 啟動入口
```

## 三個 Tab

| Tab | 對應步驟 | 說明 |
|-----|----------|------|
| 自動分割 | 步驟一 | 執行 TotalSegmentator 分割，已有結果自動跳過 |
| 匯出 CSV/PNG | 步驟二 | 產生 volume/HU CSV 與四種 PNG，永遠覆蓋舊結果 |
| 單層面積比對 | — | AI mask vs 手畫 mask 的 DICE 與面積比對 |

## 啟動

```bash
cd python
uv run python pywebview_tailwind_shell/main.py
```

或直接雙擊根目錄的 `START 啟動.bat`。

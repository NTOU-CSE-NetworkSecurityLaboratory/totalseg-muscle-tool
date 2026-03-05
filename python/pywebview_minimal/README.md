# pywebview minimal prototype

## 目的
- 純 Python + WebView 最小架構
- 不連接原本 segmentation 專案

## 結構
- `app.py`: 啟動 pywebview 視窗
- `backend/api.py`: Python bridge API
- `frontend/index.html`: UI
- `frontend/app.js`: 前端事件與 API 呼叫
- `frontend/style.css`: 樣式

## 安裝
```powershell
cd python
uv pip install pywebview
```

如果你不使用 `uv`:
```powershell
pip install pywebview
```

## 執行
```powershell
cd python/pywebview_minimal
python app.py
```

## 可測流程
1. `Ping` 呼叫 Python `ping()`
2. `Echo` 把輸入字串送到 Python `echo(text)`
3. `Run` 呼叫 Python `fake_job(seconds)` 模擬長任務

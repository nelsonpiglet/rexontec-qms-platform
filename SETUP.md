# OQC 出廠檢驗系統 — 首次設定

## 步驟 1：複製金鑰
將 `liko_repair/service_account.json` 複製到此目錄 `oqc_system/`

## 步驟 2：建立 Google Sheet
1. 到 Google Sheets 新建一份試算表
2. 命名為「REXONTEC OQC 出廠檢驗」
3. 複製瀏覽器網址列中的 Sheet ID
   - 網址格式：`https://docs.google.com/spreadsheets/d/【這段就是ID】/edit`

## 步驟 3：填入 Sheet ID
開啟 `utils/gsheet.py`，第 15 行：
```python
SPREADSHEET_ID = "請填入你的Google_Sheet_ID"
```

## 步驟 4：授權服務帳號
1. 開啟 service_account.json，找到 `"client_email"` 的值（例：`xxx@xxx.iam.gserviceaccount.com`）
2. 回到 Google Sheet → 右上角「共用」
3. 貼上上面的 Email，設為「編輯者」

## 步驟 5：啟動系統
雙擊 `啟動OQC系統.bat`，瀏覽器自動開啟 http://localhost:8503

---

## Google Sheet 工作表說明
系統會自動建立兩個工作表：
- `OQC_電調` — 電調出廠檢驗記錄
- `OQC_馬達` — 馬達出廠檢驗記錄

每行一筆記錄，包含：記錄編號、時間、表頭資訊、判定結果、NG摘要、備註、照片、明細JSON

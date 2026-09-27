# 現況盤點

- 此工作區最初只有規格，沒有公司的 Tkinter 原始碼、DB、API 成功樣本或 AD 配置。
- 目前新增獨立 desktop_app 套件；沒有修改或移轉原公司系統。
- OpenAI SDK adapter 是可執行 Chat Completions 相容實作，已用真 SDK + MockTransport 測請求／錯誤；尚未呼叫公司 API。
- 公司正式身分與 Oracle 仍是拒絕未接線的邊界。示範查詢不是公司資料。
- SQLite 是本機單使用者 profile，新檔 local-v1.sqlite3；程式之外未新增共用服務。
- 兩個專案 venv 使用確切 CPython 3.10.4 x64 / Tk 8.6.12。機器安裝例外與重建方式見 ENVIRONMENT.md。
- 當前程式版 0.3.1；完整產品規格 v2.2 的中央更新／issue 後台等仍待未來階段。

- 0.3.1 已更新 Tkinter 視覺、側邊導覽與各頁動作配置；實際畫面及驗證界線見 UI-DESIGN.md。

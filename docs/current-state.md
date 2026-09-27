# 現況盤點

- 此工作區最初只有規格，沒有公司的 Tkinter 原始碼、DB、API 成功樣本或 AD 配置。
- 目前新增獨立 desktop_app 套件；沒有修改或移轉原公司系統。
- OpenAI SDK adapter 是可執行 Chat Completions 相容實作，已用真 SDK + MockTransport 測請求／錯誤；尚未呼叫公司 API。
- 公司正式身分與 Oracle 仍是拒絕未接線的邊界。示範查詢不是公司資料。
- SQLite 是本機單使用者 profile，新檔 local-v1.sqlite3；程式之外未新增共用服務。
- 三個合格專案 venv（.venv、.venv-verify、.venv-offline2） 使用確切 CPython 3.10.4 x64 / Tk 8.6.12。機器安裝例外與重建方式見 ENVIRONMENT.md。
- 當前程式版 QA agent 0.4.1；完整產品規格 v2.2 的中央更新／issue 後台等仍待未來階段。

- 0.3.1 已更新 Tkinter 視覺、側邊導覽與各頁動作配置；實際畫面及驗證界線見 UI-DESIGN.md。

- 0.4.0 加入 catalog 動態欄位、服務層模板驗證與排程日期映射，Plan／結果／歷史同步支援。
- 已提供 test_support、company_templates、scripts/company_check.py；公司實測需可信 hook 與明確啟動，尚未接線仍 not_tested。
- diagnose.bat／doctor 提供無網路白名單報告；setup -OfflineBundle 可從完整驗證的 20-wheel 套件包重建。
- 最終三環境各 103 tests、0 skipped，pip check／freeze lock 一致；原始證據見 docs/validation。第一個離線嘗試 .venv-offline 因 freeze 路徑格式不合格而保留，不當正式基準。
- 工作單與公司驗收：COMPANY-INPUTS、ADAPTER-TEST-KIT、QUERY-CATALOG、OFFLINE-INSTALL、COMPANY-ACCEPTANCE。未新增 runtime 套件，SQLite schema 仍為 1，未讀取或遷移舊公司 DB。

- 0.4.1 品牌更新：生成透明 Q 形夥伴圖示，提供七尺寸 ICO，套用主／附屬視窗、側欄與對話署名；桌面捷徑工具見 SHORTCUT.md。資料與依賴未變。

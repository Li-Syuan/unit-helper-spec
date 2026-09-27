# 現況盤點 — QA agent 0.8.0

- 專案在 D:/unit-helper-spec；獨立 Tkinter 桌面，沒有公司的原始碼、API 成功範例或真實資料；未更動原公司系統。
- 0.8.0 提供最近對話右鍵單筆刪除及「管理對話」搜尋勾選批次清理；預覽名稱與關聯數量後確認，以服務端 10 分鐘 token、完整快照、真實 future 檢查及單交易保護。刪除只涵蓋選定對話相關資料，獨立查詢／排程、檔案、備份、其他轉交副本與公司端歷史保留。
- 0.8.0 顯示處理在建立 Tk 前設定 System DPI awareness，保留既有較高模式；固定尺寸與多尺寸素材配合倍率，文字以點數指定。小工作區可捲動；跨倍率螢幕即時重排不列為完成承諾。本機舊啟動路徑曾讀到 unaware，但不據此宣稱唯一模糊原因。
- 本輪測試及畫面證據以 VALIDATION-LOCAL.md 為準；0.8.0 三環境各 192 tests 通過，本機 150% 實際畫面已檢視。公司 Windows 真實倍率及跨螢幕仍需現場記錄。
- 沿用多助理管理、Windows keyring、對話／Plan 固定助理版本、預覽後轉交資料、Enter 送出、離線手冊／資料說明與正式 A 圖示。0.7.1 將五步隔離體驗改成八頁原地操作提示；開啟直接進入工作區，沒有歡迎彈窗。深淺主題與動態查詢／排程仍沿用。
- 各頁提示可收合並記住選擇，狀態改變時提供下一步或阻擋原因；側欄「操作提示」切換目前頁面。提示本身不填草稿、不執行、不批准或送出。示範助理與合成查詢仍可用，紀錄保存在目前個人歷史。
- 新助理只要求 endpoint、assistant ID、API key；公司請求映射初始 unconfigured。OpenAI SDK 合成契約通過不代表公司 API 已接通；session 規則與副作用能力待公司確認。
- 本機檔名維持 local-v1.sqlite3，schema 已為 2；升級前備份並交易遷移，保存 binding/source。舊對話缺乏歸屬，保留閱讀／明確轉交。未讀取公司舊資料庫。
- 正式身分與 Oracle 未配置時拒絕；三項 demo 為合成資料。排程只查詢通知，不自動送模型；程式關閉不執行。
- 三個獨立環境 .venv、.venv-verify060、.venv-offline060，皆 Python 3.10.4 x64／Tk 8.6.12；0.8.0 各 192 tests、0 skipped，doctor／pip check／freeze lock 一致。後兩者於 0.6.0 全新重建，本輪沿用；實際輸出見 VALIDATION-LOCAL.md 與 docs/validation。
- 鎖檔共 29 個套件，新增 keyring 及相依；wheelhouse-v060 已完整重建並實際離線安裝。套件包／環境不進 Git，舊鎖檔套件包不能用於本版。
- 診斷只檢查本機環境與憑證是否存在，分享白名單不含秘密或內部網址；不呼叫公司服務。
- 真 Tk 程式操作、實際自身視窗截圖、真 Windows 測試憑證及 COM 已驗；真實中文輸入法、OS 人工流程、工作列／桌面外觀、公司 API／AD／Oracle／Excel 仍 not_tested。
- 公司接手入口：COMPANY-HANDOFF.md、GPT6-SOL-HANDOFF.md、docs/ASSISTANT-INTEGRATION.md、docs/COMPANY-INPUTS.md、docs/COMPANY-ACCEPTANCE.md。
- 中央管理、遠端更新、EXE、持續 Goal、自動多 agent 協作均未加入。規格 v2.2 與 B～D 圖示保留歷史，不代表目前功能。

歷史版本與修正紀錄見 VALIDATION-LOCAL.md；目前機器可核對證據在 docs/validation，畫面在 docs/UI-DESIGN.md。

## 0.7.0 工作區改版（沿用）

- 原生 Tkinter／ttk，未新增 runtime 套件。HTML／CSS 只是可離線開啟的視覺稿，入口 docs/design/workspace.html，不嵌入正式應用。
- 工作／管理／協助分組、原創線條 PNG、820px 聊天閱讀寬度、可選取的訊息卡片樣式、3～6 行整合輸入框及真實任務狀態。
- 工作詳情由明確選定的 task／plan ID 取得，顯示來源與助理版本；寬度至少 1380px 使用右欄，較窄以附屬視窗呈現。切換聊天不會改送正在執行的工作，已開啟詳情保留明確選定的來源。
- 開發改用固定檢查／測試腳本。沒有變更防毒設定、例外或執行政策；Norton 是否不再警告尚未確認，見 docs/NORTON-DEVELOPMENT.md。
- 沿用 Python 3.10.4 三個合格環境、29 個鎖定套件與 schema 2；公司 API、AD、Oracle、Excel 及原生中文 IME 仍需現場驗收。

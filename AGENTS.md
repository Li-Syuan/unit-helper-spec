# 本機實作與公司接手守則

## 優先範圍

本次使用者核准的是 **QA agent 0.6.0 本機桌面與公司接手準備包**。先讀 README.md、LOCAL-SPEC.md、VALIDATION-LOCAL.md、COMPANY-HANDOFF.md。較早 SPEC.md、BACKEND.md、OPERATIONS.md、UPDATES.md、IMPLEMENTATION.md／完整 ZIP 保留規格歷史，其中中央功能不是本次交付需求。公司原有規則與程式不可直接覆蓋。

## 已完成，請延續

- Windows x64、Python 恰好 3.10.4、Tkinter、OpenAI SDK 及 SQLite。
- desktop_app/ui.py 畫面、theme.py 統一樣式（0.3.1），core.py 的 Store／服務流程／本機排程，choices.py 表單，files.py 輸出，config.py 設定及單例鎖。
- 本機示範與公司 adapter 明確分離；真實模式失敗不 fallback demo。
- Plan／選項、對話、TXT／CSV、三項合成查詢、通知與本機回報。
- 可重建 .venv、requirements.lock、scripts、測試與驗證紀錄。

## 待公司接線

依 COMPANY-HANDOFF.md：成功 chatbot API 契約、AD／名單／owner 授權、Oracle 三模板、舊資料移轉防雙跑、公司 GUI／Excel 真實驗收。保持 Protocol 和服務邊界，先依 docs/QUERY-CATALOG.md 宣告 catalog 欄位／日期映射；不要重做整套程式。

## 後續才做

共用管理 API、中央 Oracle schema、中央常駐排程、issue 後台、簽章遠端更新與回復、EXE 打包。產品 runtime 多 agent、持續 Goal、信件擷取、OCR、Office 原檔編輯、多文件、任意 SQL/shell 均未授權加入本機版本。

## 開發規則

- 所有正式測試用 `.venv/Scripts/python.exe` 3.10.4；`scripts/test.ps1` 為完整檢查。改依賴後於第二乾淨 venv 重建，不借別人的 site-packages。
- `.venv*`、`.runtime`、本機 config、.env、sqlite 與使用者資料不進 Git。API key 優先保存 Windows keyring；舊設定可相容讀取環境變數；不記錄 HTTP response body 或密碼。
- UI thread 只操作 widget；HTTP／檔案使用背景工作。取消後的晚到結果不能覆寫狀態；真實 future 尚未結束時禁止更換 client；關閉後才釋放 singleton lock。
- Plan 預覽不呼叫 bot；純參數驗證不能跑查詢。批准、修訂、期限、idempotency 在服務層檢查，不能以 prompt／disabled button 代替。
- 選項資料只視為候選答案，不等於工具授權。公司原生 bot 工具的副作用需查證，不能假設 SDK 呼叫是純文字。
- Oracle 使用核准模板、bind、驗證身份注入範圍及唯讀有限結果；不把 DB 共享密碼放桌面／模型。
- 不改寫使用者原文或原檔；精度不用 float；Excel 公式防護與真實貼上需分別驗證。
- SQLite 本機 schema 與舊公司 DB 分離；移轉先備份、dry-run、防重、可回復。舊 runner 未停用前不啟動對應新排程。
- 實測結果分為 mock_passed、local_real_passed、company_real_passed、not_tested。GUI 字串測試不等於人工 GUI／Excel 驗收。

## 分工

使用者允許開發 subagents。Coordinator 可把互斥工作包交 Desktop、Adapters、QA，**最多兩個執行工作包同時進行**；列明可寫檔案、契約、輸入、驗收。根設定、鎖檔、遷移與整合由 Coordinator 管。沒有工具就順序開發，不以角色文字冒充並行。沿用使用者指定開發模型，不猜公司模型 ID。

完成後更新 docs/current-state.md、docs/implementation-status.md、VALIDATION-LOCAL.md（或另建公司實測檔），維持 manifest 一致。既有 spec ZIP 不重包成看似含原始碼的發布；Git history 保留規格。

## 介面維護

0.3.1 以原生 Tkinter/ttk 改善介面，無新 GUI 依賴。調整佈局後檢查 1050×700 與一般尺寸的按鈕可見性，保留 sidebar 導覽／既有 Notebook 服務介面、Plan gate、原文與資料匯出行為；歡迎文案不得當成使用者訊息保存或傳給助理。UI 證據見 docs/UI-DESIGN.md。

## 0.4.0 接手工具

- query_schema 提供共用欄位契約；不要重新把公司欄位寫死在 ui.py。query_catalog／date_range 由服務層驗證，未宣告映射不能使用 previous_day。
- test_support 與 company_templates 為可沿用的 adapter 測試工具；公司 mock fixture 與真實服務驗證分開。company_check 預設 not_tested，不載入 hook；明確執行與能力審查後才跑可信本地 hook。
- company_local 與 artifacts 被忽略；內部樣本、帳號、網址及原始錯誤不得加入分享報告或 Git。公司 hook 回傳 True 前須真的斷言公司結果，不能用 canned True 或 demo 填滿項目。
- 診斷與離線安裝見 docs/OFFLINE-INSTALL.md；offline 安裝缺件／雜湊／lock 不符必須停止，不得改成連外補件。
- 公司資訊清單見 docs/COMPANY-INPUTS.md。舊資料盤點／移轉、正式登入授權、Oracle 接線、EXE 與中央更新仍未實作。

## QA agent 品牌

產品名稱固定為 QA agent（保留大小寫），集中於 desktop_app/branding.py。PNG／ICO 是本機打包資源，不能在執行期下載或呼叫生圖服務。Windows AppUserModelID 在建立 Tk 前設定；主視窗保存 PhotoImage 引用，附屬視窗套用相同品牌。不得為更名而改資料路徑、SQLite、環境變數或舊規格。捷徑只更新本工具所建立的項目，不能覆蓋其他程式。

## 0.5.0 深淺主題與候選圖示（歷史；0.6.0 已採用 A）

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

## 0.6.0 接手重點

已完成：A 正式圖示、使用者自管多助理、keyring、固定對話／Plan 路由、資料預覽轉交、Enter／Shift+Enter、獨立五步體驗、離線手冊及聲明。共用 endpoint／API key；名稱、assistant ID、備註由使用者管理。

修改入口：profiles.py 負責公司請求映射及憑證；assistant_views.py 為管理／轉交 UI；core.py schema 2 保存 binding/source，experience.py 管隔離導覽。公司請先提供遮蔽值的成功 API 範例，確認 ID 放 model 或獨立 body 欄位、session 規則及副作用能力。未配置 mapping 的新公司助理不能呼叫，不假裝用示範回答。具體步驟與命令見 docs/ASSISTANT-INTEGRATION.md。

環境新增 keyring==25.7.0，總鎖定套件 29 個；不得使用 keyrings.alt 或明文 fallback。完整離線包以新鎖檔重建，舊包指紋不符必須拒絕。正式驗證用 .venv、.venv-verify060、.venv-offline060，均恰好 Python 3.10.4。

完成條件：公司 API 對話隔離與回傳結果實測、AD／Oracle 核准接線、Excel／Windows 中文輸入法與縮放人工驗收。未實測項目仍保持 not_tested，不能以合成測試替代。中央協作、遠端更新、EXE、任意 SQL 及助理自動分工不在本版。

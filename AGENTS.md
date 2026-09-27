# 本機實作與公司接手守則

## 優先範圍

本次使用者核准的是 **0.3.0 本機桌面**。先讀 README.md、LOCAL-SPEC.md、VALIDATION-LOCAL.md、COMPANY-HANDOFF.md。較早 SPEC.md、BACKEND.md、OPERATIONS.md、UPDATES.md、IMPLEMENTATION.md／完整 ZIP 保留規格歷史，其中中央功能不是本次交付需求。公司原有規則與程式不可直接覆蓋。

## 已完成，請延續

- Windows x64、Python 恰好 3.10.4、Tkinter、OpenAI SDK 及 SQLite。
- desktop_app/ui.py 畫面、theme.py 統一樣式（0.3.1），core.py 的 Store／服務流程／本機排程，choices.py 表單，files.py 輸出，config.py 設定及單例鎖。
- 本機示範與公司 adapter 明確分離；真實模式失敗不 fallback demo。
- Plan／選項、對話、TXT／CSV、三項合成查詢、通知與本機回報。
- 可重建 .venv、requirements.lock、scripts、測試與驗證紀錄。

## 待公司接線

依 COMPANY-HANDOFF.md：成功 chatbot API 契約、AD／名單／owner 授權、Oracle 三模板、舊資料移轉防雙跑、公司 GUI／Excel 真實驗收。保持 Protocol 和服務邊界，必要時只擴充 query UI 的真實參數表單；不要重做整套程式。

## 後續才做

共用管理 API、中央 Oracle schema、中央常駐排程、issue 後台、簽章遠端更新與回復、EXE 打包。產品 runtime 多 agent、持續 Goal、信件擷取、OCR、Office 原檔編輯、多文件、任意 SQL/shell 均未授權加入本機版本。

## 開發規則

- 所有正式測試用 `.venv/Scripts/python.exe` 3.10.4；`scripts/test.ps1` 為完整檢查。改依賴後於第二乾淨 venv 重建，不借別人的 site-packages。
- `.venv*`、`.runtime`、本機 config、.env、sqlite 與使用者資料不進 Git。金鑰從環境變數讀取；不記錄 HTTP response body 或密碼。
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

# 單位桌面小幫手 v2.2：公司端開發守則

本檔與 GUIDED-QUERIES.md、PLAN-AND-CHOICES.md、SPEC.md、BACKEND.md、OPERATIONS.md、UPDATES.md、IMPLEMENTATION.md 是本版規範。若與舊 Multi-Agent v1 規格不同，以使用者核准的精簡版為準。公司原有規則與原始碼不可被本包直接覆蓋。

## 必須保留

- Windows／Python／Tkinter，不換 GUI 框架。
- 舊版公司智能助理 API、聊天、排程、網路蒐集與 SQLite 資料。
- 公司已存在的後端框架與 AD 登入，不重做身份平台。
- OpenAI 套件連公司端點；GPT 6 sol 是開發模型，不能硬接公共模型 API。

## 第一版只做

一般／Plan 模式＋是非／單選／多選確認＋一個通用助理＋三項核准 Oracle 查詢＋文字/TXT/CSV 整理＋文字改寫＋中央查詢排程/通知＋issue＋使用者點擊更新。不要加入產品 runtime 多 agent、Skill 市集、OCR、信件、Office 原檔編輯、任意 SQL/shell 或跨人 agent 通訊。

## 開始與分工

先讀 START-HERE.md 與 IMPLEMENTATION.md。盤點公司程式後建立 docs/current-state.md、docs/implementation-status.md；缺原碼時明確記錄，不虛構已完成整合。

使用者允許公司 Copilot 以 subagents 分工實作。Coordinator 可將互斥工作包交 Desktop、Backend、QA，最多兩個執行工作包同時進行；契約、根設定、鎖檔、migration 由 Coordinator 統一整合。每個包列需求 ID、可寫路徑、依賴、輸入與驗收；有依賴必須先完成契約。

無 subagent 工具就順序開發，明確說明，不以角色文字假裝並行。沿用使用者選擇的 GPT 6 sol，不猜模型選單 ID 或自行换模型。開發分工不等於產品需多代理。

## 技術與安全界線

- UI thread 只更新 Tk widget；背景執行 HTTP／檔案工作。
- Oracle credentials 僅 server 持有；查詢参数用 bind，scope 由經驗證身份注入。模型回覆不能直接當 SQL 執行。
- AD 帳密不得進應用資料表、prompt、log 或排程；沿用平台授權，查詢每次重驗。
- 首版單一 TXT/CSV 有大小/編碼限制；超限不假裝已完整處理。文字改寫保留原文。
- 排程獨立於 desktop，unique occurrence＋lease 防重；舊 runner 切換須有 watermark 與停用證據。
- Issue 預設私有；附加對話／資料須使用者選取；管理 issue 不等於可讀所有對話。
- 更新必須驗發布簽章與 hash，保留 last_good，程式與資料分離；不能只下載 EXE 覆蓋正在執行的程式。
- 公司 schema、API、AD 授權、套件版本、更新來源未知就做 adapter/Mock；禁止猜成功。

## 品質與自主性

沿用 repo 的測試／格式／build 指令。沒有時先建立最小可執行檢查與鎖版依賴；按 AT-01～AT-27 測試行為，不堆鏡像實作的無價值測試。修錯誤不降低規格或跳過失敗。

每階段報完成內容、真實執行檢查、未通過／阻擋及下一步，區分 mock_passed/real_passed。GUI、Oracle、AD、更新須各有實測，不因檔案存在就宣稱 production ready。

一般實作、Mock、測試、修正與可逆重構自主完成。發布、正式資料庫修改與不可逆動作依公司既有規範；沒有相依證據時只阻擋該部分，繼續其他授權工作。保留使用者修改，不以重寫刪掉初版功能。

## Plan／選項實作守則

- 先讀 PLAN-AND-CHOICES.md，實作 UH-11、UH-12。一般模式保留快查，Plan 在後端完成確認前禁止業務工具 dispatch；prompt 與 disabled button 不能代替 gate。
- 達哥沒有原生 Plan／JSON 也能用固定表單；若 bot 原生工具副作用不能關閉或驗證，Plan 不呼叫它。
- schema 僅表示候選；owner、批准、期限、修訂、form ID 和選項 typed value 由 server 掌管。選項答案不等於任意動作授權。
- 修改使原批准失效；版本／hash／idempotency 防止舊卡片和雙擊重複執行。「是，設成排程」只建 disabled 草稿，仍需原有啟用確認。
- 首版只用固定短流程；不要藉此建立持續自主 Goal、多 agent 或通用任務引擎。依 AT-16～AT-21 提供實測證據。

## 引導查詢與 Excel 複製

讀 GUIDED-QUERIES.md，完成 UH-13／UH-14／AT-22～AT-27。常用工作共用原工具，不新增引擎。一般模式一次送出，Plan 不跳過批准。複製只讀同一快照，不能另跑 SQL；欄序／精度／公式防護／跨頁與真 Excel 貼上需驗證。快速回報只開既有草稿。不得增加收藏、Excel 自動操控、固定範本產檔或評分表。

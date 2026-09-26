# 貼給公司 Copilot 的實作指令

在公司 VS Code 選擇可用的 GPT 6 sol，可選 custom agent 時選 `UnitHelper-Coordinator`。將下段貼進對話。先把本包合併到公司 repo，保留既有公司規則。

```text
請依這份 v2.2 精簡規格實作「單位桌面小幫手」。先讀 AGENTS.md、SPEC.md、GUIDED-QUERIES.md、PLAN-AND-CHOICES.md、BACKEND.md、OPERATIONS.md、UPDATES.md、IMPLEMENTATION.md 及 database/ORACLE.md。

這次產品是一個公司通用助理配少量可靠工具，不是舊版大型 Multi-Agent 平台。第一版包括：一般／Plan 切換、計畫預覽及確認、是非／單選／多選補條件、指定單位／人員登入、個人對話、三項核准 Oracle 查詢、TXT/CSV 整理、文字改寫、中央排程通知、問題回報與 issue 管理、點擊軟體更新。

必須保留 Tkinter，以及初版已能用的公司助理 API、排程、網路蒐集和 SQLite。沿用公司已有的後端與 AD 登入。openai 套件接公司端點，不是直接接公共 OpenAI；GPT 6 sol 僅作開發模型。不要新增產品 runtime 多 agent、Skill 市集、OCR、信件、Office 原檔編輯或任意 SQL/shell。

先 M0 盤點原碼、成功 API 呼叫、SQLite schema、scheduler、登入流程、Oracle 版本與三項查詢，建立 docs/current-state.md 和 docs/implementation-status.md。未取得公司資訊的項目標清楚，先完成能獨立做的 Mock、介面、schema、UI 與測試。

按 M1～M4 逐步交付可操作流程。你擔任 Coordinator；若工具可用，可將互斥工作交 UnitHelper-Desktop、UnitHelper-Backend、UnitHelper-QA，最多兩個工作包並行，契約與整合由你負責；不可用就順序開發，不假裝啟動子代理。

SQL 只用核准模板與 bind；使用者範圍由後端身份注入。排程固定重跑模板，重啟與舊版切換不得雙跑。Issue 只附上使用者選取資料。首次分發包含 Launcher/Updater，後續按鈕更新需驗簽、驗 hash、保留上一可用版，不清掉使用者資料。

Plan 確認前後端禁止業務工具派發；無原生規劃／結構輸出時用固定表單。驗證當前修訂／hash／owner，重送不重複執行，選「設排程」只建 disabled 草稿。持續自主 Goal 不在範圍。

使用 AT-01～AT-27 驗收；每階段回報實際測試、mock/real 結果及阻擋。不要只建立畫面、生成檔案或跑 Mock 就宣稱公司功能完成。一般實作與修正自主完成，正式發布與資料異動按公司流程處理。
```

v2.2 補強：讓同仁不寫提示詞也能從常用工作入口填條件查詢，再複製結果貼到既有 Excel。依 GUIDED-QUERIES.md 共用目錄／表單／snapshot，結果旁快速回報只開草稿。先完成真實資料與公司 Excel 驗收，不自行擴成 Office 自動化。

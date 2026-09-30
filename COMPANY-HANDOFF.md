## 本次新增的離線登入展示

執行 `start-demo-login.bat`，admin/admin 僅用於暫存離線fixture，禁止公司連線設定；不能作公司帳號或授權。原公司登入早已存在但未接AD，identity_mode=company拒絕回退。人事資料用途為App使用資格，核准名單／部門待定，尚未配置。詳見 [登入與資格邊界](docs/LOGIN-AND-APP-ACCESS.md)。

# 本次待辦與一鍵接手

使用本次可攜包的69正式wheels，不使用開發機舊wheelhouse或lab lock；解壓新目錄，保留公司既有修改。核准Python3.10.4 x64安裝：`install-offline.bat "C:\approved\Python3104\python.exe"`；再執行 **`test-company.bat`**，一次完整本機與WebView驗證。不必另重跑full。公司Assistant API／搜尋仍需独立核准與人工來源驗收，本次沒有live或啟用使用者排程。

待辦頁可回原流程確認、檢查主對話失敗及查看部分成果；手動完成不改AI狀態。詳見 [操作](docs/ONE-CLICK-TEST.md)、[DVC核對](docs/DVC-REVIEW.md)及[最新驗證](docs/VALIDATION.md)。下方歷史日報接手流程不是本次自動執行授權。

# 0.20.0 組織試用修正

本次對照 [Assistant API 手冊](https://dvcaiplatform.atlassian.net/wiki/spaces/DW/pages/2719802/Assistant+API)，提供安全未送出重試、分階段錯誤、每助理可選獨立金鑰及普通聊天搜尋核准。請先從 UI 完成一位助理無工具試聊，再測第二個 ID，最後核准搜尋；不要一次啟用所有角色與排程。

可交给接手 agent：沿用目前 adapter，先核對 docs/VALIDATION.md；執行環境診斷後，由使用者在 UI 保存 endpoint／key／assistant ID。不要讀出或記錄金鑰，不重寫協定。依 docs/DEVELOPMENT.md「達哥十輪連線測試」逐助理明確執行 --live；失敗收集安全分類與階段，不自動 retry 未知寫入。metadata 與聊天／搜尋各自驗收；核准普通聊天搜尋後再獨立執行 --search，人工核對來源。舊對話遇到修訂失效，先保留歷史，再另開新對話。不可手改 verified 解鎖多助理。

本輪完成一般聊天失敗恢復、本機刪除與白名單錯誤紀錄。先用完整正式離線包建立新環境，保留組織成功程式与設定，再手動測每個助理；不要先派 agent 重寫整套功能。

1. 安裝／完整驗證：依下方離線步驟。69個wheels和根lock一致，失敗不連外補件；Python、WebView2、.NET由組織另提供。
2. 設定頁保存Endpoint與API key，再新增Assistant ID。普通聊天不需先驗收四角色。對每個ID分別測三輪合成追問，記錄是哪一輪、按哪個入口失敗。
3. 中斷時按「檢查原請求」，有可恢复結果才按「取回原回覆」。不明寫入或已取消不可重送；可「另開對話保留內容」，歷史是否帶入由人決定，不自動送出。
4. 「說明與關於 → 匯出除錯包」提供白名單ZIP；請附版本、操作步驟與畫面問題編號。不附key、內部網址、完整對話或資料庫。原始事件在使用者資料目錄logs。
5. 「活動紀錄 → 管理／批次刪除」或「說明 → 管理本機資料」清理本機成果；主對話歷史和任務草稿有各自刪除入口。執行中不可刪，自動工作需先暫停。

普通聊天／metadata成功不代表搜尋或四角色已驗收。主畫面「整理任務草稿」不會自動執行；「規劃與分工」仍需完成組織角色試跑後啟用能力。本版未取得正式服務實測，不能宣稱所有助理只填ID便能使用進階功能。組織需要回報時先看安全錯誤代碼及階段，對照成功範例修adapter，不猜故障原因。

# 0.20.0 組織接手入口

**先處理部署缺件（2026-09-30）：**使用核准管道帶入正式 69 套件離線 ZIP，解壓到新資料夾。CMD 執行 `install-offline.bat "C:\approved\Python3104\python.exe"`，成功後執行 `.venv\Scripts\python.exe scripts\verify.py offline-rebuild` 一次。環境通過才設定／實測AI 助理；不需要 agent 重寫 adapter 或降版 lock。保留組織現有程式與 `.venv`，差異另行比對。詳細失敗處理見[離線安裝](docs/DEVELOPMENT.md#離線安裝)，本機結果見[驗證紀錄](docs/VALIDATION.md)。

明天先跑「現有搜尋助理 → 財經日報 → 現在試跑 → 核對來源 → 每日08:00」，不需先完成四角色。多代理改以固定合成資料測分析／覆核／彙整；[接手指令](docs/COMPANY-IMPLEMENTATION.md) 提供完整貼上內容與驗收。App 已加本機設定盤點及明確 metadata 檢查；組織已有成功呼叫請先保留，不再重寫整個介面。

先照 [GPT 6 sol 工作指令](docs/COMPANY-IMPLEMENTATION.md) 完成組織文字旅程。組織 Threads/Messages/Runs 接口已依範例實作，LangGraph 已正式接管批准後的順序分工；不用再從零設計 agent 引擎或猜 Assistant ID 映射。

本版已接通有限 pluginapi 搜尋往返。先讀取助理 metadata，核對 function 名稱／參數及唯讀用途，再在 UI 明確核准；不用重寫通用協定。搜尋開放於已確認日報及 rag 步驟；普通聊天需額外勾選核准，其餘角色不派發工具。核准會更新版本並撤銷角色 verified，所以應先完成搜尋核准，再做角色驗收。組織部署、CA、服務端副作用、真實多 ID 與格式仍須實測。AD／Oracle／舊資料仍另列待辦。


# WebView 與組織既有修改

**組織已能呼叫助理、接著要完成產品流程時：**把 [GPT 6 sol 實作指令](docs/COMPANY-IMPLEMENTATION.md) 交給組織 agent。此為使用者回報的組織進度，不代表本外部儲存庫已取得或驗證組織 adapter；以組織 checkout 為準並保留現有修改。

組織若先評估 LangChain／LangGraph，使用 [獨立離線試驗包](experiments/langgraph-lab/README.md)。已包含 wheels 與組織 agent 指令；先驗安裝及無金鑰範例，再討論服務接線。不得覆蓋 App 的根目錄鎖檔，框架可用不代表助理 API 契約已完成。

先確認 WebView2 Runtime 與 .NET Framework 已核准，重建requirements.lock環境。新版WebView為主入口，Tkinter為備用；兩者沿用Python服务與個人資料，但新增兩模式對話使用獨立dialogue-v1資料庫。

新主畫面預設離線示範，可明確選取已設定的AI 助理；任務僅確認保存、固定不啟用。ProfileDialogueProvider 已實作，維持 dialogue_contracts.py 嚴格驗證；組織現場需驗證 endpoint、認證、assistant ID、服務相容差異、session 隔離及工具副作用；不得讓回覆直接儲存、執行或讀本機檔案，不得把Demo當失敗fallback。

新草稿尚不接執行器，不能只把enabled改1；組織若要自動執行，應另外確認核准來源與工具映射、權限、批准範圍、排程防重及取消測試。原進階Workflow／Oracle／AD工作單繼續適用。測試：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_dialogue,tests.test_web`，組織正式連線保持not_tested。

以下是既有進階功能接手項目。

# QA agent 組織接手工作單

目前版本 **0.20.0**，本機桌面、核准搜尋連接器與接手工具可沿用。助理 API、AD、Oracle 與現場 Excel／IME 驗收仍為 **not_tested**。已取得 Threads/Runs＋pluginapi 官方契約，但沒有組織測試憑證及真實搜尋結果，不能保證任意端點只填三個參數就全部接通。

交付給一般同仁的目標：服務接線者先配置共用 endpoint、請求／session 映射與核准助理能力；同仁只需設定個人 API key、加入已核准 assistant ID，說需求並按一次「確認執行」。不要要求同仁編輯程式、填驗證證據或理解 adapter。新增未核准 ID 仍顯示待驗證，不能偽裝可自動協作。

UI 已備妥的入口：助理團隊卡片直接沿用新增／編輯／停用與分工設定；分工清單顯示真實狀態並開完整成果；規劃模式隱藏無關的聊天助理選單。組織完成接線後，請用全新使用者實際走一遍「填金鑰與 ID → 需求討論 → 一次確認 → 成果 → 排程」，確認無需修改 UI，記錄 company_real_passed 前不得以本機模擬代替。

通知呈現已集中至 `desktop_app/notifications.py`：右下角非模態彈窗與側欄青藍色未讀徽章，直接讀取既有 Store 通知；服務接線不必重做通知 UI，也不得以彈窗取代通知持久保存或新增自動派發。

先讀 [開發守則](AGENTS.md)、[產品與架構](docs/PROJECT.md)、[驗證紀錄](docs/VALIDATION.md)。已完成多助理、keyring、對話與刪除、Plan／選項、TXT／CSV、三項合成查詢、表格／匯出、本機排程／通知、回報草稿、深淺主題、DPI 與原地提示。沿用現有畫面及 Protocol；GPT 6 sol 是開發 agent，不是產品模型 ID。

組織可在 `desktop_app/work_cards.py` 調整三張工作卡片的文字，提供每張的合成輸入與人工預期輸出。卡片只填草稿，待辦只記錄使用者工作；不用 API 也可驗收。`local_work.py`／`todo_views.py`／`draft_views.py` 沿用即可，請勿另造任務平台。

## 組織先提供的資訊

新增的 start-trial.bat 是個人 Groq 外部 AI 試用，供使用者先體驗真正摘要／改寫。回組織仍使用 start-app.bat 與組織 adapters；不要把試用 .env 或資料帶回組織，也不能以 Groq 實測代替助理 API 驗收。修改入口 trial.py，獨立測試 `.\scripts\test.ps1 -Suite targeted -Tests tests.test_trial`；組織不需重新設計 UI。

在組織內部副本填「內部文件位置／負責窗口」，未知填待確認。**不填密碼、token、內部網址實值、個人資料或真實對話**；去識別樣本及測試 hooks 放被忽略的 `company_local`，原始證據放組織核准位置。

| 項目 | 所需資訊 | 內部位置／窗口 |
|---|---|---|
| 環境 | 核准 Python 3.10.4 x64 含 Tcl/Tk、pip 鏡像／離線政策、代理與可信 CA | 待確認 |
| Chatbot 契約 | 成功 SDK 範例、method、header 名稱、request／response 型別與位置；endpoint 是 base URL 或 action URL，assistant ID 傳送位置 | 待確認 |
| Session／能力 | session/thread 建立、續用、逾期與銷毀；跨使用者／助理／對話隔離；原生查詢、寄信、寫入工具及核准測試助理 | 待確認 |
| AD／名單 | 既有登入服務、LDAPS 規範、員工主鍵、單位／allowlist、停用／逾期／離線策略、共用裝置政策 | 待確認 |
| Oracle | 既有核准查詢服務或直連治理、scope 身份來源、row cap、timeout、唯讀帳號治理 | 待確認 |
| 舊資料／排程 | DB schema 與使用者映射、時區、runner、最後執行時間、外部副作用與停舊窗口 | 待確認 |
| 現場／部署 | Windows、縮放、字型、Excel／IME、資料保留政策、打包／簽章／防毒流程 | 待確認 |

### 三項核准查詢

| 核對欄位 | Q01 | Q02 | Q03 |
|---|---|---|---|
| 名稱／用途／核准 SQL 或服務版本 | 待確認 | 待確認 | 待確認 |
| 參數名稱、型別、必填、預設、範圍 | 待確認 | 待確認 | 待確認 |
| 日期時區、起迄包含規則、前一日映射 | 待確認 | 待確認 | 待確認 |
| 輸出欄位、型別、精度、NULL、截斷限制 | 待確認 | 待確認 | 待確認 |
| 授權 scope 的可信來源 | 待確認 | 待確認 | 待確認 |
| 人工條件／基準結果內部位置 | 待確認 | 待確認 | 待確認 |
| 正常、空結果、界線、越權、逾時案例 | 待確認 | 待確認 | 待確認 |
| 比對人、日期、結論、證據位置 | 待確認 | 待確認 | 待確認 |

人工比對使用相同資料時間、參數與授權範圍，逐欄比對精確值、筆數及截斷資訊；正式資料不放 repo。

## Groq 日報試用與組織界線

已完成 `intent_drafts.py` 的受限結構化建議、`action_views.py` 的同頁確認及 `report_engine.py` 的日報執行。Groq 只在 start-trial.bat 獨立資料區啟用；組織 adapter 契約不變。schema 4 的 conversation_actions／schedule_sources 保存來源，不混入模型歷史，也不改變排程工作歸屬。組織 agent 可參考流程，但不得將 Oracle 結果自動送至 Groq。

本機測試：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_report_engine,tests.test_report_views`。個人明確允許外部合成測試時，執行 `.venv/Scripts/python.exe scripts/check-trial.py --live --reports`，最多三筆 Groq 請求，暫存資料庫結束後清除；一般 doctor 不呼叫模型。此項不是組織驗收。

若組織後續要開放日報整理，需另核准助理資料去向、持續傳送授權、模型結構化能力、查詢範圍與每次派發身分檢查，再接組織 adapter；不僅更換 endpoint。組織持續 Goal、Windows 背景排程及自動寄信仍未實作。

組織對話操作接線新增要求：保留 catalog 動態欄位，先以同頁表單完成核准查詢；目前組織解析能力預設關閉。若組織要開放自然語言解析，須提供可信模板目錄、成功結構化回傳與副作用審查結果，新增解析 adapter 後驗證缺條件、未知欄位、錯誤型別、惡意內容及零未批准派發，不能只把 capability 改成 True。測試入口為 `tests.test_conversation_actions` 與 `tests.test_action_ui`，組織 DB 結果仍依下列工作單人工比對。

## 多助理協作接手工作

已完成：對話式主代理需求討論、選項追問、最多六步計畫、批准後依序交子代理、結果與明確重試、成功流程排程。UI 與 WorkflowService 可直接沿用；Groq 四角色真實測試不等於組織四個 assistant ID 驗收。

| 所需內部資訊 | 修改入口／工作 | 完成條件 |
|---|---|---|
| 規劃、分析、覆核、彙整、RAG 各助理 ID、用途、實際能力 | 我的助理先登錄；profiles.py 的角色與能力 metadata | 列出可接收資料、輸出及服務端工具，未知／生圖不加入自動流程 |
| 成功 API 與 session 契約 | Profiles.workflow_call(messages, role, binding, context)，沿用 respond／CompanyAssistant | ID 路由正確；run_id、step_id、助理版本隔離；沒有隱含寫入或寄信 |
| 規劃／覆核結構化回覆樣本 | adapter 回傳文字 JSON；workflows.py 做應用端驗證 | 追問、最多六步、未知工具拒絕、未批准零業務派發；不支援時明確失敗 |
| RAG 文字及真實引用格式 | 組織 adapter 保留實際來源於回覆文字 | 無來源明示，不能由 UI 推測或新增引用；生圖保持不支援 |
| 能力測試證據識別（不是秘密） | 實測通過後由可信組織 hook 呼叫 set_workflow_capability(profile_id, roles, verified=True, evidence=本機證據識別) | verified 只記錄真實驗收結果，不以填旗標代替測試；改 ID／endpoint 後重新驗證 |
| 查詢模板及數據比對 | 沿用下方 Oracle 工作單 | 相同條件的精確合計與人工一致；首版只轉交 metadata／合計，原始表格本機保存 |

本機命令：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_workflows,tests.test_workflow_profiles,tests.test_workflow_ui`。另以核准的內部合成資料驗證兩個以上真實 ID 及不同 run/step 的 session 隔離，保存 company_real_passed 證據後才開放日常排程。組織版不讀 Groq .env。

接手順序：先跑基準 → 接通一般 API → 驗證唯讀規劃與子代理能力／隔離 → 登錄並啟用角色 → 用內部合成文字試跑 → 接核准數據 → 人工對照成果 → 啟用流程排程。不必重寫畫面或引擎；但不能只換 ID、跳過能力及 API 契約驗證。

## 六項接線工作

### 1. 建立組織環境基準

- **入口／已備妥**：`scripts/setup.ps1`、`requirements.lock`、doctor、離線工具與完整測試；操作見 [開發指南](docs/DEVELOPMENT.md)。組織提供上表核准環境。
- **命令**：`./scripts/setup.ps1 -PythonExe 'C:\核准路徑\python.exe'`，接著 `./scripts/test.ps1 -Suite full`。以 `-Environment .venv-verify` 建第二乾淨環境並用其 Python 執行完整測試；離線安裝依開發指南。
- **完成條件**：確切 3.10.4／64 位元／Tk、pip check、lock 一致與完整回歸通過；記錄實際路徑、版本、命令及 exit code。不得借別的 site-packages，改鎖檔後重建及驗證，不僅修改現有 venv。

### 2. 接組織 chatbot

- **入口／已備妥**：使用者管理共用 endpoint／API key 與多助理名稱／ID／備註；`profiles.py` 固定 binding／revision 與映射，`gateways.py` 的 CompanyAssistant 保留 SDK 實作及 `respond` 介面。依 [多助理接線](docs/ASSISTANT-INTEGRATION.md) 對照成功範例，未知映射維持停用。
- **實作界線**：assistant ID 不猜成 model；自訂 headers、session、request／response 差異留在 adapter，不改成公共 OpenAI URL。session 按使用者、助理版本及對話隔離。keyring 不可用就報錯；設定只存索引，舊環境變數保持相容，不用明文 fallback。CA 使用可信 PEM，不停用 TLS 驗證。
- **能力確認**：Plan 預覽固定本機表單、零 API 呼叫。核准測試助理的副作用能力後才設定連線測試 gate／啟動真實測試；prompt 或 `verified_side_effect_free` 標記不能代替服務端工具治理與實際授權。
- **命令**：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_gateways,tests.test_profiles,tests.test_assistant_ui`；沿用 `test_support/assistant_contract.py` 補合成 wire 測試，再按下方組織 runner 明確實測。
- **完成條件**：真實回覆、401／403、timeout、空回覆、格式錯誤、不同助理／對話隔離、修訂／停用拒絕及轉交資料範圍皆符合人工結果；不自動重送、不 demo fallback，金鑰與 HTTP body 不進 log。

### 3. 接 AD、指定員工與資料 owner

- **入口／已備妥**：`CompanyIdentity.current()` 與測試骨架。組織提供登入／名單規則；優先沿用既有登入服務，補身分 adapter、Engine 每次派發與排程授權。
- **現有缺口**：`local-demo` 僅本機展示；Store 是單本機 profile，尚無多租戶 ACL。共用裝置須依登入者分目錄或補 owner 驗證及相應資料遷移，包含讀取、匯出、轉交與刪除；改名字／隱藏 UI 都不算授權。
- **命令**：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_local,tests.test_gateways`；補派發 gate／owner 隔離測試，以組織核准帳號完成 hooks 的允許、拒絕、停用、逾期四案。
- **完成條件**：錯密碼、錯單位、不在名單、停用與逾期均拒絕，不能讀取其他人資料；排程持有人失效時停止並提示，離線策略經組織確認。AD 密碼不保存、不送模型；授權失敗不能 fallback demo，也不能把連線 timeout 當成預期授權拒絕。

### 4. 接 Oracle 三項核准查詢

- **入口／已備妥**：`OracleQueries.catalog/validate/run`、動態表單、Plan 與排程預覽；依 [查詢 catalog](docs/QUERY-CATALOG.md) 填組織欄位與日期映射，不重寫 UI。未宣告日期映射只允許固定參數排程。
- **實作界線**：優先接組織既有可信查詢服務。若要求桌面直連，先確認組織核准的憑證／權限治理，不打包共享 DB 密碼，不自行建立整套中央平台。模型只能選模板與參數，不能產生任意 SQL；使用 bind、可信 scope、有限唯讀結果。`validate` 必須無 DB／HTTP I/O，`run` 前重驗身份；不要將所有 driver 錯誤都視為可重試。
- **結果契約**：欄列一致、UTC 資料時間、條件、來源、筆數及截斷明確；NUMBER／Decimal 用精確字串，不經 float。
- **命令**：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_gateways,tests.test_files,tests.test_core`；沿用 `test_support/query_contract.py`，攔截真正 I/O 驗證純 validate，補組織合成樣本及 query.q01～q03 真實 hooks。
- **完成條件**：上表三模板填齊，正常／空資料／界線／越權／超時／截斷與人工結果逐欄相符；不以 DEMO 資料當組織證據。

### 5. 舊 SQLite 與排程遷移

- **入口／狀態**：`core.Store` schema 與 occurrence 邊界可沿用；**遷移工具尚未實作**。組織先提供舊 DB／runner／watermark 資訊，不直接讀寫舊版正式 DB。
- **工作內容**：一致性備份及 checksum、唯讀盤點、dry-run 映射，stable legacy ID 防重，保留原檔。SQLite 使用 backup API 或關閉 writer 後處理 WAL，不能只複製正在寫入的主檔。先停舊 runner、確認無執行中工作及最後完成點，才啟用新排程；回復先停新 runner。
- **命令／完成條件**：新增 `scripts/migrate_legacy.py` 與 `tests/test_migration.py` 後，執行 `.\scripts\test.ps1 -Suite targeted -Tests tests.test_migration`，再於備份副本跑 migration `--dry-run`。驗證空 DB、部分失敗、重跑、回復、筆數與條件一致及無雙跑；此命令是待實作入口，不能宣稱現在可用。正式切換依組織流程。

### 6. 現場 GUI／Excel 驗收後才打包

- **入口／已備妥**：原生 Tkinter UI、[離線手冊](docs/USER-GUIDE.md)、[資料說明](docs/DATA-USAGE.md)、顯示診斷及完整回歸；打包腳本尚未提供。
- **命令**：`./scripts/test.ps1 -Suite full` → `./scripts/run.ps1`；按下表逐項操作，記錄版本／環境及證據。GUI、真實 Excel、IME、縮放不得以字串或模擬測試取代。
- **完成條件**：服務接線與現場驗收通過後，才依組織流程打包／簽章；保留 Tcl/Tk、CA／設定外置、資料目錄獨立。若需 packaging 依賴，用獨立 build lock，勿污染 runtime lock。不改防毒或增加排除；Norton 警示另記操作與警示 ID。

## 組織開發期間的選測規則

首次建立組織環境須 full 驗收一次；之後修改不重複從頭跑全部。`./scripts/test.ps1` 預設 quick，僅非 GUI 核心離線檢查；`./scripts/test.ps1 -Suite targeted -Tests tests.test_appearance` 指定模組、class 或案例，多個名稱在 PowerShell 用逗號分隔。文字／配色跑受影響測試與畫面，一般功能加 quick，核心服務／遷移／依賴／發布才跑 full。WebView smoke 只在相關 UI／bridge 變更或介面發布驗收時執行。

交付證據使用 `.venv/Scripts/python.exe scripts/verify.py development`，它執行同一 full 一次，不先跑 test full 再跑 verify。日常報告覆寫 `artifacts/testing/latest.json`，只宣稱實際選測範圍通過。新增模組／TestCase class 須加入 `tests/suites.json` 分類；保留關鍵保障，不以測試數持續增加當績效，也不為每次文案或版本另堆案例。完整做法見 [開發指南](docs/DEVELOPMENT.md#測試與交付)。

## 真實測試與現場驗收表

離線合成契約與組織真實服務分開；細節見 [串接測試工具包](docs/ADAPTER-TEST-KIT.md)。將 `company_templates` 的範本複製至 `company_local`，組織審查可信本地 hooks 的真實斷言與 timeout。不得載入下載／模型生成而未審查的程式，也不能只回傳 True、skip 或註冊 demo 補綠。

~~~powershell
# 預設不載入 hook、不連線，exit 2 表示 not_tested
.venv/Scripts/python.exe scripts/company_check.py
# 確認核准測試環境、助理能力與 hooks 後才執行
.venv/Scripts/python.exe scripts/company_check.py --hooks company_local/company_hooks.py --execute --capabilities-reviewed --output artifacts/company-check.json
~~~

旗標只記錄操作者已審查，不會關閉遠端工具。runner 通過僅代表已登記項目通過，不是全產品上線許可。每次記錄 commit、應用／Python／Windows／Excel／IME 版本、縮放、測試者、核准範圍、實際命令／exit code、預期與實際、內部證據位置及缺項；結果分為 `mock_passed`、`local_real_passed`、`company_real_passed`、`not_tested`。以下初始狀態全部 **not_tested**。

| 驗收項目 | 組織操作與通過條件 |
|---|---|
| 環境／離線 | 組織獨立及乾淨環境完整通過；需要離線時斷網可安裝，缺件／雜湊／lock 不符停止 |
| Chatbot／憑證 | 真實回覆與 session 隔離；核准測試 key 保存／讀取／更換／移除；認證管理員失敗不明文 fallback，repo／SQLite／日誌／診斷無秘密 |
| AD／owner | 允許／拒絕／停用／逾期及跨登入者隔離；派發、排程、讀取／匯出／轉交／刪除皆驗權 |
| Oracle／Plan | 三項人工比對及動態欄位；修改／批准／取消與過期修訂；未批准零派發，改 ID／endpoint 後舊 Plan 拒絕 |
| 轉交／多助理 | 目的助理、欄位、筆數、精度、條件與時間均正確；確認前不送，失敗不改原結果，切換不暗送草稿／附件 |
| 本機排程 | 固定／已宣告前一日參數、停用／立即執行／歷史、重啟防重；失效模板停止並通知；只在程式開啟時運作 |
| 文字／Excel | TXT／CSV 預覽、原文保留、另存及重開；全部／選取／含或不含標題，前導零、18 位編號、高精度、負數、中文、NULL、逗號／引號／公式型文字逐字核對；剪貼簿占用明示失敗 |
| IME／鍵盤 | 微軟注音及組織慣用 IME：組字 Enter 不送，完成後 Enter 只送一次，Shift+Enter 換行、Ctrl+Enter 送出，長按／連按／空白不重複派發 |
| 待辦／草稿 | 選文加入、期限、開始／完成／重開、來源失效及刪除；重開恢復文字、不自動載入附件、不送到其他助理；背景晚到不復活已清草稿 |
| 提示／手冊／回報 | 圖示侧欄、助理團隊、分工進度及更多工具原地提示與章節入口、收合偏好重開保留，不填稿／派發；回報編號與草稿保留，明示只存本機且不自動附私人資料 |
| 對話刪除 | 右鍵、標題搜尋、批次及篩選全選；取消為預設且不變資料；刪目前／最後一筆後可繼續，其他草稿保留，舊詳情／預覽關閉，重開不再出現 |
| 刪除保護 | 未批准 Plan 刪除不執行；執行中／取消後 future 未結束整批拒絕；10 分鐘或快照過期重預覽；原檔、匯出、備份、獨立查詢／排程、回報、轉交副本及組織歷史保留，失效來源明示 |
| 顯示 | 記正式啟動 DPI 模式／Tk scaling／字型／工作區；深淺一般、小工作區、最大化操作可達；可取得的 100／125／150／200% 真實倍率各驗，未取得標未測；最大化不改點數，跨螢幕另記限制 |
| 診斷／Norton | 分享報告無內部網址、帳號、金鑰、對話及原始錯誤；環境通過不冒充組織接通；防毒警示成效獨立記錄，不改設定 |

本機刪除不是服務端清除或安全抹除；System DPI awareness 保留既有較高模式，不承諾跨倍率螢幕即時重排。舊資料切換、正式排程與發布仍依組織流程，不因驗收表填完就擅自操作。

## 可直接貼給 GPT 6 sol

~~~text
請接手 QA agent 0.14.0 的服務接線。先讀 AGENTS.md、README.md、COMPANY-HANDOFF.md、docs/PROJECT.md 和 docs/VALIDATION.md。沿用 Windows x64、Python 恰好 3.10.4、Tkinter、SQLite、OpenAI SDK 與現有測試；不要重做 GUI、恢復獨立體驗、另建中央平台或無界限自主代理。一般使用者只負責金鑰／助理 ID、需求與一次確認；你負責預先接好助理 API、session 與助理能力規則。

先盤點組織已有程式、成功 API 範例及環境，依 COMPANY-HANDOFF 的資訊表確認缺項；找得到就沿用，缺少時一次問最少必要問題並繼續獨立可做工作。不要猜 URL、assistant ID 傳送位置、session、AD／SQL 欄位或秘密；秘密不貼對話、不進 repo／log。

依工作單六項順序完成環境基準、chatbot、AD／owner、Oracle、舊資料／排程遷移與現場驗收。每項先列可寫位置及完成條件，再實作與驗證。保留 Plan／刪除服務 gate、future 防重、綁定版本、精度、純 validate 與明確資料轉交；正式模式失敗不能 demo fallback。舊 DB 不直接改，遷移先備份與 dry-run，停舊後才啟新。

按本文件的選測規則驗證：日常 quick／targeted，核心變更或交付 full；交付只跑 verify 一次，不先完整測試再重跑。新增測試保護具體行為，不要求數量增加或每次全跑。

使用 test_support、company_templates 與 docs 的三份契約指南，不重造測試或查詢 UI。組織 hooks 預設 not_tested，審查助理能力及真實斷言後才明確執行；mock、skip、True 常值不能算組織通過。GUI／Excel／IME／縮放保留獨立實測證據。

可依 AGENTS.md 委派互斥工作包，含自己的執行工作最多兩包並行；無工具就順序完成。每次完成更新 docs/PROJECT.md、docs/VALIDATION.md、組織內部驗收表及 manifest，列出實際結果與缺項，不捏造完成，不覆蓋組織規則或擅自正式發布。
~~~

## 0.14.0 AI 助理 Instruction 試跑

從 [建立指南](docs/assistant-instructions/README.md) 取得 planner／analysis／review／compose 四份完整指示。使用組織核准的 Luna 選項建立四個助理；名稱、桌面 profile ID、組織 assistant ID 與模型識別分開，不猜 API 映射。能力/session 驗證通過後才能啟用。

新成果 UI 與本機比較／回饋不需助理 API 變更。請用正常、空資料、缺條件、故意矛盾與資料內夾指令案例核對 JSON 和自由文字；Instruction 不能代替服務端權限與數值驗證，同模型覆核不代表獨立正確性保證。組織 Luna／多 ID 結果仍為 not_tested。

## AD 登入與作者資訊

已提供原生登入頁（WebView與Tk共用啟動前入口），組織驗證函數尚未提供，正式登入 **not_tested**。目前本機模式沿用既有入口，不冒充AD；組織部署請在設定檔將 `identity_mode` 改為 `company`。此時未成功登入不能開工作區，沒有退回本機的按鈕。先看畫面可執行：

```bat
.venv\Scripts\python.exe -m desktop_app --login-preview
```

它不呼叫AD或啟動資料服務。修改 `desktop_app/company_auth.py` 的 `authenticate(employee_id, password)` 並在接線完成後使 `is_configured()` 回傳True。組織函數若僅回True/False，請在此處補查可信員工資料及單位/名單授權，再映射為下列字典，不能由使用者輸入或模型提供身分：

```python
{
    "authenticated": True,  # AD帳密有效
    "allowed": True,        # 單位/名單也已核准且未停用
    "subject": "穩定且唯一的組織員工識別",
    "employee_id": "驗證後的工號",
    "name": "可信員工資料中的姓名",
    "expires_at": "含時區的ISO日期時間，由連線設定，不超過8小時"
}
```

失敗回傳明確拒絕或拋例外；介面不顯示原始例外。函數必須限制連線/讀取timeout、使用核准TLS/CA且不記密碼。密碼只在該次驗證留於記憶體，不存keyring/JSON/SQLite/log；Python記憶體不宣稱安全抹除。尚未加入LDAP套件，待確認你函數依賴後才更新正式lock和離線包。

通過後資料存 `使用者資料目錄/users/<subject的SHA256>/`。不同登入身分不共用對話/排程/助理設定，舊本機資料不自動搬移。組織首次登入須重新設定該身分的API key與Assistant ID。登入期限到達後禁止新助理/查詢/排程派發，請關閉再登入；已送出的遠端呼叫不保證停止。本機分資料夾不等同Windows檔案ACL；共用Windows帳號、即時撤權、Oracle伺服器授權仍須組織驗收。

驗證命令：

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_authentication tests.test_about
```

組織再測有效/錯誤帳密、非名單、停用、到期、服務斷線、兩位員工隔離與排程期限；本機合成通過不可代替組織通過。

作者資訊：複製根目錄 `publisher.example.json` 為 `publisher.json`，填 `author.employee_id`、`author.name`、`author.phone`。主畫面右上角「作者」popover、Tk 側欄作者小卡、登入頁與「說明與關於」共用；未填顯示尚未設定。此檔不進 Git，也不自動放進離線交付包；由維護者確認顯示內容後隨內部分發放置。公開儲存庫及 Release 只保留空白範例，不要提交真實工號、姓名或電話。

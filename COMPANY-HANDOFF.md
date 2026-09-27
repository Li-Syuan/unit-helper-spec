# QA agent 公司接手工作單

目前版本 **0.9.0**，已完成本機桌面與接手工具；本版加入本機待辦、常用工作與草稿恢復。公司 API、AD、Oracle 與現場 Excel／IME 驗收仍為 **not_tested**。目前沒有公司原始碼、成功 API 樣本或資料庫規格，不能保證只填三個參數就全部接通。

先讀 [開發守則](AGENTS.md)、[產品與架構](docs/PROJECT.md)、[驗證紀錄](docs/VALIDATION.md)。已完成多助理、keyring、對話與刪除、Plan／選項、TXT／CSV、三項合成查詢、表格／匯出、本機排程／通知、回報草稿、深淺主題、DPI 與原地提示。沿用現有畫面及 Protocol；GPT 6 sol 是開發 agent，不是產品模型 ID。

公司可在 `desktop_app/work_cards.py` 調整三張工作卡片的文字，提供每張的合成輸入與人工預期輸出。卡片只填草稿，待辦只記錄使用者工作；不用 API 也可驗收。`local_work.py`／`todo_views.py`／`draft_views.py` 沿用即可，請勿另造任務平台。

## 公司先提供的資訊

在公司內部副本填「內部文件位置／負責窗口」，未知填待確認。**不填密碼、token、內部網址實值、個人資料或真實對話**；去識別樣本及測試 hooks 放被忽略的 `company_local`，原始證據放公司核准位置。

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

## 六項接線工作

### 1. 建立公司環境基準

- **入口／已備妥**：`scripts/setup.ps1`、`requirements.lock`、doctor、離線工具與完整測試；操作見 [開發指南](docs/DEVELOPMENT.md)。公司提供上表核准環境。
- **命令**：`./scripts/setup.ps1 -PythonExe 'C:\核准路徑\python.exe'`，接著 `./scripts/test.ps1`。以 `-Environment .venv-verify` 建第二乾淨環境並用其 Python 執行完整測試；離線安裝依開發指南。
- **完成條件**：確切 3.10.4／64 位元／Tk、pip check、lock 一致與完整回歸通過；記錄實際路徑、版本、命令及 exit code。不得借別的 site-packages，改鎖檔後重建及驗證，不僅修改現有 venv。

### 2. 接公司 chatbot

- **入口／已備妥**：使用者管理共用 endpoint／API key 與多助理名稱／ID／備註；`profiles.py` 固定 binding／revision 與映射，`gateways.py` 的 CompanyAssistant 保留 SDK 實作及 `respond` 介面。依 [多助理接線](docs/ASSISTANT-INTEGRATION.md) 對照成功範例，未知映射維持停用。
- **實作界線**：assistant ID 不猜成 model；自訂 headers、session、request／response 差異留在 adapter，不改成公共 OpenAI URL。session 按使用者、助理版本及對話隔離。keyring 不可用就報錯；設定只存索引，舊環境變數保持相容，不用明文 fallback。CA 使用可信 PEM，不停用 TLS 驗證。
- **能力確認**：Plan 預覽固定本機表單、零 API 呼叫。核准測試助理的副作用能力後才設定連線測試 gate／啟動真實測試；prompt 或 `verified_side_effect_free` 標記不能代替服務端工具治理與實際授權。
- **命令**：`.venv/Scripts/python.exe -m unittest tests.test_gateways tests.test_profiles tests.test_assistant_ui -v`；沿用 `test_support/assistant_contract.py` 補合成 wire 測試，再按下方公司 runner 明確實測。
- **完成條件**：真實回覆、401／403、timeout、空回覆、格式錯誤、不同助理／對話隔離、修訂／停用拒絕及轉交資料範圍皆符合人工結果；不自動重送、不 demo fallback，金鑰與 HTTP body 不進 log。

### 3. 接 AD、指定員工與資料 owner

- **入口／已備妥**：`CompanyIdentity.current()` 與測試骨架。公司提供登入／名單規則；優先沿用既有登入服務，補身分 adapter、Engine 每次派發與排程授權。
- **現有缺口**：`local-demo` 僅本機展示；Store 是單本機 profile，尚無多租戶 ACL。共用裝置須依登入者分目錄或補 owner 驗證及相應資料遷移，包含讀取、匯出、轉交與刪除；改名字／隱藏 UI 都不算授權。
- **命令**：`.venv/Scripts/python.exe -m unittest tests.test_local tests.test_gateways -v`；補派發 gate／owner 隔離測試，以公司核准帳號完成 hooks 的允許、拒絕、停用、逾期四案。
- **完成條件**：錯密碼、錯單位、不在名單、停用與逾期均拒絕，不能讀取其他人資料；排程持有人失效時停止並提示，離線策略經公司確認。AD 密碼不保存、不送模型；授權失敗不能 fallback demo，也不能把連線 timeout 當成預期授權拒絕。

### 4. 接 Oracle 三項核准查詢

- **入口／已備妥**：`OracleQueries.catalog/validate/run`、動態表單、Plan 與排程預覽；依 [查詢 catalog](docs/QUERY-CATALOG.md) 填公司欄位與日期映射，不重寫 UI。未宣告日期映射只允許固定參數排程。
- **實作界線**：優先接公司既有可信查詢服務。若要求桌面直連，先確認公司核准的憑證／權限治理，不打包共享 DB 密碼，不自行建立整套中央平台。模型只能選模板與參數，不能產生任意 SQL；使用 bind、可信 scope、有限唯讀結果。`validate` 必須無 DB／HTTP I/O，`run` 前重驗身份；不要將所有 driver 錯誤都視為可重試。
- **結果契約**：欄列一致、UTC 資料時間、條件、來源、筆數及截斷明確；NUMBER／Decimal 用精確字串，不經 float。
- **命令**：`.venv/Scripts/python.exe -m unittest tests.test_gateways tests.test_files tests.test_core -v`；沿用 `test_support/query_contract.py`，攔截真正 I/O 驗證純 validate，補公司合成樣本及 query.q01～q03 真實 hooks。
- **完成條件**：上表三模板填齊，正常／空資料／界線／越權／超時／截斷與人工結果逐欄相符；不以 DEMO 資料當公司證據。

### 5. 舊 SQLite 與排程遷移

- **入口／狀態**：`core.Store` schema 與 occurrence 邊界可沿用；**遷移工具尚未實作**。公司先提供舊 DB／runner／watermark 資訊，不直接讀寫舊版正式 DB。
- **工作內容**：一致性備份及 checksum、唯讀盤點、dry-run 映射，stable legacy ID 防重，保留原檔。SQLite 使用 backup API 或關閉 writer 後處理 WAL，不能只複製正在寫入的主檔。先停舊 runner、確認無執行中工作及最後完成點，才啟用新排程；回復先停新 runner。
- **命令／完成條件**：新增 `scripts/migrate_legacy.py` 與 `tests/test_migration.py` 後，執行 `.venv/Scripts/python.exe -m unittest tests.test_migration -v`，再於備份副本跑 migration `--dry-run`。驗證空 DB、部分失敗、重跑、回復、筆數與條件一致及無雙跑；此命令是待實作入口，不能宣稱現在可用。正式切換依公司流程。

### 6. 現場 GUI／Excel 驗收後才打包

- **入口／已備妥**：原生 Tkinter UI、[離線手冊](docs/USER-GUIDE.md)、[資料說明](docs/DATA-USAGE.md)、顯示診斷及完整回歸；打包腳本尚未提供。
- **命令**：`./scripts/test.ps1` → `./scripts/run.ps1`；按下表逐項操作，記錄版本／環境及證據。GUI、真實 Excel、IME、縮放不得以字串或模擬測試取代。
- **完成條件**：公司接線與現場驗收通過後，才依公司流程打包／簽章；保留 Tcl/Tk、CA／設定外置、資料目錄獨立。若需 packaging 依賴，用獨立 build lock，勿污染 runtime lock。不改防毒或增加排除；Norton 警示另記操作與警示 ID。

## 真實測試與現場驗收表

離線合成契約與公司真實服務分開；細節見 [串接測試工具包](docs/ADAPTER-TEST-KIT.md)。將 `company_templates` 的範本複製至 `company_local`，公司審查可信本地 hooks 的真實斷言與 timeout。不得載入下載／模型生成而未審查的程式，也不能只回傳 True、skip 或註冊 demo 補綠。

~~~powershell
# 預設不載入 hook、不連線，exit 2 表示 not_tested
.venv/Scripts/python.exe scripts/company_check.py
# 確認核准測試環境、助理能力與 hooks 後才執行
.venv/Scripts/python.exe scripts/company_check.py --hooks company_local/company_hooks.py --execute --capabilities-reviewed --output artifacts/company-check.json
~~~

旗標只記錄操作者已審查，不會關閉遠端工具。runner 通過僅代表已登記項目通過，不是全產品上線許可。每次記錄 commit、應用／Python／Windows／Excel／IME 版本、縮放、測試者、核准範圍、實際命令／exit code、預期與實際、內部證據位置及缺項；結果分為 `mock_passed`、`local_real_passed`、`company_real_passed`、`not_tested`。以下初始狀態全部 **not_tested**。

| 驗收項目 | 公司操作與通過條件 |
|---|---|
| 環境／離線 | 公司獨立及乾淨環境完整通過；需要離線時斷網可安裝，缺件／雜湊／lock 不符停止 |
| Chatbot／憑證 | 真實回覆與 session 隔離；核准測試 key 保存／讀取／更換／移除；認證管理員失敗不明文 fallback，repo／SQLite／日誌／診斷無秘密 |
| AD／owner | 允許／拒絕／停用／逾期及跨登入者隔離；派發、排程、讀取／匯出／轉交／刪除皆驗權 |
| Oracle／Plan | 三項人工比對及動態欄位；修改／批准／取消與過期修訂；未批准零派發，改 ID／endpoint 後舊 Plan 拒絕 |
| 轉交／多助理 | 目的助理、欄位、筆數、精度、條件與時間均正確；確認前不送，失敗不改原結果，切換不暗送草稿／附件 |
| 本機排程 | 固定／已宣告前一日參數、停用／立即執行／歷史、重啟防重；失效模板停止並通知；只在程式開啟時運作 |
| 文字／Excel | TXT／CSV 預覽、原文保留、另存及重開；全部／選取／含或不含標題，前導零、18 位編號、高精度、負數、中文、NULL、逗號／引號／公式型文字逐字核對；剪貼簿占用明示失敗 |
| IME／鍵盤 | 微軟注音及公司慣用 IME：組字 Enter 不送，完成後 Enter 只送一次，Shift+Enter 換行、Ctrl+Enter 送出，長按／連按／空白不重複派發 |
| 待辦／草稿 | 選文加入、期限、開始／完成／重開、來源失效及刪除；重開恢復文字、不自動載入附件、不送到其他助理；背景晚到不復活已清草稿 |
| 提示／手冊／回報 | 九頁原地提示及章節入口、收合偏好重開保留，不填稿／派發；回報編號與草稿保留，明示只存本機且不自動附私人資料 |
| 對話刪除 | 右鍵、標題搜尋、批次及篩選全選；取消為預設且不變資料；刪目前／最後一筆後可繼續，其他草稿保留，舊詳情／預覽關閉，重開不再出現 |
| 刪除保護 | 未批准 Plan 刪除不執行；執行中／取消後 future 未結束整批拒絕；10 分鐘或快照過期重預覽；原檔、匯出、備份、獨立查詢／排程、回報、轉交副本及公司歷史保留，失效來源明示 |
| 顯示 | 記正式啟動 DPI 模式／Tk scaling／字型／工作區；深淺一般、小工作區、最大化操作可達；可取得的 100／125／150／200% 真實倍率各驗，未取得標未測；最大化不改點數，跨螢幕另記限制 |
| 診斷／Norton | 分享報告無內部網址、帳號、金鑰、對話及原始錯誤；環境通過不冒充公司接通；防毒警示成效獨立記錄，不改設定 |

本機刪除不是公司端清除或安全抹除；System DPI awareness 保留既有較高模式，不承諾跨倍率螢幕即時重排。舊資料切換、正式排程與發布仍依公司流程，不因驗收表填完就擅自操作。

## 可直接貼給 GPT 6 sol

~~~text
請接手 QA agent 0.9.0 的公司接線。先讀 AGENTS.md、README.md、COMPANY-HANDOFF.md、docs/PROJECT.md 和 docs/VALIDATION.md。沿用 Windows x64、Python 恰好 3.10.4、Tkinter、SQLite、OpenAI SDK 與現有測試；不要重做 GUI、恢復獨立體驗、另建中央平台或產品多代理。

先盤點公司已有程式、成功 API 範例及環境，依 COMPANY-HANDOFF 的資訊表確認缺項；找得到就沿用，缺少時一次問最少必要問題並繼續獨立可做工作。不要猜 URL、assistant ID 傳送位置、session、AD／SQL 欄位或秘密；秘密不貼對話、不進 repo／log。

依工作單六項順序完成環境基準、chatbot、AD／owner、Oracle、舊資料／排程遷移與現場驗收。每項先列可寫位置及完成條件，再實作與驗證。保留 Plan／刪除服務 gate、future 防重、綁定版本、精度、純 validate 與明確資料轉交；公司模式失敗不能 demo fallback。舊 DB 不直接改，遷移先備份與 dry-run，停舊後才啟新。

使用 test_support、company_templates 與 docs 的三份契約指南，不重造測試或查詢 UI。公司 hooks 預設 not_tested，審查助理能力及真實斷言後才明確執行；mock、skip、True 常值不能算公司通過。GUI／Excel／IME／縮放保留獨立實測證據。

可依 AGENTS.md 委派互斥工作包，含自己的執行工作最多兩包並行；無工具就順序完成。每次完成更新 docs/PROJECT.md、docs/VALIDATION.md、公司內部驗收表及 manifest，列出實際結果與缺項，不捏造完成，不覆蓋公司規則或擅自正式發布。
~~~

# 公司接手工作包 — GPT 6 sol

**先保留本機可用功能，再逐一接公司服務。** 目前交付目標為 0.8.0，包含對話刪除、DPI 顯示調整、原地操作提示與公司接手準備包；實際驗證結果見 VALIDATION-LOCAL.md。 本次沒有公司原始碼、成功 API 樣本、AD 配置、Oracle schema 或真實 Excel。不能把下列事項描述成只填密碼就保證完成。

## 0.8.0 接手時保留的契約

- 本機刪除需先預覽後確認，10 分鐘 token 固定選定資料快照；Engine 鎖與單一交易執行整批刪除，不以按鈕停用替代。取消後真實請求尚未結束也會阻擋所屬對話刪除。未批准 Plan 可刪除但不得派發。
- 原始檔、匯出、備份、獨立查詢／排程、回報、其他對話的轉交副本及公司端歷史保留；公司平台保留／刪除政策須另外確認，不可把本機刪除宣稱為遠端清除或安全抹除。
- 正式啟動在 Tk 前設定 System DPI awareness；已有較高感知模式則保留。display.py 與既有主題處理固定尺寸及圖示倍率，文字以點數指定；公司打包／啟動器若另設 DPI manifest，須記錄實際模式並重驗，不能再重複縮放。
- 公司需提供 Windows 顯示倍率與常用螢幕配置，在 100%、125%、150%、200% 可用的真實倍率下檢查一般、最大化及小工作區；不能用尺寸模擬當成人工倍率驗收。跨螢幕即時 DPI 重排未列為本版保證。
- 修改入口為 core.py 刪除服務、桌面刪除入口、display.py 及 theme.py；回歸使用 scripts/test.ps1，精確證據見 VALIDATION-LOCAL.md。公司 AD 接線後仍需將刪除操作納入實際使用者授權驗收，不把本機身分冒充 AD。

## 0. 已完成與不可重做

已完成：Python 3.10.4 獨立環境／鎖版、Tkinter、SQLite、固定 Plan gate、選項、三項合成查詢、文字／檔案、OpenAI SDK adapter、本機排程、通知、回報草稿。詳細證據見 VALIDATION-LOCAL.md。

程式入口 `python -m desktop_app`；介面見 `desktop_app/gateways.py` 的 Protocol；業務流程 `core.py`；UI `ui.py`。不能換框架、把真實模式失敗變成 demo、把測試跳過當通過、把舊 SQLite 刪除或覆蓋。GPT 6 sol 是開發 agent，不是這個產品必須呼叫的模型識別。

### 0.7.1 操作提示接手要求

獨立五步體驗、歡迎彈窗與「快速體驗」入口已移除。開啟直接進入工作區，八頁頁首提供可收合提示與手冊入口；示範助理與合成查詢照常可用，紀錄保存在目前個人歷史。不要重新加入另一套體驗資料庫或流程。

- 已準備：頁面提示呈現、各頁展開偏好、離線手冊；目前執行證據以 VALIDATION-LOCAL.md 為準。
- 公司需提供：實際服務的可用條件與核准錯誤說明，供接線後校對提示；不把內部網址、金鑰或業務內容寫進提示。
- 修改入口：`desktop_app/guidance.py`、`ui.py`、`preferences.py`；完整步驟單一來源為 `docs/USER-GUIDE.md`，離線手冊入口在 `experience.py`。公司服務契約仍在原 adapter 邊界。
- 驗證命令：`./scripts/test.ps1`；另以公司設定手動核對八頁提示與章節入口。
- 完成條件：提示符合目前選定內容，不自動送出／批准；收合不遮蔽必要警告，切換後草稿與選取仍在。`page_hints` 偏好可重開保留，舊 `onboarding` 不再觸發畫面且保持原值。

## 已準備好的公司接手工具

- 動態參數規格：[QUERY-CATALOG](docs/QUERY-CATALOG.md)；提供欄位與日期映射即可沿用 UI／Plan／排程。
- 離線與真實測試分離：[ADAPTER-TEST-KIT](docs/ADAPTER-TEST-KIT.md)；有合成樣本、共用斷言及公司測試骨架。
- 離線環境：[OFFLINE-INSTALL](docs/OFFLINE-INSTALL.md)；套件包完整性驗證，不自動連外補件。
- 雙擊 diagnose.bat 或執行 scripts/doctor.py 檢查環境；診斷不呼叫公司服務，也不表示 AD／Oracle 已接通。
- 公司先填 [COMPANY-INPUTS](docs/COMPANY-INPUTS.md)，只填規格與資訊負責窗口；不填秘密。內部 hooks／fixture／報告放 company_local 或 artifacts，不推入 Git。

## 1. 重建公司 Python 3.10.4 基準

- 修改位置：`scripts/setup.ps1`、`requirements.lock`、`ENVIRONMENT.md`；預設不必改程式。
- 需內部資訊：公司核准的 Python 3.10.4 x64 完整安裝路徑、Tcl/Tk、pip 鏡像、代理與可信 CA。
- 命令：`./scripts/setup.ps1 -PythonExe 'C:\實際路徑\python.exe'`，接著 `./scripts/test.ps1`。
- 完成條件：doctor 確切版本／64 位元／Tk 成功，pip check 成功，所有本機測試通過。另建 `.venv-verify` 重跑，留存公司自己的 stdout、exit code 與版本紀錄。不得借用其他專案 site-packages。
- 若改鎖檔：先記錄原因；在兩個乾淨環境重建及驗證，不僅在舊 venv pip install。

## 2. 接公司 chatbot

- 修改位置：先讀 docs/ASSISTANT-INTEGRATION.md；使用者在設定管理助理。profiles.py 固定助理版本與 API 映射，CompanyAssistant 處理 SDK，保留 respond 介面。config.example.json 是進階相容設定。
- 需內部資訊：一份公司目前成功呼叫的去識別範例（URL、HTTP method、headers 名稱、SDK 用法、request/response shape）、模型／部署名稱、助理 ID、認證環境變數、session/thread 生命週期、TLS CA、timeout／流量限制、原生工具是否有副作用。
- 預設支援 `client.chat.completions.create(model=..., messages=..., stream=False)`；**不假設平台和 OpenAI 完全相容**。自訂 session、request wrapper、response parser 都在這一個串接邊界處理。不要改成公共 OpenAI URL。
- `header_env` 格式為 `{"X-Example-Tenant":"COMPANY_TENANT_ENV"}`；值是環境變數名稱。`assistant_ref` + `assistant_ref_field` 須依公司文件指定；不傳任意 extra_body。
- UI 經 Windows keyring 保存金鑰；assistants.json 只存索引。舊 `api_key_env` 保留相容讀取，明確保存 keyring 後切換來源；repo 與 SQLite 不保存金鑰。`ca_bundle` 指定可信 PEM；禁止 verify=False。依 IT 的密鑰配送方式設定，不把秘密貼到 agent 對話。
- `verified_side_effect_free` 預留為公司能力紀錄，目前不能繞過 gate。Plan 預覽固定本機表單，完全不呼叫 API；不要只憑 system prompt 說「不要執行工具」就認為沒有副作用。測試連線會真的呼叫 bot，必須先確認測試助理能力。
- 完成條件：真實回覆、401／403、timeout、空回覆、格式錯誤均合理；兩個對話相互隔離；有原生工具的服務需公司側關閉、使用文字專用助理或明確授權路徑；失敗不回 demo；金鑰／HTTP body 不進 log。
- 基準命令：`.\.venv\Scripts\python.exe -m unittest tests.test_gateways tests.test_core -v`。沿用 `test_support/assistant_contract.py` 與 `company_templates/test_company_offline.py.example`，補公司 wire 差異。真實驗證依 docs/ADAPTER-TEST-KIT.md 建立 company_local/company_hooks.py，執行 scripts/company_check.py 的明確啟動流程；不得以 mock／缺項代替 company_real_passed。

## 3. 接 AD 與指定員工名單

- 修改位置：`CompanyIdentity.current()`；新增公司登入狀態／授權 adapter，將身分檢查注入 `Engine` 的每個派發入口與排程執行入口。UI 登入畫面只是輸入層。
- 需內部資訊：既有全端登入方式（優先沿用）、AD 網域／LDAP TLS、員工欄位、單位範圍、allowlist 來源、停用規則、session 有效期限、服務帳號治理、離線策略。
- 目前 `local-demo` 是固定本機展示身分，**不能直接把它改名就當 AD**。目前 Store 是單本機 profile，尚無多租戶 ACL；正式共用裝置需依登入者分目錄或補 owner 驗證及資料遷移。UI 隱藏功能不等於授權。
- AD 密碼不得持久化或送給模型；每次查詢與排程重新檢查啟用／名單。授權失敗停止操作，不 fallback demo；現有排程持有人失效須停用並提示。
- 完成條件：允許者可用、錯密碼／錯單位／不在名單／已停用者拒絕；不能讀取其他人的對話／結果；session 過期及離線拒絕策略經公司核准。
- 命令：保留 `.\.venv\Scripts\python.exe -m unittest tests.test_local tests.test_gateways -v`；沿用 company_templates/company_hooks.py.example 的四個 identity 案例，接線時另補派發 gate、owner 隔離測試，使用公司核准測試帳號執行。紀錄真實授權正反案例，不保存帳密。

## 4. 接 Oracle 三項核准查詢

- 修改位置：`OracleQueries.catalog/validate/run`，保持結果契約；公司 agent 可拆出 `oracle_adapter.py`。UI 已依 catalog 自動產生參數、Plan／結果／排程預覽；依 docs/QUERY-CATALOG.md 宣告欄位與可選 date_range，不必重寫畫面。未宣告日期映射的模板只提供固定參數排程。
- 需內部資訊：Q01～03 SQL 核准版本、欄位／型別／精度、主表關聯、bind 參數、日期時區、資料範圍、授權身份欄、row cap、timeout、可重試錯誤分類、人工基準結果。
- 原架構要求 DB 密碼在可信服務端。優先接公司**既有**核准查詢服務；此 repo 沒有另造共用 API。如公司要求桌面直連，先取得其帳號／密碼治理與資料權限方案核准，不把共享 DB 密碼打包至桌面。不要因這個工作包擅自建立整套中央平台。
- 模型只能選核准模板與參數，不能執行模型生成 SQL。使用 bind 與 server-derived scope；有限讀取、明確截斷；Decimal／NUMBER 轉精確字串，不經 float。結果 `columns` 的順序與 `rows`（list of lists）一致，需含 query_ref、parameters、source_label、fetched_at_utc、row_count、truncated。
- `validate` 必須是純驗證，不執行 DB 查詢；查詢前再次授權。`run` 只能唯讀；不要把一般 Oracle driver 例外都標成可重試錯誤。
- 完成條件：三項各有正常／空資料／界線／越權／超時案例，與同條件人工 SQL 結果逐欄校對；不把 DEMO 資料標成公司資料。
- 命令：`.\.venv\Scripts\python.exe -m unittest tests.test_gateways tests.test_files tests.test_core -v`；沿用 test_support/query_contract.py，以合成 fixture 補公司離線測試；在 company_local/company_hooks.py 的 query.q01～q03 以公司唯讀環境執行並保存人工比對結果。正式測試需公司環境，不能在本機合成結果上蓋 real_passed。

## 5. 舊 SQLite 與排程遷移

- 修改位置：新建 `scripts/migrate_legacy.py`（目前沒有）；`core.Store` schema version 與排程 occurrence 邊界。
- 需內部資訊：原 DB 檔案路徑／schema／使用者映射、時區、排程 runner 位置、最後執行時間、外部副作用、同一任務可能已在哪台機器跑。
- 預設新資料庫獨立，**不讀取、不修改舊版 DB**。先離線備份、校驗 checksum、read-only inventory，產出 dry-run 映射及報告。SQLite 備份使用 backup API 或關閉 writer 後連同 WAL 一致性處理，不能只複製正在寫入的 .sqlite 主檔。
- 以 stable legacy ID 設唯一映射，重跑不重複匯入；保留原檔。明確停用舊 runner、記錄 watermark、確認無執行中作業，才啟用新排程；回復時先停新 runner。
- 完成條件：空 DB／部分匯入失敗／重跑／回復均驗證；筆數與對話／排程條件一致，無雙跑證據。排程取消不代表遠端工作已撤回。
- 命令（新增 migration 與測試後）：`.\.venv\Scripts\python.exe -m unittest tests.test_migration -v`，再於**備份副本**執行 `python scripts/migrate_legacy.py --source ... --dry-run`；正式 switch 依公司流程處理。

## 6. 公司 GUI／Excel 驗收，之後才打包

- 修改位置：`ui.py`（必要的公司欄位）、`tests/test_ui.py`、`docs/COMPANY-ACCEPTANCE.md`；packaging 腳本此階段尚未建立。
- 需內部資訊：Windows／螢幕縮放／中文字型、Excel 版本與地區格式、公司端點路徑、使用者資料保存政策、EXE 簽章與防毒流程。
- 命令：`./scripts/test.ps1` → `./scripts/run.ps1`。依 docs/USER-GUIDE.md 手動走對話、檔案預覽、Plan 修改批准取消、三查詢、跨頁複製、排程、回報、重開。
- Excel 真實驗收：前導零、18 位編號、負數／小數、高精度金額、空值、中文、逗號、引號、公式型文字；全部／選取／不含標題；受占用剪貼簿。核對列欄數與逐字結果，不能只驗 TSV 字串。
- 完成條件：公司 GUI 與 Excel 的版本、操作與結果獨立紀錄；AD／Oracle／chatbot 都通過後，依公司既有流程打包。保留 Tcl/Tk、CA／設定外置、資料目錄獨立；鎖檔若新增 packaging 依賴另做 build lock，不污染 runtime lock。

## 後續中央管理（本次未實作）

AD 中央化權限、可信後端 Oracle schema、常駐中央排程／lease、issue 工作台、跨人協作、簽章完整包更新／rollback 都屬後續另立工作。不要讓公司 agent 因讀到舊 UPDATES.md 就誤以為本地已有更新器。

## 0.5.0 深淺主題與候選圖示（歷史；0.6.0 已採用 A）

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

## 0.6.0 接手重點（歷史；獨立體驗已於 0.7.1 移除）

已完成：A 正式圖示、使用者自管多助理、keyring、固定對話／Plan 路由、資料預覽轉交、Enter／Shift+Enter、獨立五步體驗、離線手冊及聲明。共用 endpoint／API key；名稱、assistant ID、備註由使用者管理。

修改入口：profiles.py 負責公司請求映射及憑證；assistant_views.py 為管理／轉交 UI；core.py schema 2 保存 binding/source，experience.py 管隔離導覽。公司請先提供遮蔽值的成功 API 範例，確認 ID 放 model 或獨立 body 欄位、session 規則及副作用能力。未配置 mapping 的新公司助理不能呼叫，不假裝用示範回答。具體步驟與命令見 docs/ASSISTANT-INTEGRATION.md。

環境新增 keyring==25.7.0，總鎖定套件 29 個；不得使用 keyrings.alt 或明文 fallback。完整離線包以新鎖檔重建，舊包指紋不符必須拒絕。正式驗證用 .venv、.venv-verify060、.venv-offline060，均恰好 Python 3.10.4。

完成條件：公司 API 對話隔離與回傳結果實測、AD／Oracle 核准接線、Excel／Windows 中文輸入法與縮放人工驗收。未實測項目仍保持 not_tested，不能以合成測試替代。中央協作、遠端更新、EXE、任意 SQL 及助理自動分工不在本版。

## 0.7.0 工作區改版（沿用）

- 原生 Tkinter／ttk，未新增 runtime 套件。HTML／CSS 只是可離線開啟的視覺稿，入口 docs/design/workspace.html，不嵌入正式應用。
- 工作／管理／協助分組、原創線條 PNG、820px 聊天閱讀寬度、可選取的訊息卡片樣式、3～6 行整合輸入框及真實任務狀態。
- 工作詳情由明確選定的 task／plan ID 取得，顯示來源與助理版本；寬度至少 1380px 使用右欄，較窄以附屬視窗呈現。切換聊天不會改送正在執行的工作，已開啟詳情保留明確選定的來源。
- 開發改用固定檢查／測試腳本。沒有變更防毒設定、例外或執行政策；Norton 是否不再警告尚未確認，見 docs/NORTON-DEVELOPMENT.md。
- 沿用 Python 3.10.4 三個合格環境、29 個鎖定套件與 schema 2；公司 API、AD、Oracle、Excel 及原生中文 IME 仍需現場驗收。

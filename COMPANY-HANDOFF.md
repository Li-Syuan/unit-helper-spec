# 公司接手工作包 — GPT 6 sol

**先保留本機可用功能，再逐一接公司服務。** 目前程式為 0.3.1，已完成桌面介面整理。 本次沒有公司原始碼、成功 API 樣本、AD 配置、Oracle schema 或真實 Excel。不能把下列事項描述成只填密碼就保證完成。

## 0. 已完成與不可重做

已完成：Python 3.10.4 獨立環境／鎖版、Tkinter、SQLite、固定 Plan gate、選項、三項合成查詢、文字／檔案、OpenAI SDK adapter、本機排程、通知、回報草稿。詳細證據見 VALIDATION-LOCAL.md。

程式入口 `python -m desktop_app`；介面見 `desktop_app/gateways.py` 的 Protocol；業務流程 `core.py`；UI `ui.py`。不能換框架、把真實模式失敗變成 demo、把測試跳過當通過、把舊 SQLite 刪除或覆蓋。GPT 6 sol 是開發 agent，不是這個產品必須呼叫的模型識別。

## 1. 重建公司 Python 3.10.4 基準

- 修改位置：`scripts/setup.ps1`、`requirements.lock`、`ENVIRONMENT.md`；預設不必改程式。
- 需內部資訊：公司核准的 Python 3.10.4 x64 完整安裝路徑、Tcl/Tk、pip 鏡像、代理與可信 CA。
- 命令：`./scripts/setup.ps1 -PythonExe 'C:\實際路徑\python.exe'`，接著 `./scripts/test.ps1`。
- 完成條件：doctor 確切版本／64 位元／Tk 成功，pip check 成功，所有本機測試通過。另建 `.venv-verify` 重跑，留存公司自己的 stdout、exit code 與版本紀錄。不得借用其他專案 site-packages。
- 若改鎖檔：先記錄原因；在兩個乾淨環境重建及驗證，不僅在舊 venv pip install。

## 2. 接公司 chatbot

- 修改位置：先用 `config.example.json` 建本機設定；API 差異改 `CompanyAssistant`，保持 `respond(messages,purpose)->str` 介面。
- 需內部資訊：一份公司目前成功呼叫的去識別範例（URL、HTTP method、headers 名稱、SDK 用法、request/response shape）、模型／部署名稱、助理 ID、認證環境變數、session/thread 生命週期、TLS CA、timeout／流量限制、原生工具是否有副作用。
- 預設支援 `client.chat.completions.create(model=..., messages=..., stream=False)`；**不假設平台和 OpenAI 完全相容**。自訂 session、request wrapper、response parser 都在這一個串接邊界處理。不要改成公共 OpenAI URL。
- `header_env` 格式為 `{"X-Example-Tenant":"COMPANY_TENANT_ENV"}`；值是環境變數名稱。`assistant_ref` + `assistant_ref_field` 須依公司文件指定；不傳任意 extra_body。
- 金鑰從 `api_key_env` 指定變數讀取；UI 與 repo 不能保存金鑰。`ca_bundle` 指定可信 PEM；禁止 verify=False。依 IT 的密鑰配送方式設定，不把秘密貼到 agent 對話。
- `verified_side_effect_free` 預留為公司能力紀錄，目前不能繞過 gate。Plan 預覽固定本機表單，完全不呼叫 API；不要只憑 system prompt 說「不要執行工具」就認為沒有副作用。測試連線會真的呼叫 bot，必須先確認測試助理能力。
- 完成條件：真實回覆、401／403、timeout、空回覆、格式錯誤均合理；兩個對話相互隔離；有原生工具的服務需公司側關閉、使用文字專用助理或明確授權路徑；失敗不回 demo；金鑰／HTTP body 不進 log。
- 基準命令：`.\.venv\Scripts\python.exe -m unittest tests.test_gateways tests.test_core -v`。另建立 `tests/test_company_chatbot.py`，以公司測試端點驗證上述事項，再跑 `.\.venv\Scripts\python.exe -m unittest tests.test_company_chatbot -v`。此檔尚未提供，完成接線時新增；不得以缺檔／skip 代替 real_passed。

## 3. 接 AD 與指定員工名單

- 修改位置：`CompanyIdentity.current()`；新增公司登入狀態／授權 adapter，將身分檢查注入 `Engine` 的每個派發入口與排程執行入口。UI 登入畫面只是輸入層。
- 需內部資訊：既有全端登入方式（優先沿用）、AD 網域／LDAP TLS、員工欄位、單位範圍、allowlist 來源、停用規則、session 有效期限、服務帳號治理、離線策略。
- 目前 `local-demo` 是固定本機展示身分，**不能直接把它改名就當 AD**。目前 Store 是單本機 profile，尚無多租戶 ACL；正式共用裝置需依登入者分目錄或補 owner 驗證及資料遷移。UI 隱藏功能不等於授權。
- AD 密碼不得持久化或送給模型；每次查詢與排程重新檢查啟用／名單。授權失敗停止操作，不 fallback demo；現有排程持有人失效須停用並提示。
- 完成條件：允許者可用、錯密碼／錯單位／不在名單／已停用者拒絕；不能讀取其他人的對話／結果；session 過期及離線拒絕策略經公司核准。
- 命令：保留 `.\.venv\Scripts\python.exe -m unittest tests.test_local tests.test_gateways -v`；接線時新增 `tests/test_company_identity.py`，使用公司測試帳號跑同名 unittest module。紀錄真實授權正反案例，不保存帳密。

## 4. 接 Oracle 三項核准查詢

- 修改位置：`OracleQueries.catalog/validate/run`，保持結果契約；公司 agent 可拆出 `oracle_adapter.py`。UI 目前示範查詢的 category／日期欄需對應真實 catalog，若三項模板參數不同，只調整 query form 對 catalog 的映射。
- 需內部資訊：Q01～03 SQL 核准版本、欄位／型別／精度、主表關聯、bind 參數、日期時區、資料範圍、授權身份欄、row cap、timeout、可重試錯誤分類、人工基準結果。
- 原架構要求 DB 密碼在可信服務端。優先接公司**既有**核准查詢服務；此 repo 沒有另造共用 API。如公司要求桌面直連，先取得其帳號／密碼治理與資料權限方案核准，不把共享 DB 密碼打包至桌面。不要因這個工作包擅自建立整套中央平台。
- 模型只能選核准模板與參數，不能執行模型生成 SQL。使用 bind 與 server-derived scope；有限讀取、明確截斷；Decimal／NUMBER 轉精確字串，不經 float。結果 `columns` 的順序與 `rows`（list of lists）一致，需含 query_ref、parameters、source_label、fetched_at_utc、row_count、truncated。
- `validate` 必須是純驗證，不執行 DB 查詢；查詢前再次授權。`run` 只能唯讀；不要把一般 Oracle driver 例外都標成可重試錯誤。
- 完成條件：三項各有正常／空資料／界線／越權／超時案例，與同條件人工 SQL 結果逐欄校對；不把 DEMO 資料標成公司資料。
- 命令：`.\.venv\Scripts\python.exe -m unittest tests.test_gateways tests.test_files tests.test_core -v`；新增 `tests/test_company_queries.py`，以去識別 fixture + 公司唯讀環境測試，並保存人工比對結果。正式測試需公司環境，不能在本機合成結果上蓋 real_passed。

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

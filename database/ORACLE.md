# 工作台 Oracle schema 設計草案

這是供 DBA／開發者核對的設計，不是已部署資料庫。沿用公司 Oracle，不引入 PostgreSQL。假設至少 Oracle 19c、Unicode 可完整保存繁中；公司實際版本與 driver 支援需在 M0 核對。不使用 23ai 專用 JSON／SQL BOOLEAN。

## 1. 帳號與資料邊界

- 建議獨立 `UNIT_HELPER` schema，名稱由 DBA 核准；不改既有員工／業務表。
- schema owner 僅部署用；runtime account 只具工作台表必要 DML。
- 業務查詢另一唯讀帳號，只對三項 query 使用的核准 View 有 SELECT。
- 不存 AD 密碼、助理 API key 或 Oracle 密碼。資料庫只放 secret reference／連線名稱，實際秘密沿用公司存放機制。
- 本表的 member 是應用授權補充，不取代 AD 或員工在職主檔。

## 2. 共通型別與規則

ID 使用由應用產生的 UUID `VARCHAR2(36 CHAR)`；時間 `TIMESTAMP(6) WITH TIME ZONE` 並以 UTC 寫入；狀態 `VARCHAR2(32 CHAR)`＋CHECK；flags 用 NUMBER(1)＋0/1 CHECK；可修改記錄有 NUMBER(10) row_version。

JSON 使用 CLOB＋`IS JSON` CHECK，應用再做 schema validation；Oracle 官方支援以 CLOB 保存 JSON 並建議加 JSON 檢查。[Oracle 19c JSON 文件](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/json-in-oracle-database.html)

所有表有 created_at，變更表有 updated_at；FK 欄位與主要查詢條件建索引，禁止一般 cascade 刪除整串稽核紀錄。大小上限由 API＋應用驗證，不能以 CLOB 無上限無限制寫入。

## 3. 表與欄位

| Table | 主要欄位（除通用欄位） | 限制與用途 |
|---|---|---|
| UH_MEMBERS | subject VARCHAR2(255)、employee_id VARCHAR2(64)、unit_id VARCHAR2(64)、role、active、allowed_queries_json CLOB | subject 為 PK；role member/maintainer；worker 執行前仍核對員工來源 |
| UH_CONVERSATIONS | id、owner_subject、title VARCHAR2(200)、provider_session_ref VARCHAR2(500)、archived NUMBER(1) | FK owner→members；owner+updated_at index |
| UH_MESSAGES | id、conversation_id、sequence_no NUMBER、role、content CLOB、source_message_id、status | UNIQUE(conversation_id,sequence_no)；原文與改寫另存 |
| UH_UPLOADS | id、owner_subject、storage_key VARCHAR2(500)、display_name VARCHAR2(255)、mime、size_bytes NUMBER、sha256 CHAR(64)、expires_at、state | metadata；原檔在後端受限目錄，過期清除；不得直接以原檔名寫路徑 |
| UH_QUERIES | query_id VARCHAR2(64)、query_version NUMBER、name、description CLOB、sql_text CLOB、params_json CLOB、columns_json CLOB、scope_rule VARCHAR2(64)、timeout_seconds、max_rows、max_bytes、enabled | 複合 PK(query_id,query_version)，版本發布後不可改內容；預設 disabled |
| UH_TASKS | id、owner_subject、conversation_id?、kind、state、request_json CLOB、result_json CLOB、error_code、trace_id、query_id?、query_version?、attempt_no、deadline、lease_token、lease_until、remote_request_ref、plan_id?、plan_revision?、phase? | kind chat/query/rewrite/summarize/legacy/plan；query refs 成對 FK；owner+created_at、state+lease_until index |
| UH_SCHEDULES | id、owner_subject、name、query_id、query_version、rule_json CLOB、bindings_json CLOB、notify_json CLOB、timezone、enabled、next_fire_at、previous_success_hash CHAR(64)、previous_condition NUMBER(1)?、previous_success_task_id? | FK query version；enabled+next_fire index；每次執行驗證 query 還有效 |
| UH_OCCURRENCES | id、schedule_id、scheduled_for_utc、schedule_version、state、task_id?、lease_token、lease_until、reason | UNIQUE(schedule_id,scheduled_for_utc)，task_id UNIQUE；state pending/running/succeeded/failed/missed/skipped_overlap |
| UH_NOTIFICATIONS | id、owner_subject、task_id?、issue_id?、notification_key VARCHAR2(500)、kind、title、body CLOB、read_at | notification_key NOT NULL UNIQUE 防重；owner+read_at+created_at index；不得含來源無權資料 |
| UH_ISSUES | id、reporter_subject、type、title、description CLOB、expected_result CLOB、context_json CLOB、app_version、feature、trace_id、priority、status、duplicate_of?、resolution CLOB、resolution_type、fixed_release_id? | 自參照 duplicate_of，不允許指自己／循環；status 見 OPERATIONS；context 限使用者同意副本 |
| UH_ISSUE_EVENTS | id、issue_id、actor_subject、event_type、public_text CLOB、changes_json CLOB | append-only；reporter 可看公開處理說明，管理內文隔離 |
| UH_RELEASES | id、version VARCHAR2(32)、release_sequence NUMBER、platform、channel、manifest_bytes BLOB、signature_bytes BLOB、storage_key、sha256 CHAR(64)、size_bytes、published_at、status | UNIQUE(version,platform,channel)，UNIQUE(release_sequence,platform,channel)；發布後內容不可變 |
| UH_REQUEST_KEYS | owner_subject、operation VARCHAR2(100)、request_id VARCHAR2(64)、request_hash CHAR(64)、resource_type、resource_id、status、expires_at | 複合 PK(owner_subject,operation,request_id)，至少 7 天留存；建立資源與 key 同交易 |
| UH_AUDIT | id、actor_subject、action、target_type、target_id、result、trace_id、safe_metadata CLOB | append-only；不放 credentials、原始對話／完整 query rows |
| UH_PLANS | id、owner_subject、conversation_id、state、plan_revision、goal CLOB、snapshot_json CLOB、preview_hash CHAR(64)、expires_at、approved_by?、approved_at?、approved_revision?、approved_hash?、execution_task_id?、assistant_call_count | state 見 Plan 契約；row_version；UNIQUE(execution_task_id)；snapshot 含來源 ID/hash、固定步驟／參數；owner+updated_at index |
| UH_QUESTION_FORMS | id、owner_subject、task_id、plan_id?、plan_revision?、form_version、purpose、state、expires_at、questions_json CLOB、value_map_json CLOB、answers_json CLOB?、submitted_at?、result_ref? | row_version；state open/submitted/expired/cancelled；owner+state+expires_at index；result_ref 指唯一 disabled 排程草稿等已完成結果 |

? 表 nullable。中央 FK（notifications→issues→releases）以建表後加 constraint 的 migration 處理，按依賴先建 releases、issues 再加引用；避免直接照表格列序執行。issues 的 fixed_release_id FK references releases，不用自由文字版本混淆。

本 schema 不加入 agent_nodes、角色市場、Skill 發布、向量索引、多人專案 ACL 等延後功能。對話只支援個人隔離，單位名單與 query grants 先以 member 欄位保存。

## 4. 重要交易與一致性

### 提交請求

驗證身份與參數後，在同一交易 insert request key＋task＋必要 message；撞 unique 時查既有 hash，相同回 resource，不同 409。不可先派出公司 API 再補去重紀錄。完成結果與相關 message/notification/audit 同交易 commit。

### Claim 與排程

Oracle row lock 或等價 CAS 保護 claim，不能 SELECT 後在另一無鎖交易 UPDATE。worker claim 時寫 lease token；完成提交的 WHERE 要包含相同 token＋合法 state。不要在持有 DB transaction lock 時等待 LLM／Oracle 業務查詢；先 claim commit，再外部工作，再驗 lease commit 結果。

建立 occurrence＋task＋next_fire 為一個短交易。skip/missed occurrence 無 task 也可保存；通知源為 task 時保證 owner 一致。Task cancelled 不被晚到結果復活。

### 權限與刪除

每個 object read/export/list 都包含從 session 得到的 owner 範圍；不能只靠列表過濾卻讓 get-by-ID 漏資料。member 停用後取消未開始工作、停用 schedule，保留歷史稽核。刪除帳號採停用，不用 FK cascade 清掉 issue、排程與結果。

## 5. SQLite 舊資料遷移

原 DB 唯讀盤點＋一致性 backup → 脫敏 schema mapping → dry-run 產筆數／附件／排程時間報告 → 先匯入停用的中央項目 → 核對 → 切換。migration map 記 source_install_id、source_entity、source_id、target_id，匯入重跑不重複；若 existing platform 無此表，另建 `UH_IMPORT_MAP`（前三欄複合 PK）。

舊 source owner 無法確認時歸待確認，不批次公開給單位所有人。舊資料格式未知，開發 agent 必須先讀公司 schema，不能依此規格臆造舊 column。回退時需先停新 scheduler，再恢復舊 runner，避免新舊雙跑。留存原 DB backup，不在桌面更新時回滾中央資料庫。

## 6. v2.1 計畫與表單交易

UH_TASKS.plan_id FK 指 UH_PLANS，UH_PLANS.execution_task_id 反向 FK 指 tasks；採先建表後補 FK。task phase 僅 planning/execution；UNIQUE 約束的條件索引只對 phase=execution 的 (plan_id,plan_revision) 生效，planning 可有多個 task。execution task 的 plan_id/revision/phase 必須一組非空，owner 必須一致；query 的原固定版本 FK 保留。UH_QUESTION_FORMS 的 task、plan FK 與 owner／修訂一致性由服務及交易檢查。

plan_revision 只因內容修訂增加；row_version 因任何修改增加。批准檢查與寫入 approval、execution task、request key 及 executing 狀態同交易。回答表單的 CAS＋保存答案＋更新參數／修訂或取得唯一 disabled schedule 草稿同交易；表單 submitted 後不再套用答案。Plan 執行副作用不能先於確認 commit。worker 重啟只領取已批准的 execution task，取消／完成提交需 lease 及合法狀態。

資料保留與 private owner 規則同對話；附件期限不延長，confirmed snapshot 不含憑證。詳細狀態與錯誤見 [Plan 契約](../PLAN-AND-CHOICES.md)。此處依然是 DBA 待核對的設計，不是已部署 DDL。

## 7. v2.2 展示資料

此版不新增中央資料表。query display 從受控查詢目錄載入，仍跟隨 query version；結果原有 result_json 保存欄位 label／copy_as_text／順序。舊 snapshot 缺 label 時用 name，copy_as_text 缺省 false，但識別碼／高精度欄位須於公司模板核對後設定。一般既有文字型態的公式防護不因旗標缺省而取消。

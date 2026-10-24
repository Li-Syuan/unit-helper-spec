# 1.0.0rc4：統一對話與兩入口工作區

當前主Store8、DialogueStore5、Python3.10.4及69wheels。下方版本段落為既有模組的沿革；本節為目前主畫面與對話契約。

`workspace_turns.py` 協調 DialogueService 與 AgentJobs，Web／CLI共用。新對話 mode=auto 的單次回覆以 `dialogue_routing.py` version1 取得文字與意圖建議；chat直接顯示、clarify請使用者選擇、work以固定來源識別建立待確認計畫。後續補充走原AgentJobs，不送回聊天thread；工作及成果僅顯示，不自動加入聊天歷史。工作確認後composer回一般聊天。

schema5的dialogue_routes分開保存raw wire與顯示建議，workspace_views保存active_job／skill_id，routing_checks保存分項能力。舊1～4先backup再交易升級；舊chat/task不改協定。兩庫連結以來源thread/request的固定雜湊識別防重，不宣稱跨庫斷電原子性。讀取／重開只還原畫面；真future仍保護取消、刪除及關閉。

`activation.run`依序最多8次，工具核准必須先做；2輪同thread聊天兼驗辨識、3次工作格式、3次自主格式，各項證據同助理revision，失敗／取消不自動重測。搜尋是另一次明確測試。metadata失敗不阻擋聊天驗證。畫面 `workspace-ui.js` 與 `activation.js` 不自行判定工作成功或批准；原WorkflowService／LangGraph仍執行所有工作。


## 自主決策與共用工作核心

新交辦預設自主處理：`autonomous.py` 提供固定的搜尋、文字分工、彙整與補問動作目錄，主助理每輪提出結構化建議，由服務驗證後執行。`graph_runner.py` 在原 LangGraph 中加入 decide／act 條件循環；WorkflowService 仍是唯一工作狀態及執行服務，不新增另一個 runner／排程器。舊 agent.version=1 與無 agent 的流程沿原固定圖執行。

批准快照 agent.version=2 固定目標、要求、Skill／記憶、所選助理版本、搜尋工具及限額。主 Store schema8、DialogueStore5；動態決策與動作保存在既有 workflow_steps，定義、訊息與收據先保存，checkpoint只保存控制位置及指紋。每次派發前檢查身分／綁定並保留額度；預設6動作／12模型請求／600秒，工具結果續答也計數，恢復不重置。未知送出不retry；確定原run／快取才明確恢復。搜尋結果需工具收據；最終引用只能來自已取得搜尋文字，內容真實性仍需人核對。

規劃與自主決策停用工具；`autonomous` 能力須另外最多3次合成格式斷言，舊planner／assess不能替代。分工只在所選已驗證文字角色依序執行，不是並行子代理。停止後明確新建可保存來源task識別，不自動轉交成果、記憶或批准。畫面／CLI共用服務；真實DVC、AD及來源品質仍須現場驗收。Python3.10.4與69wheels未變，完整Hermes尚未移植。詳見[工作代理](AGENT-WORK.md)。

## 三欄啟用、對話續談與記憶

主Store維持schema8，DialogueStore目前schema5。`activation.py`提供endpoint/ID/key直接設定、選用部署預填與明確兩輪聊天斷言，CA預設系統信任；`continuity.py`提供記憶預覽/確認、對話草稿CAS/閱讀位置、固定快照與接續。WebView與CLI共用；Tk保留舊功能。記憶只在明確的新對話預覽或Skill選取後傳送，不背景挖掘或共享。

新資料在目前登入者既有資料目錄；對話來源可失效，不搬移舊進階歷史。記憶加入送出的固定歷史前綴，但顯示與原訊息分開；不在重試時換用最新記憶。摘要工具停用，未知摘要請求不重送，人工整理仍可建立新草稿。1.0正式版需現場驗收，候選版不代表DVC/AD已通過。

主對話資料夾由continuity.py共用服務管理，dialogue_folders保存名稱/收合/修訂，thread_views外鍵刪資料夾時只清分類。自動名稱為本機第一句摘取、手動名稱優先；不新增模型請求。WebView顯示單層可收合分組，CLI可列出、新增及移動。

## 0.23.0 自建 Skill 與單助理規劃

主 Store 當前 schema **8**；下方舊版 schema 敘述為歷史。skills.py 管定義、不可變修訂、分享、相容性證據與 Skill 流程來源，WorkflowService／LangGraph仍是唯一執行管線。規劃與執行只提供所選單一助理、rag與compose；不套四角色提示。能力證據獨立於舊 workflow verified，必須經明確合成實測；修改連線或重新測試使舊證據失效。批准快照固定方法、條件、助理版本，每次排程注入當次台北日期。

Skill Plan請求先保存原訊息與識別；未知POST阻止再次討論，檢查／取回沿原收據，取消後不復活。生成草稿與相容性同步I/O也登記真實future，關閉與改憑證等待實際收尾。WebView skills.js與CLI共用服務，無新增依賴、任意shell、背景選Skill或第二排程器。停用／刪除先列出關聯排程並暫停，保留成果；MD僅是資料。操作／格式見 [SKILLS](SKILLS.md)。

## 0.22.0 共用工作台

work_orders.py 為每日搜尋交辦服務；WebBridge與CLI共用。規劃只提scope/sources/time_hhmm、不開工具，確認試跑才交既有AssistantBriefings／Engine，人工核對與持續授權後才排程。主Store升schema7保存獨立交辦，既有schema1～6一致備份後交易遷移；其餘資料庫版本不變。work_orders的state只是需求整理狀態，執行與排程狀態從既有資料讀取。

WebSession增加start_scheduler（桌面預設true，CLI false），沿用單實例鎖與授權。CLI為固定操作入口、無shell/eval/任意bridge。WebView tray.py用既有WinForms NotifyIcon保留同程序；失敗不隱藏、真正退出drain不持bridge鎖。Skill是操作指引而非授權。詳見[工作台](WORKBENCH.md)。schema6/7為歷史，當前主Store為schema8。

## 離線登入展示與現有AD閘門

`demo_login.py` 僅記憶體fixture；`--demo-login`／`start-demo-login.bat` 先原生登入，再建立空白暫存WebSession，禁公司設定／probe，登出撤銷並關閉。company_auth既有可信hook不變；人事資格尚未接線。詳細邊界見 LOGIN-AND-APP-ACCESS.md。

# 本次待辦與交付更新

WebView「我的待辦」使用 work_inbox.py 聚合既有 plans／workflows／conversation_actions／tasks及主對話最新未完成request；唯讀、不另存工作狀態、不派發。導回原流程确认或查看成果；主對話有未送出文字時拒絕切換。個人todos仍獨立，支援台北到期篩選、說明搜尋、紀錄與來源失效提示。Tk備用維持既有看板。

test-company.bat／scripts/company-test.py 為離線單一驗證入口，隔離診斷設定、語法檢查、一次full及真WebView2合成旅程。沒有依賴／schema／角色權限改動。公司真實服務仍not_tested。操作與DVC核對見 ONE-CLICK-TEST.md、DVC-REVIEW.md。

# QA agent 0.20.0 現行架構

Assistants 連接依官方頁面 2719802 核對；assistant_errors.py 提供安全分類，config 接受單次30秒／總工作600秒預設。DialogueService 只對持久化的未派發 preflight 失敗提供 retry_unsent；缺少遠端紀錄不是證據。Profiles 提供共用／個別 keyring 金鑰與連線修訂，聊天搜尋另需 chat_search_enabled，不因已有搜尋 policy 自動開放。無新依賴或資料庫遷移。

WebView主要交付，Tk備用。主Store仍schema6；獨立DialogueStore升schema2，先SQLite backup、交易遷移，保留task_drafts CHECK=0。DialogueService保存失敗原request；inspect只讀、recover沿同ID用已知run/cache，unknown POST/取消不可重送。另開對話預設僅草稿；明確預覽確認才複製歷史。新恢復入口的I/O不持有bridge全域鎖。

DataCleanup管理本機工作／成果、計畫、流程、停用排程、回報、通知與表單；DialogueService管理主對話／草稿。刪除10分鐘一次token、快照、鎖、交易、真future／session guard，忙碌整批拒絕。tasks刪內容但留deleted tombstone防舊request重派發，Store.tasks不列出。來源排程已刪須明示，不把它誤當手動成果。company remote／獨立副本／備份保留，系統支援log無UI刪除。

support.py白名單logs/events.jsonl輪替與ZIP匯出；嚴禁原始exception／HTTP body／金鑰／URL／絕對路徑。錯誤編號可分享，不代表已確認原因。正式離線69wheels保持原lock，Python/WebView2/.NET不含於wheel包。check-launch新增LangGraph匯入检查；full仍依doctor/pip/lock先驗環境。本機合成恢復通過不能宣稱組織多ID或搜尋已實测。


## 開發驗證

作者資訊由 `about.publisher_info` 讀取固定 `publisher.json` 的三個白名單文字欄位；WebView 右上角 popover（`web_assets/author.js`）及 Tk 側欄小卡只讀取資訊，不派發工作。缺值顯示尚未設定，公開版本只有空白範例。介面採用「工作區／AI 助理／連線設定」中性文案，既有 company 設定值與服務識別保持相容。

正式離線入口install-offline.bat不需PowerShell；全部69wheels與lock核對後新建環境。日常targeted/quick，交付verify.py development一次full；真WebView smoke及組織實測分開記錄。

## 外觀與組織核准搜尋

設定→外觀提供深海青藍、星霧紫、森林青綠預覽卡，與深淺外觀獨立保存；失敗保留本次選擇並提示重試，恢復預設只重設dark/ocean。WebBridge appearance只接受theme/color_style白名單，ui-preferences保存兩值，不修改連線設定或工作。Tk備用提供同名選擇。

工作區使用深藍灰／霧藍白配色；青藍操作與未讀、紫色團隊、琥珀待確認、藍色執行、綠色完成、紅色失敗。WebView 沿用真實 task 狀態呈現，Tk 備用同步主題；通知以 is_read 顯示已讀，只有明確查看才標讀。服務 API、schema、依賴與核准流程不變。

官方手冊確認 Internet Search 插件與通用 pluginapi 呼叫流程，參考 [接線契約](ASSISTANT-INTEGRATION.md)。使用者已批准有限搜尋；metadata 核准表單、參數驗證、同源工具往返、回執防重與日報搜尋紀錄已實作。組織真實搜尋仍待現場驗收。

新增連線啟用檢查及明確的助理 metadata GET，與模型呼叫分開。CompanyProbe 追蹤實際請求與關閉；本機設定存在、金鑰來源設定或工具名稱都不代表能力已驗證。

`AssistantBriefings` 使用既有 Engine 的背景派發、取消、防重及排程時鐘，新增 assistant_briefing 工作種類與 ASSISTANT_BRIEFING 排程識別，不變更 schema。預覽→一次試跑→人工核對／持續傳送同意→每日排程；主對話、設定與自動工作皆可開啟，活動紀錄可重開成果。結果保留完整文字，search 固定 not_tested；實際搜尋及事實準確性另驗。

試跑及每次排程依 task ID 隔離組織遠端 thread。排程保留已批准需求、助理版本與台北 HH:MM；使用當次執行時間，App 開啟才運作。失敗、取消、中斷或綁定失效時暫停；取消後尚未結束的請求仍阻擋重疊。多助理 WorkflowService、未啟用任務草稿與工具限制保持原契約。

# 正式 LangGraph 與組織 Assistants

正式依賴加入 LangGraph 1.2.12、SQLite checkpoint 3.1.1 及其間接依賴，不使用高階 LangChain agent 或 langchain-openai。試驗包保持獨立，正式 lock 由 App 的乾淨環境重新建立。

WorkflowService 保留需求討論、純本機預覽、十分鐘確認、版本綁定與 task 狀態。graph_runner保留已驗證順序步驟，agent.version=2另使用decide／act有界循環；沒有平行派發、自動retry或雲端tracing。checkpoint 僅保存工作／步驟識別及定義指紋；業務成果仍以主 Store 為準。重開不自動呼叫，恢復前核對步驟收據與 checkpoint；任一不一致停止。

AssistantsGateway 使用 Threads/Messages/Runs。Profiles.respond 增加可選 context；workflow_call 傳遞 run_id、step_id、取消檢查與明確 resume。assistant-sessions.sqlite3(schema1) 保存遠端 ID、請求收據、歷史雜湊及回覆快取，不存金鑰或 endpoint。訊息／run 建立前先保存結果可能不明的狀態；未知寫入不重送，已知 run 可明確查詢及恢復。獨立資料庫首次建立，主 Store 維持schema6；獨立dialogue目前schema2。

ProfileDialogueProvider 讓主畫面明確選擇示範／組織；一般聊天沿用對話 thread。建立任務每輪帶完整已顯示歷史與草稿，使用獨立遠端 thread，避免 JSON 原文與 UI 顯示訊息混用；只有 confirm 能存未啟用草稿。主畫面有對話紀錄與取消入口；I/O 不持有 bridge 全域鎖，關閉先阻止寫回並等待請求收尾。

搜尋 policy 與助理連線 revision 綁定。經確認的 assistant_briefing／rag 步驟與另行勾選 chat_search_enabled 的普通聊天使用核准 tools＋auto；其餘呼叫 tool_choice=none。未知工具、錯誤參數整批停止。最多4工具／批、3批／run、600秒、單回覆128KiB。請求與工具回執保存原有 assistant-sessions SQLite JSON，不更改 schema 或依賴；工具POST／submit結果未明不重送。核准變更在派發鎖內完成並拒絕真實請求未結束時修改。來源與事實仍需人核對。

新增 workflow_inspect、workflow_resume、workflow_abandon 僅由明確 UI 操作呼叫。人工重試不允許繞過未釐清遠端請求。既有結束結果可讀，舊工作不自動遷移為可恢復 graph。正常關閉中的工作仍取消；意外中斷或可查的未明遠端 run 提供人工恢復。

以下為目前介面與本機服務契約。

# WebView 介面與兩模式對話

可選的 `experiments/langgraph-lab` 提供真正 LangChain／LangGraph 套件與合成節點試驗，使用獨立環境及 checkpoint 資料，不被 App import、不修改上述正式對話／排程。其離線包與驗證說明見 [試驗入口](../experiments/langgraph-lab/README.md)。

主入口是 pywebview + WebView2，HTML/CSS/JS 全部隨專案提供，無 CDN／遠端字型／遠端頁面。`web_app.py` 管宿主，`web_bridge.py` 僅允許列舉命令，`web_session.py` 組合既有 Engine／Profiles／Store。`web_render.py` 使用 markdown-it-py 與 bleach，回覆移除腳本、屬性、圖片及連結，不執行模型 HTML。Tkinter 保留 `--ui tk`／start-tk.bat。

新主畫面是無附件的兩模式對話，預設示範、AI 助理須明確選取。`dialogue_provider.py` 提供服務 Protocol、本機示範及 ProfileDialogueProvider；`dialogue_contracts.py` 驗證助理、草稿和每日／每週／指定日期格式；`dialogue_service.py` 管多輪、修訂、十分鐘預覽及明確確認；`dialogue_store.py` 保存獨立 `dialogue-v1.sqlite3`（schema2，升級前備份）。Assistants wire contract 已依提供範例實作；組織部署、可信 CA 與角色能力仍需現場驗證，失敗不自動換示範。

新任務的 enabled 固定0且有資料庫 CHECK，既有 Engine／排程器不讀這個資料庫，因此『儲存』不代表能執行。正文中的檔案路徑或命令只是文字，不觸發檔案讀取或 shell。改模式／助理開始新thread，不永久刪歷史。錯誤不寫入半套訊息、草稿或任務；確認失敗可重試，同修訂只存一次。

既有主要資料庫仍 schema6，多助理、Plan、防重、取消、排程及組織 adapter 契約不變，位於進階工作區。下方原生 Tk 功能說明同時作為備用介面的契約。

# 既有進階功能與 Tkinter 備用架構

本文件是現行行為契約。程式與 UI 已完成本機功能；服務接線見 [工作單](../COMPANY-HANDOFF.md)，實測與未測項目見 [驗證摘要](VALIDATION.md)。

## 分層

Tkinter 備用介面的 `navigation.py` 管理原地收合側欄，`team_views.py` 管理助理卡片與既有管理入口，`workflow_presenter.py` 純讀取分工清單。新版 WebView 透過橋接沿用相同服務。團隊狀態依 Profiles 真實設定顯示；UI 不建立能力驗證紀錄，不因進入團隊或選步而呼叫模型。

一般使用者路徑是「說需求 → 核對分工 → 一次確認執行」。主要按鈕旁明示此版本資料傳送，點擊後才提交 consent；服務層修訂、綁定、防重不变，未來修訂不沿用授權。助理 API 與能力啟用仍由服務接線者負責，不承諾任意 assistant ID 都可直接自動協作。

新增選用的 Groq 個人試用入口 start-trial.bat。trial.py 管固定端點／模型、有限 .env 讀取與唯讀助理清單；--groq-trial 與 --config 互斥。App 使用獨立 groq-trial 子目錄及預設合成查詢／身分，不讀組織 config 或 profiles。原入口與 adapter 契約保持相容；本機 schema 6 保存對話來源、協作流程及成果回饋。不是恢復舊導覽流程。

| 模組 | 責任 |
|---|---|
| desktop_app/ui.py | Tk 畫面、主執行緒事件、背景 IO 回傳、表格／預覽 |
| desktop_app/guidance.py | 原地提示、狀態說明及對應手冊入口；只讀取 UI 現況 |
| desktop_app/experience.py | 離線手冊、關於與環境診斷入口；不再啟動獨立體驗 |
| desktop_app/core.py | Store、任務／Plan gate、受限工作流程、本機排程與通知 |
| desktop_app/local_work.py | 待辦、版本化草稿及本機保存契約 |
| desktop_app/todo_views.py | 待辦看板、窄版分頁、編輯與來源入口 |
| desktop_app/draft_views.py | 延遲保存、失敗重試、恢復與關閉補存 |
| desktop_app/work_cards.py | 組織可調整的三張文字工作卡片 |
| desktop_app/choices.py | 持久化 typed 選項、owner／版本／期限／一次提交 |
| desktop_app/gateways.py | 身分、組織 OpenAI 相容助理、查詢介面與合成實作 |
| desktop_app/files.py | UTF-8 上傳驗證、CSV／TSV 安全輸出 |
| desktop_app/query_schema.py | 動態欄位、純型別驗證、顯示與日期映射 |
| desktop_app/config.py | 本機設定、資料路徑、單一執行個體鎖 |

UI 不直接持有 SQL、密碼或 HTTP 細節。組織請求映射與憑證集中 profiles.py，SDK 傳输維持 gateways.py；未來需要獨立 adapter 檔可在保持介面下拆出，不重寫 UI。

## 工作區與原地操作提示

啟動直接進入對話，提供試查一筆資料、整理一段文字及自行輸入。四個主入口為對話、我的待辦、自動工作、活動紀錄；更多工具保留查詢、結果及進階紀錄，設定與回報在底部。無獨立體驗模式。

ActionService 保存 conversation_actions：來源對話、kind、request、spec、binding、revision、draft/submitted/cancelled 及 task／schedule／plan 連結。真實執行狀態即時讀既有紀錄；schedule_sources 是可失效來源，不是執行歸屬。查詢及排程工作不強加 conversation_id。messages 僅聊天歷史，卡片、表格、通知不自動送模型。

create/update/get/list 管草稿與來源；preview 純驗證並產生10分鐘記憶體確認快照；confirm 重新驗證修訂與綁定，使用固定request ID、Engine鎖及交易同時保存工作／排程與連結。重開草稿重新預覽，不自動批准；已受理不重建。Plan 使用既有修訂與批准契約，每次新修訂另建卡片，舊卡失效。

begin_parse/end_parse 追蹤實際解析工作，apply_parse 驗修訂與來源存在；取消或刪除後舊结果不寫回。刪除快照包含操作記錄，進行中及取消後未結束的即時工作／解析阻擋刪除。刪除清連結，獨立表格及排程保留，排程來源變空並顯示已刪除。

Text 時間線以穩定事件及 marks 增量更新，原生同頁操作區可收合；前三種工作入口只準備草稿。表單沿 catalog，完成条件自動本機預覽，使用者才可確認。Groq 試用可解析需求；組織解析能力預設關閉，不 fallback 外部。頁首提示可收合且保存偏好，必要標示不隱藏。

## 對話、Plan 與選項

對話歷史完整保存，送給 SDK 時使用指定對話的不可變快照；同一對話尚有工作則拒絕重疊提交。總內容超限拒絕，不靜默裁切。
一般模式明確送出即執行。先規劃模式只建立本機固定候選，不呼叫 bot。只有 `confirm_plan` 成功才建立工作；24 小時期限、修訂比對、原子交易與 request ID 防止舊卡片／雙擊重跑。修改需重新批准。桌面流程限查詢、對話、摘要、改寫；查詢後整理須預覽並確認轉交。舊獨立 Engine 契約保留 query_summarize，但桌面的 routed Engine 拒絕直接自動整理。

選項有 yes_no／single_choice／multi_choice；最多 3 題，每題 2～6 選項。未選不當同意，未知值與數量不符拒絕；owner、version、expiry、request ID 由本機服務檢查。取消後不可提交。選項答案不等於任意工具授權。「是，設排程」只開設定，仍建立停用草稿並另確認啟用。重開待答表單可保存答案，**不重播先前 UI callback**，使用者回原工作繼續。

取消在派發界線前阻止新助理呼叫；界線後可能已送出至組織，不能保證遠端撤回。晚到結果不寫回已取消工作。已完成查詢表格可保留，摘要失敗不重跑查詢。未結束的真實 future 會阻擋切換設定，即使工作已標取消。關閉等待遠端 drain 後才釋放資料目錄鎖。
支援經批准的有界限多助理依序協作；沒有持續自主 Goal、通用 shell／任意 SQL或執行時動態增派代理。

## 對話刪除

最近對話的右鍵提供單筆刪除；「管理對話」可依標題搜尋、勾選多筆與全選目前搜尋結果。變更搜尋條件會清除已被隱藏的選取，不把看不到的對話暗中加入刪除。確認顯示對話名稱與數量、訊息／Plan／工作／通知數量，預設焦點在取消，明示永久刪除與無法由應用復原。

Engine.preview_conversation_deletion(ids) 回傳 token、conversations、counts、task_ids、plan_ids；Engine.delete_conversations(token) 回傳同摘要及 deleted_ids。token 在服務端保存選定 ID 與完整資料快照指紋，10 分鐘有效，成功後失效；過期、重複或資料變更須重新預覽。確認時在引擎鎖內重新檢查，以單一 BEGIN IMMEDIATE 交易完成整批刪除；失敗全部回復，不改 schema。

範圍限選定對話、訊息、專屬 Plan、工作輸入／結果及其通知，以及該對話的持久化草稿、記憶體草稿／附件引用；待批准 Plan 一併刪除而不執行。另存待辦保留，來源入口顯示「來源對話已刪除」。排隊、執行中或取消後仍有未結束 future 的選定對話會阻擋整批刪除，不能只檢查畫面狀態，不能自動取消。其他對話的工作可以繼續；不正常的跨工作、Plan 或排程關聯拒絕刪除，不擴大範圍。

原始檔、匯出檔、既有備份、獨立查詢／排程、問題回報、選項表單、其他對話及轉交副本保留。轉交副本的來源不存在時顯示「來源對話已刪除」。服務端歷史不在範圍內；此操作不是安全抹除，也不自動新建含原內容的備份。

刪除後關閉選定資料的詳情及未送出轉交預覽，清除對應草稿及附件引用。刪除目前對話後切到最近保留對話；全部刪除後建立一個空白新對話，其他對話的草稿及附件保持不變。已刪對話不可由舊畫面或舊 Plan 再派發。

## 顯示與 DPI

在建立 Tk 前設定 System DPI awareness；啟動環境已有更高感知模式時保留，不強制覆寫。display.py 集中處理顯示倍率與尺寸換算；以 100% 的邏輯像素為基準換算固定尺寸，避免字體放大而容器不變，或字型與容器重複縮放。微軟正黑體主要操作 11 點、聊天本文 12 點、次要提示至少 10 點。

圖示依倍率使用隨附的本機多尺寸素材；常用 24 邏輯像素圖示對應 24／30／36／48 像素，品牌沿用多尺寸資源，不放大小圖充當高解析。一般、拉大與最大化均由原生文字及控制項重排，不把介面當圖片拉伸。小螢幕／高倍率視窗須限制在可用工作區內，內容必要時可捲動，保留送出、取消、批准及刪除確認的操作路徑。

記錄 DPI 感知、螢幕倍率、Tk scaling、實際字型與視窗尺寸，診斷不包含組織內容。本機舊啟動路徑確認為 unaware；最大化的字型點數未改變，因此不能將最大化本身認定為模糊原因，也不宣稱 DPI 是唯一因素。跨不同倍率螢幕的即時 DPI 重排仍需另案驗收。

## 檔案與結果

單一 TXT／CSV，2 MiB、UTF-8／UTF-8 BOM；TXT 最多 50,000 字，CSV 最多 10,000 列／100 欄。標題空白／重複、列寬不一致、NUL、錯誤編碼拒絕。預覽 TXT 前 2,000 字、CSV 前 20 列，送出完整內容；超過助理設定上下文上限則拒絕。沒有多文件、Office 原檔排版修改。

三項 DEMO01～03 為獨立合成查詢。固定日期區間起含迄不含，1～90 日，category all/A/B。最多 1,000 列與 2 MiB，截斷有標記。正式 Q01～03／Oracle 保持停用。
表格 100 列一頁，全部複製跨所有頁；選取列只限當页、換頁清除選取。輸出只讀同一 snapshot，不另查資料。數值用精確十進位字串，拒絕 float。公式型文字加前置 apostrophe；TSV 分隔字元拒絕並提示改 CSV；CSV 有 BOM、標準 quoting。程式保留精確字串，**Excel 自動推斷可能改變代碼／長整數，貼上前要設文字格式；真正 Excel 貼上尚待組織驗收**。不以 `="..."` 公式包裹值。

## Groq 試用日報

只在隔離的 Groq 工作區使用 ReportEngine；一般工作區使用 Engine。intent_drafts 的能力開關只允許 Groq 固定綁定與合成目錄。送出明確查詢／排程需求後以 strict schema 解析，程式再檢查格式；缺少條件留空追問。已知合成範例不呼叫模型。正式模式使用表單，不假稱解析已驗證。

ActionService 的 report 確認強制每日前一日、三項合成模板及 Groq 固定綁定，使用者另勾選持續傳送授權。一次確認建立啟用排程及來源，不立即執行。原對話可現在測試一次及暫停；立即測試不更改 next_fire。原有 preview_report／confirm_report 與獨立視窗保留相容測試，不作主要使用路徑。

沿用 schedules.parameters 的 _report 版本／binding，每次 occurrence 計算前一日。先存完整snapshot，以Decimal精確計算後只送來源、模板、條件、時間、筆數及合計。空結果不呼叫AI；截斷／格式錯誤／超限拒絕。摘要失敗整體failed但表格保留；取消晚到不覆寫，每次結果通知一次，不自動重試。

## 本機排程

以下是一般查詢自動工作；Groq 明確授權日報例外見上節。每日／每週、HH:MM、星期 0～6；台北 UTC+8 固定時區。對話確認卡可從已核對條件或成功結果建立，確認才啟用、不立即執行。進階舊入口仍從成功查詢建立停用草稿，另行啟用。固定參數或每次前一日；後者必須由模板宣告 date_range，依該次預定執行時間解析起含迄不含日期。未宣告者不能使用；舊 DEMO 排程僅對 DEMO01～03 保留明確相容映射。

程式每 3 秒檢查，`unique(schedule_id,scheduled_at)` 防重。同排程不重疊。關閉期間最新 24 小時最多補跑一次，較舊紀錄以壓縮略過標記保存。重開未完成工作標失敗、不自動重送。停用期間不追補。這是單機防重，不宣稱跨機 exactly-once 或分散式 lease。

通知規則：非空且內容 hash 改變；或單一數值首次達標／由未達標轉達標。取得時間不納入 hash。失敗通知一次。只有唯讀查詢的 ConnectionError／TimeoutError 可有限重試，最多 3 次；AI 助理一律不自動 retry。站內通知未讀數可見，無郵件或 OS 背景常駐服務。

## 資料與回報

0.12.1 通知呈現由 `notifications.py` 管理：側欄常駐紅色未讀徽章、新通知右下角非模態彈窗，八秒逾時、滑鼠停留暫停，多則合併。讀取既有通知與真實 task 狀態；關閉不標已讀，明確查看才標讀。啟動只恢復未讀數，不重播舊通知。不新增依賴、schema 或 Windows 背景服務，不改排程通知條件。

獨立 `local-v1.sqlite3`、schema user_version=6、WAL；本應用 schema 1／2／3／4／5 升級前以 SQLite backup 備份，再以交易遷移。無可靠助理歸屬的舊對話保留閱讀／轉交，不接觸舊組織 SQLite。較新 schema 拒絕開啟。單一資料目錄只能一個程式使用；不把本機檔案當授權系統。
回報 draft 可讀取修改，local_saved 只表示保存在此電腦；編號 LOCAL-*。不自動附加對話、資料或檔案，不冒稱管理者已收到。未實作處理狀態同步／修正版本管理。
組織舊資料移轉、中央 API、AD、Oracle、簽章更新及 EXE 打包均另列交接；未接線或未實測項目不得記成已通過。

## 接線工具

catalog 的參數定義支援 text/date/integer/decimal/single_choice/boolean、required/default 與適用範圍。UI、Plan 修改與預覽、結果條件及排程共用定義；decimal 保持文字，未知欄位／模板或不支援定義拒絕。adapter.validate 仍為純驗證且保有查詢商業規則；一般送出／批准與排程服務均檢查。細節見 [查詢契約](QUERY-CATALOG.md)。

本機診斷不連網、逐项收集結果與白名單分享報告；company_acceptance 不因本機通過而改為通過。離線套件包綁定 requirements.lock 指紋與各 wheel SHA-256，缺失或損壞停止，無連外 fallback。雜湊保護傳輸完整性，不是組織發布簽章。

test_support 包含可重用 adapter 契約，company_templates 提供待填測試骨架，company_check 必須明確啟動且完成組織能力審查才載入可信 hooks。無 hooks 或缺項是 not_tested，不能以 demo／skip 替代組織驗收。不包括正式 AD、Oracle 或舊資料移轉。


## 個人工作流程

我的待辦與 Engine 的 tasks 分離。todos 保存標題（1～120 字）、說明（最多 50,000 字）、todo／ongoing／done、選填 YYYY-MM-DD、來源對話 ID、建立／更新／完成時間與保存防重 ID。來源不使用連動刪除；對話刪除後待辦保留，來源失效明示。狀態不觸發模型、查詢或排程，台北日期只作到期標記。

`todo_views.py` 在可用寬 900 邏輯像素以上用三欄，以下用狀態分頁。標題搜尋、顯示已完成及三欄排序沿用使用者選擇，重複刷新不重建未變卡片。常用文字卡片定義於 `work_cards.py`，只填入可修改草稿，既有草稿／附件存在時開同一助理的新對話。

`draft_views.py` 約一秒 debounce，依對話記錄文字、用途、先規劃及是否曾有附件，不保存檔案路徑或內容。Store reservation 使舊寫入失效；接受工作／Plan 後清除，刪除草稿包含於原刪除快照和同一交易。正常關閉補存，失敗須提示；Plan 修訂仍明確保存。重開舊綁定只能閱讀，不改送目標。

## 助理連線與資料轉交

`profiles.py` 管理共用 endpoint、金鑰索引、多助理名稱／ID／備註與連線版本；金鑰由 Windows keyring 保存，舊環境變數只相容讀取，不自動匯入、不明文 fallback。組織成功 API 範例未確認前，wire_mode 保持 unconfigured，不猜 ID 傳送位置。

每段對話固定 profile_id／revision；改 endpoint 或 assistant ID 使舊綁定失效，名稱／備註不換版本。切換助理另開對話，草稿及附件不自動轉交；Plan 保留目標版本，批准與派發時重驗。組織 session 若非 stateless messages，須沿 adapter 邊界擴充並驗證隔離。

查詢結果與對話選定內容先指定目的助理、預覽再確認；建立獨立新對話並記來源。最多 50,000 字，超限拒絕、不默默截斷；失敗保留來源。一般查詢排程不自動送模型；Groq 明確授權日報依上節限送合計。細節見 [助理接線](ASSISTANT-INTEGRATION.md)。

## 維護入口与完成界線

`assistant_views.py` 為管理／轉交、`conversation_views.py` 為刪除、`workspace.py` 為訊息與工作詳情；`branding.py`、`display.py`、`theme.py`、`preferences.py` 管品牌與外觀，`keyboard.py` 管送出與 IME 保護。保持此分層，不因接正式服務重做 UI。

深淺主題原地更新控制項與品牌圖示（含已開啟附屬視窗）；assets/light 保存淺色包，缺少時提示並使用深色包，桌面捷徑維持深色。不清除草稿、選取、附件、Plan 或背景工作；偏好獨立存在 ui-preferences.json，損壞用深色，保存失敗保留本次變更並提示。應用訊息框由 dialogs.py 呈現、預設焦點為取消／關閉，恢復呼叫前的模態抓取。window_chrome.py 使用 Windows 原生 DWM 顏色，不移除標題列或改寫視窗控制；不支援時保留系統樣式。檔案選擇器與啟動早期錯誤維持原生外觀。

標題列介面依 [Microsoft DWM 屬性文件](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute)，著色能力須依 Windows 版本實測；不更改全系統主題。

| 狀態 | 能力 |
|---|---|
| 本機已實作 | 四主要入口與更多工具 UI、助理管理、Plan、選項、TXT／CSV、合成查詢、轉交、排程／通知、回報、刪除、深淺與 DPI |
| 工具已準備，待服務接線 | chatbot API 契約、AD／名單與 owner 授權、Oracle 三查詢、組織資料移轉 |
| 仍待真實驗收 | 正式服務、Excel、中文 IME、組織設備倍率與跨螢幕；詳見驗證摘要 |
| 後續才做 | 中央管理／協作、遠端更新、EXE、持續 Goal、無界限多 agent 自主分工、信件／OCR、多文件與 Office 原檔編修 |

Python 3.10.4 與 29 個鎖定套件維持不變。schema 5 加入 workflows／workflow_versions／workflow_steps，沿用 conversation_actions／schedule_sources／todos／drafts，無中央同步。歷史規劃由 Git 保存，不當成目前交付能力。


## 主代理規劃與子代理協作

WorkflowService 使用 create/discuss/get/list 管需求討論；discuss 是明確的模型呼叫，questions 支援文字、單選、多選及是非，模型輸出通過格式與目錄驗證後才成為 ready 計畫。update 產生新修訂；preview 不呼叫外部；confirm 需明示資料傳送授權，交易保存不可變版本及工作，提交後才派發。已批准計畫修改以另開計畫處理，不更換正在執行的目標。

步驟限 query 或 assistant，最多六步，inputs 只能引用前面步驟。workflow_call(messages, role, binding, context) 的 context 包含 run_id、step_id；現行組織相容 adapter 為無狀態請求，組織若有 session 必須在此處映射隔離。各助理 roles、verified、read_only 及能力 revision 保存在既有 profiles metadata；不是模型自行宣告的能力。

一個工作背景執行全部步驟，不向同一工作池提交再等待子工作。各步驟輸入／輸出獨立保存。查詢原始表格留本機，只轉交 report_input 的精確合計與 metadata；資料上限超過即停止。分析／彙整回覆 text、facts；覆核多 verdict(pass/needs_attention)。facts 必須等於程式從核准來源建立的精確物件，不接受錯誤數值；自由文字仍需核對。同欄名的不同數值來源衝突時停止，需拆成不同流程。

任一步驟失敗保留成果，下游 blocked；重試明確建立新工作，只沿用連續成功前置結果，不重查已取得數據。取消停止後续派發並阻擋晚到結果。排程 query_id=WORKFLOW，parameters 的 _workflow 綁定流程版本；沿用現有 occurrence、防重、漏跑及通知，成功後才允許建立。排程失敗或能力失效暫停，人工處理後重啟；程式重新啟動不自動續接中斷工作。

workflow_views 為同頁可選取文字、步驟編輯及進度，模式依對話保存個人偏好。規劃討論不送聊天歷史或附件，使用者需明確貼入允許的文字。UI 不保管或直接派發工具。

## 0.14.0 成果與品質回饋

OutcomeService（outcomes.py）只讀既有 task／workflow_steps，提供 read、compare、feedback、save_feedback、clear_feedback；outcome_views.py 呈現成果優先頁面與背景保存回饋。不改模型派發與組織 adapter。schema 6 的 outcome_feedback 按 task_id 唯一保存 rating、note（最多2000字）、建立及更新時間；外鍵隨工作刪除。schema 1～5 先一致性備份，再交易升級。來源對話刪除保留獨立流程與回饋。

比較選此前完成且較早建立的成功工作，嚴格同流程／修訂／planner及子助理綁定／步驟與非日期條件；排程僅同 schedule_id，手動僅手動。前一日使用 catalog 日期映射忽略變動日期，固定日期全比對。各步從快照重新取得精確合計與筆數；不混來源、不比較自由文字、不送模型、不產生異常恢復判斷。截斷、空結果、來源欄位不符或無效數值明示不可比較。

成果文字保留完整原文，Instruction 使用結論／需要注意／待確認與決策標題；不依任意模型文字推定結構。覆核顯示「流程覆核通過」仍需核對來源。部分成果和成功分開，僅已結束且有文字的工作可評價。

## 登入入口與身分界線

identity_mode=company時，WebView/Tk啟動前共用login_view.py；authentication.py驗證組織函數回傳、登入期限與每subject資料目錄。company_auth.py仍是拒絕的接線stub，不含LDAP連線或假成功。Profiles/查詢/Engine/bridge檢查登入期限；App關閉清除記憶體session。舊demo模式保持既有資料與入口。--login-preview只顯示畫面，沒有驗證或工作區。

about.py讀本機publisher.json，供兩介面及登入頁顯示作者工號、姓名、電話；缺失或損壞顯示未設定。檔案不進Git，範例全空。組織AD/伺服器ACL/停權即時撤銷仍not_tested。

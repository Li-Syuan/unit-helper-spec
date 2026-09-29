# 0.18.2 外觀選擇

color_style只允許ocean/violet/forest，與theme深淺獨立存ui-preferences；缺失或損壞預設ocean。恢復預設僅重設dark/ocean，不清除其他偏好或公司連線。WebBridge appearance變更本次顏色，保存失敗須如實回報saved=false並可重試。風格只調主操作與選取，不改WARNING/RUNNING/SUCCESS/ERROR及一般未讀青藍；故紫色也可作星霧紫的操作色。切換不得重建設定表單、丟失草稿或派發。Tk同名選擇與整組原子保存保持相容。

# 0.18.1 呈現規則

WebView 的 badge／tone 只將既有狀態映射為語意色：待確認琥珀、執行藍、完成綠、失敗紅、取消中性；紫色只標團隊識別。未讀數不表示故障，使用青藍；notifications.is_read 是已讀來源，只有明確查看才標讀。Tk 同步主題，紅色驚嘆號保留給錯誤。顏色須搭配文字／圖示，不改批准、派發或成功判定；綠色不代表事實已核實。

# 0.18.0 僅核准搜尋（優先於下方禁止 pluginapi 的舊規則）

使用者已明確同意「只開核准的搜尋工具」。`search_tools.py` 的每助理 policy 保存人工核對的 function 名稱、有限 JSON schema 與說明；CompanyProbe metadata GET 產生十分鐘一次性核准 token，保存／移除皆提升連線 revision、撤銷 workflow verified。改 endpoint／assistant ID／協定清除 policy。核准不是能力實測，不能由 UI 自動標 verified。

僅已確認的 assistant_briefing 與已驗收 rag 流程步驟可送核准 tools＋auto；普通聊天、task 草稿、planner、analysis／review／compose 保持 tool_choice=none。每批先完整驗證、最多4 call／3批／600秒，固定同源 pluginapi，不接受模型 URL／headers／檔案指令。TLS、零自動重試不變。單工具回覆超128KiB停止、不截斷（目前 HTTP response 先由 SDK 完整接收，再檢查大小）。

每個 call 的 digest／結果及提交狀態存既有 JSON 帳本，未知 plugin POST／submit 不 retry；已知完成快取可以明確恢復，取消不得提交晚到結果。公司真實相容、來源、權限與多ID仍 not_tested。新核准修改在 Engine／Dialogue／Probe 鎖內檢查真實 inflight 並保存，不阻塞遠端請求時持有 bridge 全域鎖。Store schema6／dialogue CHECK=0／依賴保持。

# 0.17.0 公司試跑入口

`company_readiness.py` 本機盤點不讀取金鑰或呼叫服務。明確啟動的 CompanyProbe 只 retrieve assistant metadata，工具宣告不是實測或授權；close 等待真實請求，不持有 bridge 全域鎖。不得由連線成功自動設定 workflow verified。

`assistant_briefings.py` 以既有 tasks/schedules/occurrences 保存單助理日報，kind=assistant_briefing；schema 與依賴不變。預覽零派發、十分鐘 token、固定 request ID、連線版本綁定；試跑收到文字後，由人核對並另行同意持續傳送才建立每日台北時間排程。四角色不是單助理日報前提。每次執行獨立遠端 thread；失敗、取消或中斷暫停對應排程，真實 future 未結束不重疊執行。收到文字不代表已搜尋或事實正確。

工具仍禁止 pluginapi、保留 tool_choice=none 與 TLS；公司搜尋能力必須另行實測。主畫面兩模式 task_drafts.enabled=0 不變，不將草稿私自接入排程。

# 0.16.0 正式整合規則（優先於舊版限制）

使用者已明確批准 App 正式引入 LangGraph、SQLite checkpoint 及必要間接依賴，允許重新鎖定正式 requirements 與更新常駐 .venv。仍不得直接覆蓋為 lab lock；lab wheels 的 Git 例外僅原目錄。正式離線包在 artifacts，不提交 Git。無 LangSmith tracing／外部遙測。

graph_runner.py 接管已批准順序步驟；WorkflowService 保持唯一業務状态與批准／成果／排程契約。checkpoint 不代表 exactly-once。恢复核對 task、step、定義指紋、成果收據及 Assistants 請求帳本；未知寫入不 retry；已知 run 只 retrieve，已完成結果用快取。重開無自動派發，取消後不可復活。

公司成功範例已確認為 Threads/Messages/Runs + 自訂 pluginapi（非 Azure Chat Completions）。assistants_gateway.py 為文字專用連接器，Profiles 顯式 wire_mode=assistants，不猜 ID 是 model。tool_choice=none 需公司驗收，requires_action 停止，禁止 pluginapi；TLS 保持驗證。公司服務端副作用與角色能力尚未實測，不以設定旗標當證據。

主畫面透過 ProfileDialogueProvider 明確選擇公司或示範，無 fallback。task_drafts CHECK=0 保持；草稿建議每輪獨立遠端 thread，一般聊天沿用相同 thread。dialogue_send 不得持有 bridge 全域鎖；追蹤真实請求、取消與 close drain，原始錯誤不顯示。公司端 thread 不隨 App 退出刪除。

本機新增 assistant-sessions.sqlite3 與 workflow-checkpoints.sqlite3，皆為使用者資料，不進 Git。刪除進階對話在同一 SQLite transaction 刪除附加帳本的對應回覆快取，獨立 workflow 及遠端資料保留。跨 SQLite 檔的斷電原子性不作保證；還原必須關閉 App 並還原整個資料目錄的一致備份。


# 0.15.0 新增規則（優先於下方舊版介面限制）

`experiments/langgraph-lab` 是使用者明確要求隨 GitHub 提供 wheels 的獨立試驗包，例外僅限該目錄的 `packages/*.whl`。不得把其 lock 合併到 App、把 LangGraph 範例當正式多助理整合，或啟用公司任務。試裝使用自身暫時 .venv，完成驗證後清除；原 App requirements 與常駐 .venv 保持不變。公司試跑見該目錄 README。

使用者已允許pywebview>=6,<7、markdown-it-py>=4,<5、bleach>=6,<7、python-dotenv>=1,<2。WebView2為主介面、Tkinter保留--ui tk備用。宿主／bridge／session／render與web_assets分層，不從模型載入HTML或外部URL，禁止任意bridge方法、檔案路径或eval命令。

新主畫面無附件、一般聊天／建立任務兩模式，始終明示離線示範。dialogue_provider/company provider未完成正式契約保持停用、不fallback；dialogue_contracts嚴格驗證助理、欄位與schedule。dialogue_store獨立schema1（主Store仍schema6），task_drafts.enabled CHECK=0，不能接到原scheduler。只有dialogue_service.confirm可儲存完整且預覽未過期的草稿。切模式或助理開新thread，不永久刪歷史。既有多助理与排程保留進階入口。

真WebView視覺驗證使用scripts/web-smoke.py合成資料及mock回覆，CapturePreview只擷取App內容；GUI執行不代表人工直觀性、IME、Clipboard或公司實測通過。只在明確驗證後發布，保留失敗紀錄。

# QA agent 開發與公司接手守則

## 當前範圍

先讀 [README](README.md)、[產品與架構](docs/PROJECT.md)、[驗證紀錄](docs/VALIDATION.md) 與 [公司接手工作單](COMPANY-HANDOFF.md)。0.14.0 新增成果優先、精確數值比較、本機回饋與公司助理Instruction；沿用可收合圖示側欄、助理團隊與分工進度，沿用對話式 Plan、多助理依序協作及流程排程，延續個人待辦、工作卡片、草稿保存與深淺正式品牌圖示；歷史規格由 Git 查閱，不再作為當前開發需求。

沿用 Windows x64、Python **恰好 3.10.4**、Tkinter／ttk、SQLite、OpenAI SDK 與 Windows keyring。公司待辦為 chatbot 契約、AD／名單及 owner 授權、三項 Oracle 查詢、舊資料／排程遷移與現場驗收。不得覆蓋公司原有規則或程式。

中央管理 API、中央 schema／常駐排程、issue 後台、遠端更新、EXE、無界限自主多 agent／持續 Goal、信件、OCR、Office 原檔編輯、多文件及任意 SQL／shell 均不在目前範圍。GPT 6 sol 是開發 agent，不是預設產品模型 ID。

## 架構與安全契約

- 選用外部試用限 start-trial.bat／--groq-trial。trial.py 固定 Groq 官方端點、模型、無工具、零自動重試；只讀專案 .env 的 GROQ_API_KEY，不得把公司憑證或資料自動帶入。試用子目錄與公司工作區分離，正式入口不讀 .env。這是使用者明確選用的明文檔例外，不能擴大成公司 keyring 失敗 fallback。TLS 使用系統信任庫且強制驗證，不能為連線關閉驗證。

- UI／呈現位於 `desktop_app/ui.py`、`workspace.py`、`theme.py`；服務／Store／本機排程位於 `core.py`。保留 `gateways.py` Protocol 與 `profiles.py` 公司映射邊界，不重做整個應用。
- 公司模式失敗明確報錯，不 fallback demo；未取得成功 API 範例不得猜 endpoint、assistant ID 的傳送位置、session 或 AD／SQL 欄位。助理原生工具副作用須經公司確認，SDK 呼叫不能視為天然無副作用。
- Plan 預覽不呼叫 bot，`validate` 不查 DB；批准、修訂、期限、綁定及防重由服務層強制。選項不是工具授權，換助理／連線版本不能把舊 Plan 改送新目標。資料轉交只送明確選取、預覽及確認的內容；一般排程不自動交助理整理。例外限 Groq 試用的明確授權日報：intent_drafts.py 只解析建議，action_views.py 提供同頁編輯／授權／預覽；report_drafts.py／report_views.py 保留既有測試契約，report_engine.py 在服務層固定三項合成查詢、每日前一日、Groq 綁定及一次確認；只送精確合計等 metadata，禁止轉交逐筆資料或移植成未批准的公司排程。
- UI thread 只操作 widget，I/O 在背景；取消後晚到結果不得覆寫狀態，未完成真實 future 存在時禁止更換 client，關閉完成才釋放單例鎖。
- AD 接線必須補每次派發／排程授權及跨登入者資料隔離；目前本機 profile 並無多租戶 ACL。`local-demo` 不得冒充 AD，UI 隱藏不等於授權，停用／逾期後應拒絕操作。
- Oracle 僅核准模板、bind、可信身份注入範圍及有限唯讀結果；不要把共享 DB 密碼放桌面或模型。依 [查詢契約](docs/QUERY-CATALOG.md) 宣告動態欄位／日期映射，未宣告映射不能使用前一日排程。精度不用 float，不覆寫原文／原檔，Excel 公式防護與實際貼上分別驗證。
- 金鑰存 Windows 認證管理員，設定只存索引；舊環境變數相容讀取，不自動搬移或刪除。禁止明文 fallback、`keyrings.alt`、停用 TLS 驗證；不記 HTTP body、密碼或原始敏感錯誤。
- `.venv*`、`.runtime`、本機 config、`.env`、SQLite、使用者資料、`company_local`、`artifacts` 不進 Git。分享診斷只輸出白名單安全欄位。
- 新 SQLite 與公司舊 DB 分離。移轉先一致性備份、唯讀盤點、dry-run、防重與回復；舊 runner 未停用且未確認無執行中工作前，不啟用對應新排程。

## UI 與資料維護

- 0.13.0：`navigation.py` 管圖示側欄收合與 tooltip，偏好存 ui-preferences；切換保留頁面／草稿。`team_views.py` 沿用 Profiles 管理，UI 不得自行標記 verified。`workflow_presenter.py` 只呈現 snapshot，不另存工作狀態。「確認執行」是使用者明確授權當下可見修訂；不要恢復額外 checkbox 或逐步批准，也不要改成送出需求就自動授權。排程持續授權保持獨立。

- 0.12.1 通知 UI 位於 `notifications.py`：只讀既有通知與工作狀態，不派發工作。關閉／逾時不標已讀、啟動不重播舊通知；僅明確查看單則才標讀。彈窗不搶焦點或使用 grab，關閉 App 清除 timer。未讀徽章是側欄按鈕的 sibling overlay，避免 Windows 原生按鈕遮蔽子元件；保留實際畫面檢查。

- 品牌固定 **QA agent**，正式 A 深淺圖示與各倍率圖示隨專案提供；assets 根目錄為深色及固定捷徑，assets/light 為淺色，切換須更新已開啟附屬視窗；Tk 視窗使用多尺寸 PNG iconphoto，ICO 僅供捷徑，勿恢復每次切換的 iconbitmap 載入（會累積 Windows 圖形資源），不在 runtime 下載素材。名稱集中 `branding.py`；不得因更名改資料路徑／環境變數。捷徑只更新本工具建立的項目。
- System DPI awareness 及 AppUserModelID 在 Tk 建立前設定，保留較高既有模式。沿用 `display.py`：固定尺寸按倍率換算，點數字型不再縮放；不宣稱跨螢幕即時 DPI 重排已完成。
- 主題、頁面提示及介面刷新保留草稿、附件、游標、選取、捲動、Plan 修訂與工作。訊息是可選取的純文字，不執行模型 HTML；任務狀態來自選定的 task／plan，不捏造百分比或重送。
- 操作提示位於原頁面，只讀狀態，不填稿或派發；收合不得遮蔽必要警告。`page_hints` 與外觀存 `ui-preferences.json`；舊 `onboarding` 保留原值但不啟用。無獨立體驗資料庫，正常示範操作存目前個人歷史。
- `experience.py` 提供離線手冊／關於／診斷；[使用手冊](docs/USER-GUIDE.md) 章節標題是 UI 入口契約，包括「管理對話」。修改章節須同步檢查入口。
- 永久刪除使用 10 分鐘一次性預覽 token、完整資料快照、Engine 鎖及單一交易；queued/running/executing 或未結束真實 future（含已取消）拒絕整批。不自動取消或擴大刪除，未批准 Plan 可刪但不得派發。
- 刪除保留獨立查詢／排程、回報／表單、原檔／匯出／備份、公司端及其他轉交副本；異常跨資料關聯拒絕。清除對應草稿與過期詳情／轉交預覽，保留其他對話草稿；不宣稱安全抹除。

## 對話操作

conversation_actions.py 為 ActionService 與 schema 4；action_views.py 呈現卡片／時間線／活動；intent_drafts.py 僅 Groq 試用能力開關允許結構化建議。不要改成所有公司助理自動解析，更不能把公司資料送 Groq。預覽純驗證，確認檢查修訂、10 分鐘期限、綁定及持續傳送授權；工作／排程與來源連結交易提交，固定 request ID 防重。

conversation_actions 與 messages 分開；查詢、排程 task 保持獨立，不為畫面便利填入 conversation_id。schedule_sources 保留可失效來源；刪除對話清連結但保留獨立資料。解析未結束、取消後真實 future 未完成須阻擋刪除，舊解析結果必須驗修訂，不能復活已刪來源。新 schema 向舊版降版需先回復一致性備份，不直接降低 user_version。

主要四入口與更多工具皆保留功能；首次合成查詢三次操作完成，不要求看手冊或先接 API。自動預覽不意味自動批准，模型文字不是執行授權；時間線更新保留 Text 選取與閱讀位置。

## 個人待辦與草稿

`local_work.py` 為本機 CRUD 與草稿版本防重；`todo_views.py`／`draft_views.py` 為介面，`work_cards.py` 是公司可調整的文字入口。待辦狀態由人確認，不得觸發模型、排程或標記 AI 工作成功；來源只是可失效的連結，刪除對話保留另存待辦副本。

Store 升級至 schema 6，schema 1／2／3／4／5 先以 SQLite backup 備份，再同交易遷移；不要直接降低 user_version。草稿按對話保存，背景寫入須檢查 reservation，送出清除／刪除後晚到結果不得復活；Plan 修改不當普通草稿。對話刪除快照和交易包含草稿。附件不跨啟動讀取，重開提示重新選取。

## 驗證與交付

環境、離線安裝與診斷操作見 [開發指南](docs/DEVELOPMENT.md)。正式測試使用專案 Python 3.10.4；`scripts/test.ps1` 預設 quick，僅非 GUI 核心離線測試。`-Suite targeted -Tests tests.test_appearance` 可選多個模組或案例；`-Suite full` 才執行完整回歸及 doctor／pip check／lock 檢查。改依賴須更新鎖檔並在第二乾淨環境及離線來源重建，不借外部 site-packages。離線包缺件／雜湊／lock 不符必須停止，不連外補件。

測試按變更風險選取：文字／配色只跑受影響測試與畫面，功能修改加 quick；核心服務、遷移、依賴或發布跑 full。交付需正式證據時，只跑 `scripts/verify.py development` 一次，它使用同一 full 執行器，不先跑 test full 再重跑 verify。WebView smoke 只在相關 UI／bridge 變更或介面發布驗收時跑；純文件修改只檢查引用。通過後沒有新修改、失敗或未解疑慮，不重複驗證。

`scripts/test_runner.py` 共用執行與計時，`tests/suites.json` 按 TestCase class 明確分類；新增模組／class 未分類即失敗。新增測試需保護具體行為或已發現問題，不以測試數增加為交付條件；重複覆蓋可合併，但批准、防重、取消、隔離、工具授權、遷移及刪除保障必須保留。GUI 串行且案例資料獨立；空集合、載入錯誤、失敗或非預期 skip 不算通過。日常報告覆寫 `artifacts/testing/latest.json`，明示範圍與耗時；quick／targeted 通過不能宣稱 full 通過。正式交付才更新驗證摘要，不累積逐版測試材料。

常駐環境只保留 `.venv`。另建的驗證環境完成後保留實測紀錄，確認程序已結束、解析路徑位於專案內且無連結跳轉，再清除該次建立的環境；不要累積版本備份。刪除前讀取 `.venv/pyvenv.cfg`，保留它依賴的基礎直譯器（此機為 `.runtime/python3104`）。

[串接測試工具包](docs/ADAPTER-TEST-KIT.md) 提供合成斷言與公司 hooks；公司測試預設 `not_tested`，明確執行且能力審查完成才載入可信本地 hook。hook 必須真的斷言公司結果，不能以 canned True、skip 或 demo 假通過。

結果分列 `mock_passed`、`local_real_passed`、`company_real_passed`、`not_tested`。GUI 字串／倍率模擬不等於人工 GUI、Excel、IME 或真實 Windows 倍率驗收。調整 UI 後檢查一般、小工作區及最大化的操作可達性。完成後更新 `docs/PROJECT.md`、`docs/VALIDATION.md`、公司工作單及 manifest；不得捏造測試證據。

開發優先固定腳本與直接參數；捷徑測試保留 `tests/helpers/shortcut-fixture.ps1` 的 `-File` 流程，不恢復 EncodedCommand、動態 shell 字串或政策繞過。不要關防毒／加排除；警告出現時記錄操作、程式路徑及警示 ID，獨立確認成效，不用測試通過代替防毒驗證。

## 開發分工

允許 Coordinator 委派 Desktop、Adapters（既有 Backend 識別）與 QA，**含 Coordinator 自己的執行工作，最多兩個工作包同時進行**。每包指定可寫路徑、契約、輸入、依賴與驗收；根設定、鎖檔、遷移與整合由 Coordinator 管。子 agent 不另委派；沒工具就順序做，不以角色文字冒充並行。沿用使用者指定模型，不猜公司模型 ID。保留 `.github/agents` 的既有角色識別。

## 0.11.1 視窗與訊息框

應用 showerror／showwarning／showinfo／askyesno 集中 dialogs.py，保留同步結果語意、取消預設焦點及巢狀grab恢復。不把提示關閉當成重試或批准。theme.Appearance 同步更新既有與後開視窗；window_chrome.py 只呼叫原生DWM著色，失敗不影響功能、不以無框視窗替代。檔案選擇器及外觀尚未建立的啟動錯誤才沿用系統。


## 對話式 Plan 與多助理協作

workflows.py 為 WorkflowService，workflow_views.py 為同頁呈現。新「規劃工作」會明示呼叫已驗證 planner 討論需求，與既有零模型呼叫的本機 Plan 預覽分開。規劃輸出是建議，最多六個無循環的依序步驟；規劃期間不能查詢／派發子代理／建排程。preview 純驗證、十分鐘確認、版本綁定與 request ID 由服務層檢查。

schema 5 新增 workflows／workflow_versions／workflow_steps；tasks(kind=workflow) 保存每次真實執行，既有 occurrences／schedules 負責排程，不另建狀態來源。刪對話清未批准草稿與來源連結，已批准流程、工作及排程保留；規劃及執行的真實 future 結束前不能刪除。取消／關閉後晚到回覆不得寫回，失敗不自動重試。

Profiles.workflow_catalog／workflow_binding／validate_workflow／workflow_call 為公司協作邊界。只有經實測的唯讀文字／RAG能力可由公司 hook 使用 set_workflow_capability 啟用；UI 只能保存未驗證角色。不得把填 evidence 或 verified=True 本身當成真實驗收。assistant ID／endpoint 改變會撤銷能力驗證。公司有 session 時依 run_id＋step_id＋助理版本隔離；未知公司格式禁止猜測或 Groq fallback。

子代理只收已批准的指定來源。查詢向下游只送程式合計及 metadata，原始表格本機保留；精確 facts 與來源不符即失敗，但不能宣稱已驗證自由文字全部正確。覆核 needs_attention 停止後續。成功流程才能建立持續授權排程；重用固定版本，App 須開啟。失敗、失效綁定、關閉時未完成流程會暫停相關排程。無自動重規劃、無自動 retry、無生圖或 shell。

Groq 試用使用同模型的 planner／analysis／review／compose 四個隔離角色。scripts/check-workflows.py --live 才啟動最多四次合成請求，僅暫存資料，不動使用者排程。驗證入口：tests.test_workflows、tests.test_workflow_profiles、tests.test_workflow_ui；真公司多ID與使用性另驗收。

## 0.14.0 成果契約

當前版本0.14.0/schema6，outcomes.py 只讀快照及保存本機品質回饋；outcome_views.py 成果優先，背景寫回饋不派發工作。compare 嚴格同流程修訂／綁定／排程／非日期條件，前一日僅忽略宣告日期映射；Decimal 保留精度，空資料不推零，數值差異不代表異常。歷史 schema 1～5 升級前備份且交易遷移。docs/assistant-instructions 四角色指示沿用 JSON 契約，不能因 prompt 而跳過公司能力驗收或宣稱零幻覺。

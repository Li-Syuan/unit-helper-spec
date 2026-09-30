# 0.18.0 官方契約與核准搜尋接線

查證日期：2026-09-29。使用者已批准僅核准搜尋；下列往返已實作並以合成 HTTP 驗證，公開文件與本機測試不代表組織部署已實測。

| 官方來源 | 已確認內容 |
|---|---|
| [官方網站文件入口](https://dvcbot.net/docs) | 平台區分助理、插件與 DSE 文件檢索 |
| [Assistant API](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/200671332/MediaTek+Assistant+API) | 提供 Python 範例、Threads/Messages/Runs，以及 requires_action 後呼叫 pluginapi 並提交工具結果 |
| [Plugin Chat](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/3309569/Plugin+Chat) | Internet Search 是預設插件；插件也可能具備程式執行等其他能力，不能把所有插件都當搜尋 |
| [智能檢索 SE](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/173408275/Search+Engine+SE) | 上傳文件轉為檢索插件，由助理使用；與網際網路新聞搜尋不同 |
| [任務管理](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/223084553/Task+Management) | 描述代使用者與指定同仁討論的分身型任務；此頁不能證明循環排程能力 |

官方 API 範例確認：POST 到同一 Assistants base URL 的 `/pluginapi`，query parameters 為 tid=thread ID、aid=assistant ID、pid=回傳的 function.name；JSON body 取自 function.arguments。回覆文字與 tool_call_id 配對，交回同一 run 的 submit_tool_outputs，再輪詢。組織自行部署需使用組織的 base URL。這個通用傳輸契約已有依據，不再要求使用者重新提供整套 API 規格。

尚未由公開頁面確認的是組織搜尋插件實際 function 識別、參數定義、權限及版本相容性；顯示名稱 Internet Search 不可直接猜成 function.name。可先由已配置助理的 metadata／組織插件設定核對，僅在不支援讀取時再取去識別化樣本。metadata 是宣告，非唯讀性或能力驗收證明。

## 已實作的核准範圍

已配置 Internet Search 的AI 助理可走「核准工具 → 搜尋試跑 → 查看來源 → 另行確認每日執行」，也可使用既有 rag 角色加入批准後的多助理流程。預設仍沒有核准工具；不開放任意插件。

1. **組織搜尋設定**：沿用 endpoint／key／Assistant ID，新增管理者核准的搜尋工具識別與參數契約，綁定該助理及連線版本。從官方 metadata 讀取候選設定後仍須核對實際用途；普通使用者不編寫程式，未核准助理保持工具停用。
2. **派發範圍**：planner 的需求討論與草稿建議保持 tool_choice=none。只有明確預覽／確認過的搜尋試跑或流程搜尋步驟可使用該策略；分析、覆核、彙整不因此自動取得工具能力。新搜尋步驟可沿用既有 rag 角色及 JSON 契約，不另加隱藏主代理。
3. **Gateway 處理**：在 assistants_gateway.py 的 requires_action 分支驗證同一 thread/run、call ID、function 白名單與參數型別。先驗完整批次，再 POST 組織固定 pluginapi；不接受模型指定 endpoint、headers 或本機檔案路徑。不符合核准策略即停止，不執行其他插件。
4. **有限執行**：每輪最多4個工具呼叫、每run最多3輪，工作總期限最多600秒及原單次timeout；回覆最多128KiB，超限明示失敗，不靜默截斷。SDK目前先完整接收HTTP回覆再檢查大小，非串流記憶體上限。TLS及零自動重試保持。
5. **收據與恢復**：assistant_sessions.py 請求記錄增加每個call的識別、參數雜湊、策略指紋、傳送前狀態及已取得結果。工具送出／工具結果提交前先記錄；結果不明時停止。已取得结果使用快取、不重搜；只在遠端run與工具批次完全一致時允許明確恢復，不宣稱 exactly-once。取消後不提交晚到結果，不復活已取消任務。
6. **試跑與呈現**：財經日報試跑顯示實際工具呼叫狀態及完整成果，不因HTTP200／有文字就標搜尋已驗證。人核對日期／來源後才另外啟用08:00台北排程。主代理仍為planner；多助理接入沿用一次確認、來源限制、覆核停止與固定版本排程。

驗證需包含官方形狀的合成往返、兩輪工具、多call配對、未知工具／錯誤參數整批零派發、逾時與未知結果不重送、取消晚到、改助理或策略使舊批准失效，以及主代理規劃期間零工具派發。再於組織完成真實搜尋、多輪、排程及多助理成果核對，才能記 company_real_passed。合成通過不自動寫 verified。

修改入口：search_tools.py（有限schema／policy）、assistants_gateway.py（工具往返）、profiles.py（修訂與rag路由）、company_readiness.py（metadata一次性token）、assistant_briefings.py（預覽與收據）、web_bridge.py／app.js（核准UI）。主Store schema6、dialogue task_drafts.enabled=0 與依賴保持；工具記錄放現有 JSON 帳本，舊文字請求相容預設無工具。

支援 schema：object／string／integer／number／boolean／array、properties／required／additionalProperties=false、items、enum、數值上下限、字串／陣列長度，以及有上限的 description／title。最多6層、每物件32欄，字串最多4000字、陣列64項、參數JSON32KiB；未知條件（含 $ref、pattern、anyOf、default）拒絕，不忽略限制。省略 additionalProperties 會明確收緊為false；metadata畫面呈現的是核准後定義。組織若用不同schema，請提供去識別化定義，擴充驗證及反例後再啟用，不把驗證移除。

metadata／核准不執行工具，也不等於多助理能力驗收。核准token10分鐘、一次使用；變更策略提升profile revision並撤銷角色verified。更換endpoint、ID或協定清除核准。正在執行或取消尚未收尾時不能修改。已取得工具結果可在原batch明確恢復時用快取；未知plugin POST／submit永不自動重送。

# Assistants 模式

組織已提供 Threads／Messages／Runs 範例。設定頁 wire_mode 選 assistants，輸入共用 endpoint／API key，助理團隊管理各 Assistant ID。每段對話綁定版本；改 endpoint、ID、協定會使旧綁定失效並撤銷協作能力驗證。

傳輸在 assistants_gateway.py、隔離與請求收據在 assistant_sessions.py、路由仍在 Profiles。respond 的可選 context 支援 conversation_id／request_id；workflow_call 以 run_id／step_id 隔離。已完成收據回傳快取，已知未完成 run 必須明確 resume，結果不明不重送。

普通聊天與規劃使用 tool_choice=none；僅上述核准日報／rag步驟傳入受限tools與auto。CA 使用本機 config.json 的 assistant.ca_bundle；不關閉 TLS。組織測試仍須確認平台遵守tools限制、服務端是否有其他原生副作用及session保留政策。

來源為使用者提供的組織去金鑰範例；Git 不保存內部 endpoint。沒有正式 API server，scripts/mock-assistants.py 只供 loopback 合成協定測試。


# 組織多助理接線

## 現有行為

使用者在設定中輸入共用 endpoint、保存 API key，新增助理名稱／assistant ID／備註。metadata 位於使用者資料目錄 assistants.json；金鑰僅在 Windows 認證管理員 QAagent.Desktop.API。assistants.json 不提交 Git，也不是授權名單。

每段對話保存 profile_id／revision。改 ID 或 endpoint 使現有 binding 失效，舊版本資料保存在本機 history 供辨識；名稱／備註改動不影響連線版本。切換助理另開對話，不傳舊歷史；Plan 固定 binding，批准前／派發前皆驗證。keyring 讀取失敗直接失敗，不用示範補答案。

## 組織需提供

1. 已提供的 Threads/Runs 範例與組織實際成功版本有無差異；樣本遮蔽 endpoint、ID 及 key。
2. 核准的 SDK base URL；本版 Assistant ID 透過 runs.create 的 assistant_id 傳送，不當 model。
3. 回覆文字位置、session／thread 的建立與續用規則、是否需要額外 headers／CA。
4. 助理原生工具可能產生的副作用，及允許用於測試的專用助理。
5. 對照人工的請求與回覆案例，包含認證失敗、逾時、空回覆與不同對話。

不要把秘密填入 repo、手冊、截圖或組織測試輸出。

## 修改與驗收

- profiles.py 的 respond 是多助理連接入口；gateways.py CompanyAssistant 保留現有 Chat Completions 相容實作。
- 新 metadata 的 wire_mode 預設 unconfigured，必須有成功範例才修改。若 ID 明確放 model，設定 wire_mode=model；若放 body 欄位，設定 wire_mode=body_field、assistant_field 為組織欄位名、model 為組織指定值。這些是維護者設定，不要求一般使用者理解。
- 如果實際 API 不是上述格式，修改 adapter，不以猜測參數讓 request 勉強通過；不要切到公共 OpenAI 端點。正常組織錯誤不得回退 demo。
- 舊 config 的 model／assistant_ref 接線可沿用；新助理不自動套用它。組織 session 必須按使用者、助理版本及對話隔離；舊 Chat Completions 映射使用 stateless messages；Assistants 模式已提供持久化 thread 與隔離測試，仍需組織真實驗收。
- 維護者確認測試助理不會執行副作用後，才配置既有 verified_side_effect_free；測試連線按鈕讀取這個 gate。它不等於資料庫／工具授權。
- Oracle 仍由核准查詢工具處理，結果經選列／預覽後才交助理。一般查詢排程不自動呼叫助理；新協作排程須經成功試跑與持續傳送授權。
- 升級至 schema 5（由 schema 1／2／3／4）之前產生 SQLite backup API 備份；舊對話 binding 為 NULL，保留只讀。不要猜舊訊息的助理歸屬。需回復時關閉新程式，由維護者使用備份與舊版配套恢復，不直接降低 user_version。

基準命令：

~~~powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profiles tests.test_assistant_ui tests.test_experience tests.test_keyboard -v
.\.venv\Scripts\python.exe scripts/verify.py development
~~~

組織實測仍按 [接手工作單](../COMPANY-HANDOFF.md) 和 [測試契約](ADAPTER-TEST-KIT.md) 明確啟動；先完成 mock 契約，再用組織測試助理執行。完成條件是對話隔離、正確助理 ID、資料送出範圍與失敗狀態皆與組織人工結果一致。未拿到範例前保持 not_tested。


## 協作 adapter 契約

組織沿用 `workflow_call(messages, role, binding, context)`，role 為 planner／analysis／review／compose／rag，binding 包含 profile_id、連線 revision、capability_revision；context 包含 run_id、step_id。無狀態 API 可沿用現有 respond；有 session 的平台需依上述識別及助理版本建立獨立上下文，不能挪用個人聊天 session。重試有新的 run_id。

规划 role 回傳 JSON：message、questions、steps。問題支援 text/single/multi/boolean；有問題時 steps 為空。步驟為目錄內 query 或 assistant，inputs 引用前置步驟 ID。分析／彙整／RAG 回傳 JSON：text、facts；覆核另含 verdict=pass 或 needs_attention。facts 的精確預期物件隨每步輸入提供，不推測或轉浮點。回覆格式不符、錯誤數值及未核准工具要求都應失敗，不截斷、不替換成示範答案。搜尋所得行情等數字寫在 text 並附來源，不新增到程式 facts。

RAG 來源按平台實際格式映射至回覆文字，不能猜引用；assistant metadata verified/read_only 需組織核准測試支持。UI 只可保存角色、會撤銷驗證；啟用由可信組織 hook 完成並記錄本機證據識別。名稱／備註修改不影響連線，ID／endpoint 改變會撤銷能力驗證；流程固定版本，不能暗換目標。參見 [組織工作單](../COMPANY-HANDOFF.md#多助理協作接手工作)。

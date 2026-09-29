# 0.16.0 Assistants 模式

公司已提供 Threads／Messages／Runs 範例。設定頁 wire_mode 選 assistants，輸入共用 endpoint／API key，助理團隊管理各 Assistant ID。每段對話綁定版本；改 endpoint、ID、協定會使旧綁定失效並撤銷協作能力驗證。

傳輸在 assistants_gateway.py、隔離與請求收據在 assistant_sessions.py、路由仍在 Profiles。respond 的可選 context 支援 conversation_id／request_id；workflow_call 以 run_id／step_id 隔離。已完成收據回傳快取，已知未完成 run 必須明確 resume，結果不明不重送。

本版使用 tool_choice=none，requires_action 停止，不呼叫 pluginapi。CA 使用本機 config.json 的 assistant.ca_bundle；不關閉 TLS。公司測試仍須確認此限制被平台接受、伺服器是否有原生工具及 session 保留政策。

來源為使用者提供的公司去金鑰範例；Git 不保存內部 endpoint。沒有正式 API server，scripts/mock-assistants.py 只供 loopback 合成協定測試。


# 公司多助理接線

## 現有行為

使用者在設定中輸入共用 endpoint、保存 API key，新增助理名稱／assistant ID／備註。metadata 位於使用者資料目錄 assistants.json；金鑰僅在 Windows 認證管理員 QAagent.Desktop.API。assistants.json 不提交 Git，也不是授權名單。

每段對話保存 profile_id／revision。改 ID 或 endpoint 使現有 binding 失效，舊版本資料保存在本機 history 供辨識；名稱／備註改動不影響連線版本。切換助理另開對話，不傳舊歷史；Plan 固定 binding，批准前／派發前皆驗證。keyring 讀取失敗直接失敗，不用示範補答案。

## 公司需提供

1. 已提供的 Threads/Runs 範例與公司實際成功版本有無差異；樣本遮蔽 endpoint、ID 及 key。
2. 核准的 SDK base URL；本版 Assistant ID 透過 runs.create 的 assistant_id 傳送，不當 model。
3. 回覆文字位置、session／thread 的建立與續用規則、是否需要額外 headers／CA。
4. 助理原生工具可能產生的副作用，及允許用於測試的專用助理。
5. 對照人工的請求與回覆案例，包含認證失敗、逾時、空回覆與不同對話。

不要把秘密填入 repo、手冊、截圖或公司測試輸出。

## 修改與驗收

- profiles.py 的 respond 是多助理連接入口；gateways.py CompanyAssistant 保留現有 Chat Completions 相容實作。
- 新 metadata 的 wire_mode 預設 unconfigured，必須有成功範例才修改。若 ID 明確放 model，設定 wire_mode=model；若放 body 欄位，設定 wire_mode=body_field、assistant_field 為公司欄位名、model 為公司指定值。這些是維護者設定，不要求一般使用者理解。
- 如果實際 API 不是上述格式，修改 adapter，不以猜測參數讓 request 勉強通過；不要切到公共 OpenAI 端點。正常公司錯誤不得回退 demo。
- 舊 config 的 model／assistant_ref 接線可沿用；新助理不自動套用它。公司 session 必須按使用者、助理版本及對話隔離；舊 Chat Completions 映射使用 stateless messages；Assistants 模式已提供持久化 thread 與隔離測試，仍需公司真實驗收。
- 維護者確認測試助理不會執行副作用後，才配置既有 verified_side_effect_free；測試連線按鈕讀取這個 gate。它不等於資料庫／工具授權。
- Oracle 仍由核准查詢工具處理，結果經選列／預覽後才交助理。一般查詢排程不自動呼叫助理；新協作排程須經成功試跑與持續傳送授權。
- 升級至 schema 5（由 schema 1／2／3／4）之前產生 SQLite backup API 備份；舊對話 binding 為 NULL，保留只讀。不要猜舊訊息的助理歸屬。需回復時關閉新程式，由維護者使用備份與舊版配套恢復，不直接降低 user_version。

基準命令：

~~~powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profiles tests.test_assistant_ui tests.test_experience tests.test_keyboard -v
.\.venv\Scripts\python.exe scripts/verify.py development
~~~

公司實測仍按 [接手工作單](../COMPANY-HANDOFF.md) 和 [測試契約](ADAPTER-TEST-KIT.md) 明確啟動；先完成 mock 契約，再用公司測試助理執行。完成條件是對話隔離、正確助理 ID、資料送出範圍與失敗狀態皆與公司人工結果一致。未拿到範例前保持 not_tested。


## 協作 adapter 契約

公司沿用 `workflow_call(messages, role, binding, context)`，role 為 planner／analysis／review／compose／rag，binding 包含 profile_id、連線 revision、capability_revision；context 包含 run_id、step_id。無狀態 API 可沿用現有 respond；有 session 的平台需依上述識別及助理版本建立獨立上下文，不能挪用個人聊天 session。重試有新的 run_id。

规划 role 回傳 JSON：message、questions、steps。問題支援 text/single/multi/boolean；有問題時 steps 為空。步驟為目錄內 query 或 assistant，inputs 引用前置步驟 ID。分析／彙整／RAG 回傳 JSON：text、facts；覆核另含 verdict=pass 或 needs_attention。facts 的精確預期物件隨每步輸入提供，不推測或轉浮點。回覆格式不符、錯誤數值及工具要求都應失敗，不截斷、不替換成示範答案。

RAG 來源按平台實際格式映射至回覆文字，不能猜引用；assistant metadata verified/read_only 需公司核准測試支持。UI 只可保存角色、會撤銷驗證；啟用由可信公司 hook 完成並記錄本機證據識別。名稱／備註修改不影響連線，ID／endpoint 改變會撤銷能力驗證；流程固定版本，不能暗換目標。參見 [公司工作單](../COMPANY-HANDOFF.md#多助理協作接手工作)。

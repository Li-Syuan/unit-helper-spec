# 給公司 GPT 6 sol：0.17.0 接手指令

請先讀根目錄 AGENTS.md、COMPANY-HANDOFF.md 與本文件。保留公司現有能成功呼叫的程式與設定，不重寫 UI，也不要把 Assistant ID 當 model。

## 明天先完成一份可核對的財經日報

使用者已回報：公司 UI 能搜尋，過去本機 App 亦曾排程呼叫並取得回報。請優先比對那份成功程式，不重寫現有成功接線。新入口已完成「選現有助理 → 預覽 → 試跑 → 核對 → 啟用每日08:00」，不要求先建立四個角色。

1. 重建既有 lock 環境，保留公司 checkout 修改。設定 assistants 協定、endpoint、API key 及現有搜尋助理 ID；需要 CA 時使用核准憑證，不關 TLS。
2. 「設定／公司啟用檢查」先看本機缺項。這不讀金鑰或連線。「檢查搜尋助理連線」是明確的 assistant metadata GET；取得工具名稱不等於工具能力已測過。如公司不支援此 GET，記錄相容性問題，不把它等同所有聊天皆不可用。
3. 主對話按「財經日報」，確認台股、美股、重大總經及08:00。預覽零派發，按「現在試跑」才送出一次；看實際日期、來源連結及內容，不以 HTTP200 或 succeeded 當搜尋驗收。
4. 若成功：人工核對後才勾選每日傳送並啟用。啟用不多跑一次，另測「現在測試一次」、暫停、重開及歷史；App 開啟才執行。每次應是獨立遠端 thread。
5. 若失敗：先分清憑證／協定、工具派發、輸出格式；一次只修該邊界。不得為了過關同時重寫 UI、換模型、跳過驗證或改成示範。成果不合格不啟用排程。

日報修改入口：`desktop_app/assistant_briefings.py`；metadata 與公司呼叫：`assistants_gateway.py`、`profiles.py`；介面：`web_assets/app.js`。既有 task_drafts 永遠未啟用，與此明確批准的獨立日報入口不同。

### Internet Search 已放在助理內，仍需核對呼叫方式

不必重建搜尋引擎。助理配置 Internet Search 可能由服務端自行完成，也可能回 `requires_action`，要求呼叫端把指定 function 送到公司 `/pluginapi` 再回填結果。使用者提供的成功範例包含後者，但該搜尋助理實際走哪條路仍待公司實測。

本版明確傳 `tool_choice=none`、不呼叫 pluginapi，可能抑制已配置搜尋。不得宣称本版只換參數就能搜尋；也不得直接移除限制並允許所有模型指定 function。

**2026-09-29 官方查證更新：**[Assistant API 手冊](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/200671332/MediaTek+Assistant+API) 已公開上述 pluginapi 往返範例；[Plugin Chat 手冊](https://dvcbot.atlassian.net/wiki/spaces/DW/pages/3309569/Plugin+Chat) 確認 Internet Search 為插件。通用接線格式已有官方依據，請直接沿用，不再把重新取得整套 API 規格當作開發前置阻礙。公司只需核對特定搜尋工具識別、參數／權限及部署差異。完整來源與尚未啟用的修改範圍見 [搜尋接線草案](ASSISTANT-INTEGRATION.md#待批准的具體修改範圍)。

需要公司保存的本地資訊：搜尋工具名稱、參數 schema、成功回覆形狀／大小、是否唯讀、是否有費用或其他副作用，以及 run 狀態變化。不要把金鑰或內部原始回覆提交 Git。核對後另做限定搜尋工具的 adapter：固定公司 endpoint、白名單 function、嚴格 arguments 驗證、有限輪數／時間／回覆大小、取消與未知写入停止；其他工具拒絕。需公司明確核准與真實測試才改現行工具限制，不能以 metadata 或 checkbox 作驗收。

### 多代理第一題：固定資料晨報

**四個角色包含主代理：planner 是主代理，analysis／review／compose 是三位子代理。** 主代理提問與規劃；確認後由 App／LangGraph 執行核准步驟，沒有持續自主擴張任務的第五位隱藏代理。四份 [Instruction](assistant-instructions/README.md) 建立及公司能力驗收後，在「規劃工作」貼入以下內容。若先用隔離 Groq 試用，只貼這些合成資料；那是同模型四個角色，不算公司多 ID 已通過。

```text
請規劃一次「合成財經晨報」多代理測試，先不要建立排程，也不要上網。
只能使用以下虛構來源：
A：台股觀察指標本期100、前期99；只提供兩期。
B：美股觀察指標本期200，沒有前期數據。
C：某項政策聲明預計明日公布，目前沒有公布結果。

由分析助理整理已知事實與未知資訊；
由覆核助理同時核對原始A/B/C與分析，發現重要矛盾就停止；
最後由彙整助理產出「結論／需要注意／待確認與決策」。
不得編造漲跌原因、連續趨勢、政策結果、新聞網址或投資建議。
各步需要的原始來源必須列入核准輸入／步驟說明，不能只拿前一位的結論當證據。
先給我分工預覽，等我確認才執行。
```

預期：確認前沒有子代理執行；確認後分析→覆核→彙整各有真實紀錄。A 可比較這兩期；B 不能聲稱上漲／下跌；C 不能聲稱政策已公布；全文必須說明是合成資料。可直接查看每位的輸入與輸出，不能只看最終文案。程式 facts 檢查不保證自由文字正確，仍須人工核對。不要手動偽造 verified 來繞過角色測試。

再用既有 Instruction 案例 C（原始12.50、分析文字125.00）於公司測試 hook 驗證覆核停止、後續彙整零派發；正常任務成功不能代替這個負向驗收。

真實財經版本可擴為「主代理 → 既有搜尋助理 → 分析 → 覆核 → 彙整」。搜尋結果需保留來源及日期並交覆核，不能讓分析自行補新聞。這是搜尋接線後的目標流程；目前沒有已驗證的獨立搜尋角色／pluginapi 節點，不能將上述合成通過寫成五助理上網已完成。

## 已完成

- 真正 LangGraph 順序分工及 SQLite checkpoint；一次確認、覆核停止、成果與回饋沿用原服務。
- OpenAI SDK Threads/Messages/Runs 公司連接器、多助理綁定、多輪記憶、取消及未知結果防重。
- WebView 主畫面可選公司助理；建立任務仍只保存未啟用草稿。Tkinter 可作備用。
- 公司協定模擬服務、SDK MockTransport、graph 恢復測試與合成端到端旅程。

以上是本機實作；公司 API／CA／assistant ID／服務端工具均尚未 company_real_passed。

## 順序工作單

| 工作 | 公司需提供 | 修改入口 | 驗收 |
|---|---|---|---|
| 環境基準 | Python 3.10.4 x64、WebView2、可信 CA | scripts/setup.ps1、requirements.lock | pip check 與完整回歸；先記錄現有環境限制 |
| 單助理聊天 | 核准 endpoint、API key、測試 ID、API 相容差異 | assistants_gateway.py、Profiles | 真實單輪／多輪、不同對話隔離、認證／逾時錯誤；不 fallback |
| 能力驗收 | 助理的伺服器工具、唯讀能力、結構化輸出 | 公司本地 hook、profiles.set_workflow_capability | 證據合格才啟用 planner／analysis／review／compose |
| 多 ID 試跑 | 四個角色 ID；可同模型，不推測模型名稱 | 我的助理團隊、docs/assistant-instructions | 規劃只提建議，確認前零子助理；一次確認後依序完成 |
| 中斷與恢復 | 可核對的測試 run | WorkflowService、AssistantsGateway | 已知 run 不重建，結果不明停止；取消後不復活 |
| 工具與排程（後續） | 核准插件名稱、參數、回覆、唯讀範圍及人工基準 | 新工具 adapter，另提修改計畫 | pluginapi 本版不執行；先工具實測，再明確啟用持續授權排程 |

## 本機命令

```powershell
.\scripts\test.ps1
.venv\Scripts\python.exe -m unittest tests.test_assistants_gateway tests.test_assistants_profiles tests.test_company_journey tests.test_graph_runner tests.test_dialogue_concurrency -v
.venv\Scripts\python.exe scripts/mock-assistants.py
```

mock server 僅提供本機協定測試，不直接作公司 App HTTP endpoint；正式連接器保持 HTTPS。公司網址與真實樣本只存忽略的 company_local；API key 存 Windows 認證管理員，不填進 Markdown 或 Git。

## 公司設定與能力核對

1. 設定頁選 assistants 協定，保存 endpoint 和 API key；助理團隊建立各名稱／ID。
2. 如需要公司 CA，在本機 config.json 的 assistant.ca_bundle 指向公司核准 PEM。不得使用 verify=False。
3. 主畫面選「公司 · 助理名稱」，用合成文字驗證多輪，從對話紀錄重開後再追問。
4. 連接器傳 additional_instructions 及 tool_choice=none；先確認平台接受且服務端不執行未授權工具。如果不支援，保留錯誤並由公司審查契約，不能直接移除工具限制。
5. 工作角色必須依回傳的 JSON 契約測試，再由可信本機 hook 登錄驗收證據。不可只寫 verified=True 交差。
6. API key 只管理認證，不取代 AD／owner 授權。目前仍為單人本機工作區；部門全面部署前完成原交接工作單。

失敗時先保存安全錯誤代碼與測試條件，再修改 adapter。不要同時改 UI、workflow JSON 和公司 API；不要把 Groq 或示範結果當公司驗收。新版文字流程完成之前不加入 DSE、Oracle 或郵件副作用。

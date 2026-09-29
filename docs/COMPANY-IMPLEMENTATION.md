# 給公司 GPT 6 sol：0.16.0 接手指令

請先讀根目錄 AGENTS.md、COMPANY-HANDOFF.md 與本文件。保留公司現有能成功呼叫的程式與設定，不重寫 UI，也不要把 Assistant ID 當 model。

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

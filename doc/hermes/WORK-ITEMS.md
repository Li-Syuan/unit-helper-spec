# 每次完成一項 Hermes 類能力

先選一個工作編號，再改程式。以下是開發路線與驗收條件，不是已實作清單，也不授權一次開發全部項目。H0 使用既有已確認的 UI 工作單；H1 以後先核對缺口及使用者選定範圍。

所有項目沿用 [TO-AGENT](../../TO-AGENT.md) 的資料、批准與真實服務界線。來源參考固定於 [UPSTREAM](UPSTREAM.md) 的提交。較廣的未移植需求仍保留在 [相容性清單](../../docs/HERMES-COMPATIBILITY.md)，不因優先順序較後而取消。

## H0 讓一次工作順利完成

- **交付結果**：使用者不建立 Skill，只用一位助理說明需求，在原處補條件、確認、看成果，再另行啟用排程。
- **目前已有**：統一輸入框、AgentJobs、inline 預覽、批准及結果。工作與 Skill 共用能力檢查，現場混淆原因需先重現。
- **實作入口**：依 [UX-SIMPLIFICATION](../../docs/UX-SIMPLIFICATION.md) 修改 workspace-ui、agent-jobs、能力提示及必要的共用服務。本包不再複製該工作單。
- **上游閱讀**：[architecture](reference/architecture.md)、[agent-loop](reference/agent-loop.md)。了解一次工作如何完成即可，不移植整個核心。
- **合成案例**：輸入每天八點的市場日報，不建立 Skill；補條件、修改及取消都留在同一工作。只有明確保存方法才開 Skill 草稿。批准前零搜尋，取消保存方法不影響工作。
- **離線驗證**：按改動選 `tests.test_workspace_turns`、`tests.test_agent_jobs`、`tests.test_web`，受影響畫面使用 `scripts/web-smoke.py --workspace-only`。
- **現場完成條件**：一位已驗證助理、零 Skill 完成試跑，人工核對來源後啟用並暫停排程。記錄不看手冊的使用者在哪裡停住；合成點擊不替代人工使用性。

## H1 完善自主工作的補問與恢復

- **交付結果**：代理遇到缺資料會停在可理解的位置；使用者知道要補充、檢查原請求，還是取回既有結果。
- **目前已有**：有限的 search/delegate/compose/ask 動作、持久預算、收據與 checkpoint。先確認問題是否只是呈現，不能重建第二套 runner。
- **實作入口**：[autonomous.py](../../desktop_app/autonomous.py)、[agent_jobs.py](../../desktop_app/agent_jobs.py)、[workflows.py](../../desktop_app/workflows.py)、[graph_runner.py](../../desktop_app/graph_runner.py) 與現有工作卡。
- **上游閱讀**：[agent-loop](reference/agent-loop.md)、[tools-runtime](reference/tools-runtime.md)、[prompt-assembly](reference/prompt-assembly.md)。
- **合成案例**：搜尋回傳來源不足、重複動作無進展、使用者取消、已知 run 中斷及未知送出。預算不得在接續時歸零；未知請求不得藉「補充」建立可重送副本。
- **設計必須先決定**：新的資訊是否仍在原批准範圍。若需要新計畫，顯示新修訂並重新批准；不把原工作改成成功，不因重開畫面派發。上游的自動 retry/fallback 不直接套用。
- **離線驗證**：按改動選 `tests.test_autonomous`、`tests.test_agent_jobs`、`tests.test_graph_runner`、`tests.test_dialogue_recovery`。擴充已有中斷案例。
- **現場完成條件**：已知請求可以依原收據恢復；未知送出被明確阻擋；來源品質不足與網路失敗能區分。保留安全錯誤編號，不收集原始 HTTP。

## H2 讓日報試跑接上可管理的排程

- **交付結果**：試跑後核對成果，明確啟用每日或每週工作；看得到下次台北時間、最近成果、暫停與失敗原因。
- **目前已有**：AgentJobs 排程、occurrence 防重、系統匣及原排程器。自然語言時間未必有可直接使用的結構化欄位，不能把 08:00 預設當作理解成功。
- **實作入口**：[agent_jobs.py](../../desktop_app/agent_jobs.py)、[workflows.py](../../desktop_app/workflows.py)、[core.py](../../desktop_app/core.py) 與 agent-jobs.js 的 schedule。查詢既有排程模型後才決定是否需額外資料。
- **上游閱讀**：[cron-internals](reference/cron-internals.md)、[session-storage](reference/session-storage.md)。借用工作、執行次數與交付分開的觀念，不改存上游 jobs.json。
- **合成案例**：可控制時鐘下的到期、睡眠後漏跑、重開、立即測試、暫停、連線修訂改變；同一 occurrence 不多派發。試跑成功但未核對或未同意時，不建立啟用排程。
- **時間交接**：已有經驗證的欄位才預填；缺少時保留原需求並問一次。若本項另需新增解析契約，先列版本、相容及失敗處理，不以字串猜測代替驗證。
- **離線驗證**：按改動選 `tests.test_agent_jobs`、`tests.test_work_orders`、`tests.test_assistant_briefings`、`tests.test_workflows`。不靠等待隔天驗證。
- **現場完成條件**：核准日報成功、來源可核對、另行啟用，App 或系統匣保留時到期執行。App 真正退出後沒有常駐服務，畫面不可承諾照常跑。
- **SMTP 後續工作**：見 [既有郵件提案](../../TO-AGENT.md#4-下一階段核准-smtp-自動寄信尚未實作)。需核准 host、port、TLS、認證方式、寄件者、允許收件範圍及測試信箱。以本機設定提供秘密，不寫入文件。先設計送信收據、部分拒收及未知結果，再實作；未知 SMTP 傳送不可盲目重試。

## H3 讓記憶與工作方法能安全重用

- **交付結果**：使用者可以挑選既有方法與記憶，知道本次傳送內容，修改後也找得到舊版工作成果。
- **目前已有**：明確保存的記憶、同助理隔離、對話快照、接續、Skill 不可變修訂及匯入匯出。新功能先選「方法修訂差異」「記憶查找」或「長對話接續」其中一項。
- **實作入口**：[skills.py](../../desktop_app/skills.py)、[continuity.py](../../desktop_app/continuity.py)、[dialogue_store.py](../../desktop_app/dialogue_store.py) 及相關 WebView 入口。
- **上游閱讀**：[creating-skills](reference/creating-skills.md)、[memory](reference/memory.md)、[session-storage](reference/session-storage.md)、[context-compression-and-caching](reference/context-compression-and-caching.md)。
- **合成案例**：同助理新對話選入記憶、跨助理不共享、停用後不再選入、舊工作仍讀原修訂。匯入不可信 Markdown 只能成為待確認資料；不能安裝腳本、取得環境變數或授權工具。
- **接續邊界**：本機摘要不等於遠端 Thread 已壓縮；新 Thread 與原文來源分開。摘要呼叫、記憶建議及套用均需可見，不背景處理所有聊天。
- **離線驗證**：按改動選 `tests.test_skills`、`tests.test_continuity`、`tests.test_dialogue_recovery`。資料變更另驗備份與回復，不先假定需要升 schema。
- **現場完成條件**：使用者能核對選入內容與目的助理，重開續談不串線，刪除記憶的說明不宣稱撤回已送出的資料。

## H4 擴充一個有契約的工具

- **交付結果**：新增一個核准工具，模型只能提出工具名稱與資料，App 驗證後執行並留下結果與收據。
- **目前已有**：核准搜尋及固定自主動作。尚無任意本機工具、通用外掛或 shell 權限。
- **實作入口**：[search_tools.py](../../desktop_app/search_tools.py)、[assistants_gateway.py](../../desktop_app/assistants_gateway.py)、[autonomous.py](../../desktop_app/autonomous.py) 與既有批准服務。先寫名稱、參數 schema、結果型別、權限、timeout、大小限制、取消及是否可重試，再決定最小共用介面。
- **上游閱讀**：[tools-runtime](reference/tools-runtime.md)、[adding-tools](reference/adding-tools.md)、[provider-runtime](reference/provider-runtime.md)。
- **第一個案例**：用無外部副作用的合成工具回覆固定測試資料，驗證未知名稱、壞參數、過大結果與取消。不要用 shell 或真實寄信測第一次派發。
- **達哥現場條件**：若選原生 function 路徑，先確認 run 是否接受名稱/schema、requires_action 與 submit_tool_outputs 格式。平台 pluginapi 不能拿來執行任意本機函數。若用現有 JSON 決策，仍由 App 的固定目錄驗證派發，不能假稱已接通原生 function calling。
- **離線驗證**：沿 `tests.test_search_tools`、`tests.test_assistants_gateway`、`tests.test_autonomous` 補具體工具邊界案例，參考 [串接工具包](../../docs/ADAPTER-TEST-KIT.md)。只有新增的行為需要新案例。
- **現場完成條件**：取得核准契約與測試權限，完成一次真實往返、重複 call 防重及取消驗證。工具文字不能自行指定目的 URL、headers、金鑰、路徑或提高權限。

## H5 真正並行的子代理工作

- **交付結果**：主工作可以同時處理互相獨立的子工作，明確顯示各自狀態及合併條件。
- **目前已有**：已選助理依序分工及上下文隔離。上游 lifecycle API 存在，不代表 QA 已有並行執行。
- **實作入口**：[workflows.py](../../desktop_app/workflows.py)、[graph_runner.py](../../desktop_app/graph_runner.py)、[autonomous.py](../../desktop_app/autonomous.py)、[profiles.py](../../desktop_app/profiles.py)。先畫父子狀態及收據關係，再判斷資料遷移需求。
- **上游閱讀**：[subagent-lifecycle-api](reference/subagent-lifecycle-api.md)、[agent-loop](reference/agent-loop.md)、[session-storage](reference/session-storage.md)。
- **先定契約**：子工作識別、固定目的助理、上下文、總預算、並行上限、父取消、部分失敗、結果合併與重開恢復。子工作不能超過父批准範圍，也不能自行再委派。
- **合成案例**：兩個獨立子工作，一個成功、一個失敗；父取消時仍等待真實請求收尾；晚到結果不復活；重開不重派；共用 Assistant ID 時使用不同上下文且總預算不超支。
- **離線驗證**：沿 `tests.test_autonomous`、`tests.test_workflows`、`tests.test_graph_runner` 的現有隔離及取消案例擴充。先驗服務，再呈現 UI；多卡片不等於真正並行。
- **現場完成條件**：確認平台同時 run 限制、配額與助理隔離，明確啟動有限次實測。沒有條件時保留依序功能，不把單模型多階段稱為獨立覆核。

## 實作與驗收回報

每次只填目前工作編號的結果，放入既有驗證摘要。私人紀錄留 artifacts，不新增逐版資料夾。

```text
工作編號與目標：
現場基準提交／已保留的修改：
根因或缺口證據：
修改檔案與服務契約：
批准／資料傳送／取消／防重的影響：
定向命令、結果、退出碼：
使用者操作結果與畫面：
真實達哥／來源品質／人工使用性：passed 或 not_tested，附理由
剩餘阻塞與下一個最小動作：
```

在專案根目錄以既有執行器選測，例如 H0：

```powershell
.\.venv\Scripts\python.exe scripts/test_runner.py --suite targeted --tests tests.test_workspace_turns tests.test_agent_jobs
```

其他項目替換 `--tests` 模組清單。功能變更新增一次 quick，核心、遷移、依賴或交付按 [開發指南](../../docs/DEVELOPMENT.md) 做一次完整驗證，避免 full 與 verify 重跑。未新增套件就不重建環境或離線包。現有剪貼簿失敗、正式 1.0 與現場未測狀態按 [VALIDATION](../../docs/VALIDATION.md) 如實保留。

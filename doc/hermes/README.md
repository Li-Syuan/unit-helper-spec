# 用 Hermes 參考資料擴充 QA agent

從本頁選一件可驗收的工作，再交給 SOL 6.1 或 Copilot 實作。這個資料夾提供離線官方文件與 QA 程式對照，不會被 App 當成 Skill、外掛或執行核心載入。下載或修改文件不會自動增加功能。

適用基準為 QA agent **1.0.0rc5**，整理日期 **2026-10-27**。沿用 Windows、Python **3.10.4**、現有 LangGraph 與達哥 Assistants 接線。現場分支可能已有修改，先比對再採用。

## 先完成一件工作

1. 先讀根目錄 [TO-AGENT](../../TO-AGENT.md) 與 [Copilot 共用指引](../../.github/copilot-instructions.md)。已有成功接線與合格環境就保留，不重跑整套安裝。
2. 在 [工作單](WORK-ITEMS.md) 選一個編號。近期優先 H0，讓一位助理、零 Skill 的交辦順利完成。後續項目先定範圍，不一次全做。
3. 只讀該項引用的上游文件與 QA 程式。完整現況直接看 [QA 架構圖](../../docs/ARCHITECTURE.md) 及 [Hermes 相容性清單](../../docs/HERMES-COMPATIBILITY.md)，不用重寫一份架構。
4. 先重現或建立合成案例，再修改程式。保留原批准、隔離、取消、未知送出及排程同意規則。
5. 跑受影響的 targeted 檢查，交付可操作結果、修改位置及未測項目。真實 API 由使用者明確啟動，文件本身不授權呼叫。

可以把這段貼給 SOL，將 H0 改成已同意的工作編號：

> 請讀 doc/hermes/README.md，依 WORK-ITEMS.md 的 H0 修改 QA agent。先核對現場分支、未提交修改、AGENTS.md 與既有接線。只閱讀此項需要的官方參考，沿用目前 Python、LangGraph、達哥 adapter 及資料，不整套安裝 Hermes。先重現，再做最小修正，完成指定旅程及相關測試。不要只改 Markdown 就回報完成。不要改寫能力證據或重送未知請求。交付程式差異、畫面、測試結果及現場待驗證事項；真實 API 測試另行說明請求量並取得同意。

## 依問題選 reference

這些是固定提交的英文官方文件，含上游程式範例。已收錄頁面之間可離線跳轉；其他延伸連結仍需連網。原始 Docusaurus 特殊區塊可能以文字顯示，這不影響 agent 閱讀正文。

| 你要處理的問題 | 離線參考 | 在 QA 應用時注意 |
|---|---|---|
| 不知道各模組怎麼分工 | [architecture](reference/architecture.md) | 對照既有 QA 架構，不另造核心。 |
| 工具完成後怎麼決定下一步 | [agent-loop](reference/agent-loop.md) | QA 已有有界 decide/act；檢查缺口再擴充。 |
| 工作指示、Skill、記憶怎麼組合 | [prompt-assembly](reference/prompt-assembly.md) | 只傳批准或明確選入內容，不混用聊天與工作歷史。 |
| 達哥接口與上游模型接口差在哪裡 | [provider-runtime](reference/provider-runtime.md) | Assistant ID 不是 model，保留下節的接線邊界。 |
| 新工具如何描述、驗參數及派發 | [tools-runtime](reference/tools-runtime.md)、[adding-tools](reference/adding-tools.md) | 上游可用工具不等於 QA 已核准。 |
| 重開後怎麼續談、處理歷史 | [session-storage](reference/session-storage.md) | QA 本機資料與達哥遠端 Thread 都需核對。 |
| 長對話與上下文限制 | [context-compression-and-caching](reference/context-compression-and-caching.md) | 本機壓縮不會清除達哥遠端歷史。 |
| 記憶該怎麼管理 | [memory](reference/memory.md) | QA 目前由人確認保存，不能直接改成背景自動傳送。 |
| 工作方法如何重用 | [creating-skills](reference/creating-skills.md) | QA Skill 是資料，不具備上游 shell、腳本或自動憑證傳遞能力。 |
| 工作如何排程及交付 | [cron-internals](reference/cron-internals.md) | 沿用原排程器；成功試跑與持續傳送同意仍分開。 |
| 真正並行子代理要管理什麼 | [subagent-lifecycle-api](reference/subagent-lifecycle-api.md) | 參考父子生命週期；QA 目前仍依序分工。 |
| 為何不能直接安裝完整上游 | [installation](reference/installation.md) | 僅核對環境差異，不執行安裝命令。QA 固定 3.10.4。 |

來源、完整授權及快照變更方式見 [UPSTREAM](UPSTREAM.md)。[SOURCES.json](SOURCES.json) 固定每份原始檔與本機副本的雜湊，另列 12 個已核對存在的上游程式位置。程式位置是固定版本連結，沒有複製成可執行模組，也未逐個驗證可移植性。

## 接達哥時要保留的差異

| 上游概念 | QA 現況與修改入口 | 不可直接照搬的行為 |
|---|---|---|
| 模型 provider | [assistants_gateway.py](../../desktop_app/assistants_gateway.py)、[profiles.py](../../desktop_app/profiles.py) 使用 Threads/Messages/Runs | 不把 Assistant ID 當 model，不以改 base URL 宣稱相容。 |
| 工具派發 | [search_tools.py](../../desktop_app/search_tools.py) 及核准的同源 pluginapi | 平台搜尋工具與未來本機工具要分開；模型不能指定 URL、金鑰或任意函數。 |
| 自主回圈 | [autonomous.py](../../desktop_app/autonomous.py)、[graph_runner.py](../../desktop_app/graph_runner.py)、[workflows.py](../../desktop_app/workflows.py) | 保留已批准範圍、持久額度與唯一工作狀態，不能直接套用上游 fallback/retry。 |
| 歷史與恢復 | [dialogue_service.py](../../desktop_app/dialogue_service.py) 及原請求帳本 | 已知 run 才沿原識別檢查；未知 POST 不重送。取消後仍追蹤真實請求收尾。 |
| 工作方法與排程 | [skills.py](../../desktop_app/skills.py)、[agent_jobs.py](../../desktop_app/agent_jobs.py) | 建立 Skill 不等於授權工具；工作不必依賴 Skill；讀到每日需求不等於排程已啟用。 |

實際達哥格式、搜尋來源品質及選用的 AD 接線，仍由現場另行驗收。這份參考包的文件檢查，不等於上游模組已移植或公司功能已通過。

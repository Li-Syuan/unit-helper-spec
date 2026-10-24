# Hermes 完整功能需求與相容性

2026-10-24 使用者補充：目標涵蓋 Hermes 功能，模型服務接達哥；同時確認 **必須保持 Python 3.10.4，先不更換核心**。因此本版沿用 QA agent／LangGraph。以下是後續移植與驗收清單，並非已實作清單，也不把尚未完成項目默默排除。

當日官方 HEAD 的唯讀查詢結果為 `f7fb481502bd3ef32be19e7034ba566801d7bf85`。功能盤點依當日官方文件；尚未對該提交的每個工具做逐項程式或相容性測試。未 clone、匯入或執行 Hermes 程式。

## 環境與接線事實

Hermes 官方目前支援的安裝 runtime 為 Python 3.14；pyproject 的較寬範圍是舊版升級用途，不是 Python 3.10.4 相容承諾。不能修改版本檢查、把它安裝進現有 `.venv`，再宣稱完整支援。維持 3.10.4 時，需逐項實作相容功能或挑選可移植模組；若日後採用上游程式，另核對固定提交、相依與 MIT 授權聲明。[官方安裝說明](https://hermes-agent.nousresearch.com/docs/getting-started/installation)、[官方專案設定](https://github.com/NousResearch/hermes-agent/blob/main/pyproject.toml)。

Hermes 一般自訂服務預期 Chat Completions；目前 QA agent 的成功範例是達哥 Threads／Messages／Runs 及平台 `/pluginapi`。兩者不是換 `base_url` 即等價，Assistant ID 也不能猜成模型名稱。須驗證轉接後的工具回呼、隔離、取消、長上下文及結果格式。[官方模型服務說明](https://hermes-agent.nousresearch.com/docs/integrations/providers)、[官方架構](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)。

## 功能對照

「部分完成」只指 QA agent 已有對應能力；不代表 Hermes 原生功能、完整相容或現場服務驗收。

| 功能群 | QA agent 目前狀態 | 尚需完成／外部條件 |
|---|---|---|
| 工作回圈、Plan、補問與工具選擇 | 部分完成：可編輯Plan／範圍確認、結構化下一步決策、核准搜尋／文字分工／成果、預算及失敗恢復 | 已有固定小型工具目錄及動態決策；仍缺可擴充的通用工具系統，更多工具需逐項契約及權限，不能直接以 JSON 文字當執行授權 |
| 子代理與並行分工 | 部分完成：指定已驗證助理依序處理、上下文隔離 | 真正並行派發、分支取消／合併、總預算、父子工作生命週期與資源上限 |
| Skills 與學習循環 | 部分完成：建立／分享／選用、版本快照、成功後明確另存草稿 | 自動產生與修訂建議、差異審閱、回退、標準相容及來源驗證；載入 Skill 不等於批准工具或安裝 |
| 長期記憶、歷史與上下文管理 | 部分完成：確認保存的筆記、助理隔離、固定快照、歷史／資料夾／接續 | 跨歷史搜尋、檢索排序、自動壓縮、自動記憶建議；需有可關閉、可刪除及資料傳送可見性 |
| 排程、背景與投遞 | 部分完成：每日／每週、台北時間、App／系統匣執行、防重 | 更完整 cron／間隔、獨立常駐服務、多目的地投遞與送達狀態；SMTP、聊天平台各需核准設定，尚未實作 |
| 終端、程式、檔案與瀏覽器 | 未移植 | 執行範圍、路徑限制、批准、程序取消、檔案備份、瀏覽器元件；各平台／容器環境需另備。現版不會因文件或模型要求執行命令 |
| MCP、外掛、外部平台及多媒體 | 未移植 | MCP／外掛生命週期與來源、平台憑證、圖像／語音／瀏覽器服務；達哥文字金鑰不會自動提供這些能力 |
| CLI／桌面、管理與研究工具 | 部分完成：共用服務 CLI、桌面、日誌、離線包、設定 | TUI／串流、API／ACP、工具管理、批次軌跡等需逐項盤點；保留現有資料與啟動入口，不覆寫為別套資料格式 |

上游功能群來源：[工具與工具集](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)、[專案功能概覽](https://github.com/NousResearch/hermes-agent)。第三方服務「有入口」與「已配置可用」必須分開，不得宣稱只填達哥三欄便可使用所有外部服務。

## 後續通用工具驗證：達哥能否承接本機 function 回圈

rc3自主模式已採文字JSON建議＋App驗證派發核准搜尋／助理操作，不以本機function calling為前提。以下是擴充到更通用工具時的現場驗證；不能當成rc3已通過的能力。

由現場 agent 使用核准的測試助理與非敏感內容，在明確同意後做一次有限實測，保留去識別結果：

1. 確認是否允許每次 run 傳入本機 function 的名稱與 schema，或必須先在達哥平台建立。先測一個無副作用的固定回覆函數。
2. 確認服務回傳 `requires_action` 時，參數與 call ID 可驗證，並能由本機回傳 `submit_tool_outputs` 後完成。同一 call 不重複執行。不能把平台 `/pluginapi` 名稱當成任意本機工具。
3. 核對工具停用、未知工具拒絕、壞參數、逾時、取消及未知送出；沒有證據就記 `not_tested`，不要開放 shell 來測試。
4. 驗證多段／多助理隔離、工具結果大小限制、上下文壓縮後的歷史接續。模型與上下文上限依實際服務確認，不捏造能力。

若只支援平台既有插件，先以已核准搜尋完成目前版本；其餘本機工具仍是待接線，不能透過 prompt 假裝具備工具呼叫。若另提供正式 Chat Completions 契約，可評估相容 provider，但不擅自改接口。達哥歷史保存在遠端 Thread；壓縮本機文字不會清除遠端歷史，需驗證摘要接續新 Thread 的策略，不能宣稱原 Thread 已壓縮。

## 交付順序與完成定義

先完成現場聊天／工作格式／核准搜尋及一次完整工作；再依序補通用工具回圈、並行代理、Skills／記憶學習、常駐排程與投遞，最後外掛／多媒體／研究入口。這是執行順序，不是刪除完整功能需求。

每一群都需列出實際操作入口、可重現案例、缺少外部服務時的狀態、資料及批准界線；完整功能聲明須附固定上游版本的逐工具對照，而非只比八個類別名稱。此矩陣目前仍有未移植功能，因此 **1.0.0rc3 是 QA agent 工作代理候選版，不是完整 Hermes，也不是正式 1.0 驗收完成**。

## 接手開發者的程式入口

目前版本為 **1.0.0rc5**。上方rc3是自主回圈落地階段；目前側欄／統一輸入框依rc4。下表供Copilot定位現有程式，不表示已完成上游同名功能或現場驗收。測試命令依 [TO-AGENT](../TO-AGENT.md#3-測試與問題回報) 選targeted，勿將所有模組每次都跑一遍。

| 工作面向 | 目前共用入口 | 相關現有測試 |
|---|---|---|
| 達哥服務與工具往返 | [assistants_gateway](../desktop_app/assistants_gateway.py)、[search_tools](../desktop_app/search_tools.py) | `tests.test_assistants_gateway`、`tests.test_search_tools` |
| 對話／工作辨識與連結 | [workspace_turns](../desktop_app/workspace_turns.py)、[agent_jobs](../desktop_app/agent_jobs.py) | `tests.test_workspace_turns`、`tests.test_agent_jobs` |
| 自主決策／有限工具／恢復 | [autonomous](../desktop_app/autonomous.py)、[graph_runner](../desktop_app/graph_runner.py)、[workflows](../desktop_app/workflows.py) | `tests.test_autonomous`、`tests.test_graph_runner`、`tests.test_workflows` |
| Skill、記憶與接續 | [skills](../desktop_app/skills.py)、[continuity](../desktop_app/continuity.py) | `tests.test_skills`、`tests.test_continuity`、`tests.test_dialogue_recovery` |
| CLI／畫面共用 | [cli](../desktop_app/cli.py)、[workspace-ui](../desktop_app/web_assets/workspace-ui.js) | `tests.test_cli`；受影響UI用既有 `scripts/web-smoke.py` 旅程 |
| SMTP（待開發） | [既有提案](../TO-AGENT.md#4-下一階段核准-smtp-自動寄信尚未實作)；日後接現有成果與排程服務 | 尚無正式郵件adapter／CLI；需補傳送未知、部分拒收與重複派發案例 |

每次擴充先選一項旅程，列現有能力、缺口、修改入口、正反驗收及現場資訊；使用者批准範圍後再實作。無需為了Copilot閱讀而把Hermes整庫複製進來；上游文件連結與此對照已能提供方向。

若確實移植上游程式，先固定提交與檔案、核對Python3.10.4和Windows相容性、間接依賴／離線wheels及MIT授權，保留來源及授權文字。沿現有服務及批准／收據／取消規則整合，不建立第二套狀態資料庫、scheduler或隱藏工具權限。裝好套件、複製程式或修改prompt都不能替代功能驗收；並行代理、MCP、shell／檔案等仍按上表缺口處理。

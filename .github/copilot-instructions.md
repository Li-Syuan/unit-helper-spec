# QA agent：Copilot 共用指引

目前為 **1.0.0rc4 候選版**。先讀根目錄 [AGENTS](../AGENTS.md) 的最新優先規則與 [TO-AGENT](../TO-AGENT.md)；依任務查 [架構](../docs/PROJECT.md)、[驗證紀錄](../docs/VALIDATION.md)，不要把歷代章節當成新增需求。保留現場未提交修改、已成功接線及個人資料。

## 固定架構

- Windows x64、Python **恰好3.10.4**，沿用專案 `.venv`；69個鎖定wheels都在 `offline-app/packages`。沒有環境才用既有離線安裝器；環境符合lock不重裝，不連外補件。
- WebView主介面、Tk備用；主Store8、DialogueStore5。WorkflowService／LangGraph仍是唯一工作執行與狀態來源，不另建runner、API server或排程器。
- `desktop_app/workspace_turns.py` 共用Web／CLI交辦；`assistants_gateway.py` 接達哥Threads／Messages／Runs與核准pluginapi。不要把Assistant ID猜成model，不改成Chat Completions。
- 日常只有對話／我的工作；Skill在輸入框，設定集中助理／記憶／外觀。舊入口與歷史保留，UI不自行判成功或改寫raw wire。

## 必須保留

- 辨識、規劃及自主決策停工具；模型JSON只是建議。執行需當前修訂明確批准，排程另需成功試跑、人工核對及持續同意。
- 核准搜尋及每助理版本的能力證據分開；三欄保存→選用工具核准→最多8次基本檢查，搜尋另測。聊天可用與工作可用分開；不手填verified。
- 預設6動作／12請求／600秒，派發前持久計數；未知POST不重送，已知run／快取沿原ID恢復。真future守護取消、刪除、切設定與關閉。
- keyring保存金鑰，TLS保持驗證，真實失敗不fallback demo。不要讀出或附上 `.env`、憑證、內部設定、HTTP body、完整SQLite。升級先備份再交易。
- Hermes是功能參考，沒有內嵌其核心；按 [功能與程式對照](../docs/HERMES-COMPATIBILITY.md#接手開發者的程式入口) 逐項擴充。不整包clone／vendor、不換Python或依賴來繞過相容性；移植需固定上游提交、保留授權及驗證。

## 工作方式

先定位一條可重現旅程→最小修正→相關targeted；功能改動加quick，核心／交付由整合者一次 `scripts/verify.py development`，不先full再重跑。純文件只查連結／格式／manifest，不執行App回歸。新案例保護具體行為，TestCase class列入 `tests/suites.json`。

缺現場資訊只問阻擋下一步的項目；真實API須使用者明確啟動並說明請求量，不因執行接手prompt就授權呼叫。分列離線合成、本機真實與現場結果，未測為not_tested。不要改防毒／執行政策／權限設定。

預設單一agent；僅在使用者授權分工時，Coordinator＋一個實作工作包同時進行，先定檔案責任，子代理不再委派。QA唯讀審查；角色不等於App產品裡的多助理。

交付列問題、根因證據、修改位置、驗證命令／結果、剩餘現場事項。依實際變更更新既有文件及manifest，不累積新歷史包，不自行宣稱正式1.0或完整Hermes。

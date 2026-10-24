---
name: UnitHelper-Backend
description: 修復達哥接線、續談、代理執行及資料契約；保留既有共用服務。
tools: ['read', 'search', 'edit', 'execute']
user-invocable: false
disable-model-invocation: false
---

讀 [共用指引](../copilot-instructions.md)、[AGENTS](../../AGENTS.md) 與 [接手工作單](../../TO-AGENT.md)。只修改分配的服務範圍，不再委派。

- 依證據定位 `desktop_app/assistants_gateway.py`／`profiles.py`、`dialogue_service.py`／`continuity.py` 或 `workspace_turns.py`／`agent_jobs.py`，不要重寫UI或所有adapter。
- 達哥契約與JSON驗證分層；保留原始reply與畫面文字、固定request ID、助理revision及原thread。未知送出不retry；連結中斷只修連結，不重派發。
- 沿 `workflows.py`／`graph_runner.py`／`autonomous.py` 擴充；規劃無工具、批准及額度由服務層強制，checkpoint不能當exactly-once保證。
- 身分、核准搜尋、能力證據與遷移依最新AGENTS；沒有真實資訊就提供接線缺口，不猜AD／Oracle／認證格式。
- 選受影響模組做targeted，回報命令／結果及需要整合者驗證的範圍。不要自行跑另一份full、修改鎖檔或呼叫真實模型。

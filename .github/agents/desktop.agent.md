---
name: UnitHelper-Desktop
description: 維護 QA agent WebView 主介面與 Tkinter 備用畫面、提示、表格、對話與本機操作入口。
tools: ['read', 'search', 'edit', 'execute']
user-invocable: false
disable-model-invocation: false
---

目前架構與版本見 [AGENTS](../../AGENTS.md)、[產品](../../docs/PROJECT.md)、[組織工作單](../../COMPANY-HANDOFF.md)、[驗證](../../docs/VALIDATION.md)。WebView2 為主、Tkinter為備用，LangGraph已正式整合；連線設定不代表已驗收。

固定Python3.10.4、正式69套件lock與離線wheels。組織現有修改先保留比較，不能用整包覆蓋。金鑰keyring、TLS驗證、無demo fallback、未知寫入不retry、一次明確批准與真實future隔離保持。主畫面task_drafts永遠未啟用。普通聊天僅在另行核准 chat_search_enabled 時使用已核准搜尋；planner／task草稿保持無工具，日報及rag沿用原授權。個別key只存keyring，改憑證使綁定失效。未送出重試必須有typed preflight證據，不能依缺少帳本推論。

日常選targeted／quick，核心或發布才由Coordinator安排一次verify full；UI變更加真WebView smoke。新增測試保護具體行為，class須分類，不堆文案案例。實測分mock/local/company/not_tested，不用skip或旗標替代驗收。不得改防毒、執行政策、TLS或私自呼叫組織模型。

只改指派的UI路徑，不另委派。web_assets／web_bridge為主介面，ui.py／theme.py等為Tk備用。I/O不阻塞UI與bridge全域鎖；模型內容不可當HTML／指令，沿用安全renderer。所有執行、批准、刪除與恢復走服務，不在JS推定成功。

失敗原處呈現原因與問題編號，保留已完成訊息及草稿；檢查與取回原請求分開，另開對話的歷史轉交要預覽確認。刪除取消預設焦點，busy不得批次刪除。主題／資料刷新保留選取、草稿與閱讀位置。組織連線入口以Endpoint、API key與Assistant ID為主；角色與工具驗收不偽裝完成。

檢查深淺、1050×700及正常／最大化按鈕可達，保留原圖示／DPI／IME防護；人工IME與可用性需另外實測。

0.22.0工作台：主Store schema8，work_orders為交辦共用服務，CLI與Web使用同一批准／防重契約；規劃不開工具，試跑後人工核對再啟用每日排程。WebView系統匣不另造runner。接手先讀docs/WORKBENCH.md與最新VALIDATION，不能以demo或Skill冒充使用者批准。


0.23.0：自建Skill／單助理Plan見docs/SKILLS.md與AGENTS最新節。沿用SkillService→WorkflowService→LangGraph；不得另造引擎或以prompt解鎖工具。真實能力只由明確相容性測試產生證據，規劃無工具，批准與持續排程分開；Markdown匯入僅草稿。

1.0.0rc1：依使用者最新更正，直接填endpoint/Assistant ID/API key三欄；CA預設系統信任，deployment.json僅選用預填。更換已有端點/協定先確認並撤銷舊綁定，預填不覆寫手動設定；不要把內部端點或憑證提交Git。activation兩輪工具停用合成斷言與metadata/Skill/search各自驗收。continuity提供明確記憶預覽確認、固定thread快照、草稿CAS、來源接續；Dialogue schema4先backup交易遷移，主Store仍8。未知摘要POST不重送、接續只建草稿；記憶不自動跨助理或登入者傳送。舊進階歷史保留原入口，不強制遷移。先驗證主對話十輪/重開/故障恢復，再單助理Skill與排程；實際DVC/AD/來源品質未驗收維持候選版。

1.0候選版現場接手先讀 [TO-AGENT](../../TO-AGENT.md)。主對話本機命名/可收合資料夾不派發；SMTP僅後續規格，尚未實作。

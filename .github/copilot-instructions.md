# Copilot 接手入口

0.22.0先讀[工作台](../docs/WORKBENCH.md)：單助理交辦由work_orders共用服務處理，主Store為schema8（先backup），CLI不啟動排程器。規劃零工具、試跑與每日持續授權分開；不要讓模型或Skill代填確認。WebView系統匣只是同一程序背景運作，不是Windows服務。依賴69wheels不變，來源與公司API效果仍須現場驗收。

版本與實測結果以 [README](../README.md)、[驗證紀錄](../docs/VALIDATION.md) 為準。先讀 [AGENTS](../AGENTS.md) 與 [組織工作單](../COMPANY-HANDOFF.md)，保留組織成功程式及設定後再比對合併。

正式架構為 Windows x64、Python 恰好 3.10.4、WebView2 主介面、Tkinter 備用、SQLite 與 OpenAI SDK；LangGraph 已接管批准後的多助理依序流程，不另建一套引擎。主畫面任務草稿維持未啟用，普通聊天需另行勾選才使用核准搜尋；規劃及任務草稿不開工具。只有明確核准搜尋可進 pluginapi。TLS、未知寫入不重送、取消防晚到回覆及助理版本綁定不可放寬。

組織先走正式69套件離線安裝：install-offline.bat 或 scripts/install-offline.py，新資料夾、新環境，保留既有組織程式。不得使用 lab lock、連外補件或為安裝成功任意降版；Python／WebView2／.NET另由組織提供。

對話失敗先用檢查／取回原請求；不可重新生成 request ID 冒充恢復。刪除必須經服務預覽與確認；執行中或取消尚未收尾拒絕。工作最少防重識別保留，正文與成果可刪。日誌與分享包只用 support.py 白名單，不記金鑰、網址、訊息、HTTP body 或原始例外。

測試依風險選取：一般功能 targeted＋quick；核心服務／遷移／發布以 scripts/verify.py development 跑一次 full，不先重跑 full。WebView UI變更再跑 scripts/web-smoke.py。新增 TestCase 必須分類，不以數量增加當標準。組織真實接口、人工GUI、IME與Excel未測就記 not_tested，mock不代替。

開發分工按AGENTS，含Coordinator最多兩包同時進行，子代理不另委派。不要擴張中央平台、更新器或任意命令工具。使用者的目標是填參數後操作既有功能，先修可重現的失敗與入口，避免重寫畫面或整套服務。

登入只接 company_auth.py 的可信 AD／名單函數；identity_mode=company 必須先驗證才建工作區，不能以返回 True 代替完整身分契約。每 subject 獨立資料夾，舊資料不自動搬移；密碼不保存、未知認證例外不顯示。publisher.json 是私人作者設定，不進 Git；範例只留空欄位。


0.23.0：自建Skill／單助理Plan見docs/SKILLS.md與AGENTS最新節。沿用SkillService→WorkflowService→LangGraph；不得另造引擎或以prompt解鎖工具。真實能力只由明確相容性測試產生證據，規劃無工具，批准與持續排程分開；Markdown匯入僅草稿。

1.0候選版：直接填endpoint/Assistant ID/API key三欄；CA預設系統信任，deployment.json僅選用預填。改已有端點/協定先確認並撤銷舊綁定，不提交內部設定。activation兩輪聊天、Skill/search各自驗收；continuity記憶預覽確認、固定快照、草稿CAS及接續保持。Dialogue schema4、主Store8不變；未知POST不重送。實際DVC/AD/來源品質未驗收維持候選版。

1.0.0rc3：新交辦預設自主模式，agent.version=2；舊固定流程不變。autonomous.py固定search/delegate/compose/ask目錄，原LangGraph決策／執行條件循環，WorkflowService唯一狀態。獨立自主格式證據不可手填；一次確認固定目標、工具、助理及資料，最多6動作／12請求／600秒，工具結果續答計量，未知POST不retry。來源與收據核對不等於事實正確。先讀docs/AGENT-WORK.md及AGENTS最新節；仍Python3.10.4／69wheels，無schema改動或完整Hermes。

1.0候選版現場接手先讀 [TO-AGENT](../TO-AGENT.md)。主對話本機命名/可收合資料夾不派發；SMTP僅後續規格，尚未實作。
最新方向：完整Hermes功能是後續目標；使用者仍要求Python3.10.4、不換核心。依[相容性清單](../docs/HERMES-COMPATIBILITY.md)逐項驗證，不直接安裝Hermes新版、不把達哥Assistants當Chat Completions、不將本版候選成果宣稱全功能完成。

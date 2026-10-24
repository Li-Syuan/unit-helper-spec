# Copilot 接手入口

目前版本1.0.0rc4候選版。先讀../AGENTS.md、../TO-AGENT.md、../docs/PROJECT.md及../docs/VALIDATION.md。保留現場既有接線、資料與設定，再做最小修正；不把合成通過當DVC／AD／來源品質驗收。

Python恰好3.10.4、主Store8、DialogueStore5、69個鎖定wheels。升級先backup再交易，不降低schema、不循環重裝套件、不新增依賴。WebView主介面、Tk備用。工作仍由WorkflowService／LangGraph執行，沒有第二套狀態或排程器。

日常對話／我的工作兩入口；Skill在composer，助理／記憶／外觀在設定，舊入口在更多工具。workspace_turns.py共用CLI/Web的版本化建議與固定來源工作連結；raw wire與顯示文字分存。舊chat/task沿原thread。辨識與規劃停工具，JSON不是批准；只有明確確認才執行，持續排程另行核對同意。未知POST不重送，真future守護取消、刪除與close，金鑰只keyring，TLS不關閉，失敗無demo fallback。

啟用先保存三欄，再核准選用搜尋工具，最後最多8次基本檢查；搜尋另一次。每項同修訂實測證據，不手填verified。聊天可用與工作可用分開；metadata失敗不是聊天失敗。

功能修改targeted＋quick，核心／發布由整合者一次verify full。UI改動跑web-smoke.py --workspace-only。新增案例保護具體行為，class必須分類，不以數量為目標。保留失敗證據，未測列not_tested；不改防毒或系統執行政策。

只在使用者授權的範圍安排分工；Coordinator與一個實作工作包同時進行，整合後再審查，子代理不另委派。

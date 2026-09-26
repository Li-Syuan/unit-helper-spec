# 單位桌面小幫手 v2

讀取根目錄 [AGENTS.md](../AGENTS.md)、[SPEC.md](../SPEC.md) 與 [START-HERE.md](../START-HERE.md)。這是精簡版，取代舊 Multi-Agent v1 的範圍。

必須保留 Tkinter、原有聊天／搜尋／排程／SQLite、公司既有後端與 AD 登入。openai 套件連公司端點；產品一個助理搭配核准工具。第一版為三項 Oracle 查詢、TXT/CSV／文字整理、排程通知、issue、使用者點擊更新。

依 IMPLEMENTATION.md M0～M4 開發；未實際驗證就不能標 real_passed。可用 custom agents 時先凍結契約再分工，最多兩個工作包並行；否則順序實作。不要引入延後的產品 runtime 多 agent、Skill 市集、Office 編修或公共模型服務。

v2.1 加入 [Plan 與選項契約](../PLAN-AND-CHOICES.md)：後端強制確認 gate、是非／單選／多選表單、舊修訂防重、無原生功能的固定表單 fallback。納入 AT-16～AT-21；不新增持續自主 Goal。

v2.2 另讀 [引導查詢](../GUIDED-QUERIES.md)，完成 UH-13／UH-14 與 AT-22～AT-27；一般模式一次送出、Plan 仍需批准，Excel 複製基於原 snapshot。快速回報不自動提交或附加資料。

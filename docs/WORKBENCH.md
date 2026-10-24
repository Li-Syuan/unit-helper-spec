# 交辦工作與 CLI

1.0.0rc2沿用桌面的達哥連接器、工作引擎及本機排程，不需要另部署 API server。主資料庫schema8、DialogueStore schema4（舊版先backup）；不可用舊版直接開啟新資料庫。原有任務草稿維持未啟用。

新一般工作使用 `/job`、`/job-create`、`/job-reply`、`/job-preview`、`/job-run`，與主對話「交辦工作」共用服務；`qa.bat jobs`列JSON。可選Skill、記憶及有限補查，並支援核對後每日／每週排程。完整格式與操作見[工作代理](AGENT-WORK.md)。下方 `/order` 是原每日搜尋交辦，仍保留相容，UI位於進階入口；不要混用兩種紀錄ID。CLI不啟動排程器，也不能以模型輸出或管線代替批准。

## 三欄啟用與記憶命令

`/activation`看狀態，`/activate AssistantID`互動詢問endpoint（留空沿用既有設定），再遮蔽讀取key（不接受key命令列參數或管線），只保存不呼叫。更換已有端點/協定先確認。CA用系統信任，部署預填檔為選用。`/activation-test profileID`明確確認後兩輪合成測試；聊天、Skill及搜尋證據獨立。隔離`--demo`不能開真實連線。

`/memories [聊天助理ID]`列記憶；`/remember {"data":{"assistant_id":"demo-general","title":"語言偏好","text":"用繁體中文","category":"preference"}}`預覽確認保存。種類還有background/rule；修改加入id/revision。`/memory-manage ID disable|enable|delete`預覽確認。`/new-memory 聊天助理ID`確認選定記憶後開新對話；普通`/new`不隱藏加入記憶。

`/rename 標題`、`/pin on|off`、`/draft 文字`保存目前對話資訊。`/summarize 選取原文`明確單次摘要，只輸出結果；`/continue 修改後摘要`預覽後建立同助理新草稿，舊連線失效用`/continue-to 聊天助理ID 摘要`。所有接續都不自動送出。

`/skill-with-memory {"id":"SkillID","revision":1,"profile_id":"demo","memory_ids":["記憶ID"]}`明確選記憶建立規劃，之後仍需/reply、/preview、/approve。CLI不啟動排程器，模型輸出或管線不能批准。

`/folders`列主對話資料夾，`/folder-create 名稱`新增，`/folder-move ID`將目前對話移入，`/folder-move none`移回未分類。`/rename`不帶文字可恢復本機自動名稱。這些操作零模型請求、不變更遠端thread。

## 桌面最短路徑

1. 雙擊 `start-app.bat`，在主對話按「交辦工作」。原本聊天草稿不會被送出或清除。
2. 選擇助理，輸入「每天早上八點，幫我整理台股、美股和重大總經新聞」。範例只填入草稿，按提交才請助理規劃。
3. 依提示補齊新聞範圍、資訊來源及每天台北時間。可以用表單修改；按預覽不會搜尋。
4. 核對目的助理與資料範圍，按「確認試跑一次」。原處顯示執行狀態及完整文字。
5. 人工核對資料日期與來源，再同意每日持續傳送並確認啟用。沒有人工核對時不啟用。

公司助理須使用既有 Assistants 協定，並在設定核准唯讀搜尋工具。規劃只提出 JSON 建議，不啟用工具、不標記角色驗證；真實格式與搜尋效果仍需逐助理實測。這條單助理路徑不要求四個角色。

沒有金鑰時選「示範助理」可體驗補問、編輯、預覽及合成成果；不會搜尋即時新聞，也不能把示範成果變成真實排程。真實連線失敗不切示範。

試跑後條件固定，修改請以原工作建立新交辦，原成果保留。取消後不接受晚到結果；原請求結果不明時不自動重送。「檢查原請求」只讀遠端狀態；可恢復的規劃請求沿原識別取回，日報執行本版僅檢查、不自動重跑。交辦是獨立保存的需求副本，來源聊天刪除不恢復原對話。工作／排程經既有清理入口刪除後連結顯示失效，不重建。

## 視窗關閉與背景運作

WebView 首次按 X 詢問留在系統匣或退出，可記住並在設定更改。系統匣提供開啟視窗、運作狀態及退出；圖示建立失敗時不隱藏視窗。

留在系統匣仍是同一個 App 程序。不是 Windows 服務，不會自動開機啟動或喚醒電腦。真正退出、睡眠、關機或登入失效時不能保證執行；漏跑沿用既有有限補跑與防重規則。Tk 備用入口維持原關閉行為。

## CLI 操作

請用專案的 Python 3.10.4。`qa.bat` 會切換至正確工作目錄，從其他目錄啟動亦可。

```bat
qa.bat --demo
qa.bat assistants
qa.bat orders
qa.bat status
qa.bat result 工作ID
qa.bat desktop
```

`--demo` 是一次性離線工作區，不載入正式設定。正式模式沿用本機設定及 keyring；AD 模式先互動輸入工號及遮蔽密碼，登入成功才開資料庫。CLI 不提供命令列金鑰或密碼。

互動介面可直接聊天，`/help` 查看完整指令。交辦範例：

```text
/assistants
/order demo 每天早上八點，幫我整理台股、美股和重大總經新聞。
/order-edit {"scope":"台股＋美股＋重大總經新聞","sources":"公開網路可靠來源","time_hhmm":"08:00"}
/order-preview
/order-run
/orders
/quit
```

真實日報把 demo 換成清單中的工作 profile ID。`/order-run` 需要互動確認，`/order-enable` 另需人工核對與每日授權。管線不能批准；這是操作限制，不是辨識人類身分的技術保證。Skill／agent 不得代填批准字串。

只讀指令輸出 JSON，成功退出碼0、操作失敗1、用法錯誤2、中斷130；互動模式的單次錯誤留在工作台供處理。模型文字一律當資料，不執行命令或終端控制碼。

CLI 與桌面包含背景系統匣不能同時開同一資料目錄。CLI 不啟動排程器；讀取時仍會開啟工作區並執行正常的資料升級／中斷狀態整理，不是資料庫的唯讀鑑識工具。離開時收尾未完成請求，已批准的排程需回桌面運作。

CLI JSON 包含使用者選擇查看的對話或成果，不是去識別支援包；回報問題請沿用「說明與關於」的安全匯出。

## Skill 與接手界線

[每日交辦 Skill](skills/qa-daily-briefing/SKILL.md) 隨專案提供，未自動安裝到任何開發工具。可由組織依其 agent／Copilot 設定載入；不要把安裝 Skill 當成模型取得執行權限。

共用服務是 `work_orders.py`；桌面 bridge 與 CLI 只提供入口。新工作資料不觸碰公司舊資料庫，既有 69 個 wheels 及鎖檔不變。公司需驗證工具停用的規劃格式、核准搜尋、兩次確認、多輪中斷與來源品質；本機合成測試不能代替公司驗收。

## 使用者自建方法

新增 `skills` 查詢及 `/skill ID`、表單／Markdown建立、相容性測試與單助理規劃。詳見 [SKILLS](SKILLS.md)。這是 App 工作方法功能，與供開發agent使用的 docs/skills 操作指引分開；兩者都不能代替批准。

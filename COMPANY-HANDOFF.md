# QA agent 現場接手工作單

當前 **1.0.0rc5候選版**。要直接交給SOL／Copilot的指令見[TO-AGENT](TO-AGENT.md)；此檔集中列出現場所需資訊與完成條件，不重複歷代交接。現場已有成功接線須保留，再做最小修改。

VS Code Copilot先依[接手入口](TO-AGENT.md#在-vs-code-copilot-接手)選Coordinator或附上接手prompt；先離線診斷，再取得明確授權做現場驗收，不需匯入Hermes核心。

## 最短操作路徑

1. 完整clone或解壓Code ZIP。核准Python3.10.4 x64完整版、WebView2與.NET準備好後，首次用`install-offline.bat`建立環境；已有符合lock的環境不重建。69個wheels全在`offline-app/packages`。
2. 首次部署做一次`test-company.bat`，日常修改只跑targeted／quick；[驗證紀錄](docs/VALIDATION.md)分開記錄本機與真實服務。
3. `start-app.bat` → 設定助理 → 填endpoint／Assistant ID／key並保存。如需搜尋，先核對並保存工具，再明確同意最多8次基本檢查；搜尋另外一次。
4. 聊天成功即可使用一般聊天；工作格式、自主決策、搜尋需分別通過。單一助理即可，不需先設四個角色。
5. 在同一輸入框提出需求、補條件、核對計畫後確認執行。日報成果與來源人工核對後，另行同意每日排程。App需開啟或留在系統匣。

普通本機模式不是AD登入。選用組織登入的部署，須先完成可信驗證及App使用資格，未接線不能以示範身分冒充。

## 已完成的本機能力

- 單一輸入框聊天／交辦，最近對話、分類／置頂／刪除、固定記憶及明確接續。
- Skill建立、分享、補問選項、一次計畫確認、有界自主搜尋／依序分工／成果，以及獨立排程授權。
- WebView主介面、Tk備用、共用CLI、待辦、回饋、資料清理、安全診斷與支援紀錄。
- Windows keyring、Assistants收據帳本、已知請求恢復及未知POST防重；正式LangGraph已整合。

主Store8、DialogueStore5；升級前備份並交易遷移，不能直接降低schema。既有公司SQLite不在本次自動遷移範圍。

## 現場資訊與驗收

rc5 先在「設定助理 → 連線診斷」定位助理／修訂／檢查項目。聊天通過即可使用，需求辨識、工作格式、自主決策及搜尋分別驗證。失敗時預覽並匯出修復 Markdown，交給 Copilot 配合 TO-AGENT；工作單不含端點、金鑰、Assistant ID、對話或原始 HTTP。不要直接附私人診斷 JSON。

| 項目 | 修改入口／命令 | 現場完成條件 |
|---|---|---|
| 診斷與安全工作單 | connection_diagnostics.py；`scripts/test_runner.py --suite targeted --tests tests.test_connection_diagnostics tests.test_support` | 兩位助理的結果不混用；重開保留失敗階段；匯出無秘密 |
| 聊天中斷 | dialogue_service.py／assistants_gateway.py；依工作單選恢復測試 | 已知 run 沿原請求取回；未知送出不重派，原訊息及草稿保留 |
| 使用者操作 | WebView設定及原對話診斷入口 | 真人完成查看→預覽→分享→明確分項重測；Copilot能依工作單定位，而非重做整套架構 |

本機合成與自動WebView通過不等於實際達哥或公司Copilot驗收。AD只有採用組織登入才需要接線；四角色不是普通聊天或單助理工作的前提。

秘密只填本機安全設定，不貼入本文件或Git。

| 工作 | 需提供 | 修改／操作入口 | 完成條件 |
|---|---|---|---|
| 環境 | 核准Python路徑、Windows前置軟體、可寫目錄 | install-offline.bat、scripts/doctor.py | 69wheels/hash/lock、pip check及一次full通過；缺件停止、不降版補件 |
| 助理接線 | endpoint、ID、API key、已成功的去識別請求／回覆範例 | activation.py、profiles.py、assistants_gateway.py | 同thread兩輪啟用、十輪續談、兩段對話切換及重開；metadata失敗不直接判聊天不可用 |
| 工作格式 | 工具停用能力、嚴格JSON回覆契約 | dialogue_routing.py、workspace_turns.py、agent_jobs.py | 聊天／辨識／工作／自主分項實測，舊revision證據失效；不得手填verified |
| 搜尋 | function名稱、schema、唯讀用途、權限及已知來源 | search_tools.py、Assistants pluginapi | 僅核准工具；實際收據與回覆格式通過，資料日期與來源另人工核對 |
| AD／使用資格（選用） | authenticate函數、穩定subject、允許名單／部門、到期規則 | company_auth.py、authentication.py | 允許／拒絕／停用／到期實測；未成功不開Store／scheduler，密碼不保存，不接受單一True |
| Oracle三項查詢（後續） | 核准SQL、參數、欄位、關聯、單位範圍、人工比對答案 | gateways.py、query catalog；詳見QUERY-CATALOG | bind唯讀查詢、可信身份注入範圍，日期與精度可核對；不把DB密碼交模型 |
| 舊資料與排程 | 原SQLite/schema、時區、舊runner與未完成工作 | 先唯讀盤點、備份、dry-run、回復方案 | 不刪原DB；確認舊runner停用且無執行中工作，才啟用對應新排程 |
| 使用者驗收／打包 | 真實Windows倍率、IME、Excel、測試使用者及發布流程 | WebView／Tk入口、PyInstaller後續流程 | 真人完成旅程、複製貼上／取消／重開；未測分列，不用合成替代 |

CA預設系統信任，僅實際憑證錯誤時由部署者處理；不得關TLS。不同助理或連線版本不得共用錯誤歷史／批准。未知POST只檢查原請求，不盲目重送。

## 核准查詢資訊表

依[查詢契約](docs/QUERY-CATALOG.md)各填一份，連線秘密另管：

| 查詢 | 名稱與用途 | 參數／預設／限制 | 欄位／單位／精度 | 核准資料範圍 | 人工對照資料時間及答案 |
|---|---|---|---|---|---|
| 1 | 待提供 | 待提供 | 待提供 | 待提供 | 待提供 |
| 2 | 待提供 | 待提供 | 待提供 | 待提供 | 待提供 |
| 3 | 待提供 | 待提供 | 待提供 | 待提供 | 待提供 |

## 測試與問題回報

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_workspace_turns tests.test_continuity tests.test_assistants_gateway
```

選受影響模組即可；功能修改加quick，核心或交付才一次`verify.py development`，不先full再重跑。UI變更使用`web-smoke.py --workspace-only`。真實hooks見[串接測試工具包](docs/ADAPTER-TEST-KIT.md)，未配置保持not_tested；真實API測試需明確啟動並說明用量。

提交問題時提供版本、去識別操作、預期／實際結果、錯誤編號及安全支援ZIP。不要附原始HTTP body、金鑰、內部網址或整份SQLite。本機事件在使用者資料目錄`logs/events.jsonl`，不是Git專案內容。

作者資料在忽略的`publisher.json`填工號／姓名／電話，從`publisher.example.json`建立；UI以popover呈現。不要將私人資料提交公開儲存庫。

## 後續與現況界線

SMTP已選核准郵件伺服器，但尚未實作；必要資訊與預定CLI在[TO-AGENT](TO-AGENT.md#4-下一階段核准-smtp-自動寄信尚未實作)。中央管理、遠端更新、任意shell／檔案、MCP、並行子代理與完整Hermes仍有缺口，見[相容性清單](docs/HERMES-COMPATIBILITY.md)。

公司模型及能力以實測為準，GPT 6 sol是接手開發agent，不是預設產品model ID。舊版交接與獨立lab可從清理前提交`301c3f8`查閱，毋須照舊文案重新開發已完成模組。

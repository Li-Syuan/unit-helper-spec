# 需求與參考來源

查核日期：2026-09-25。本規格是自有產品設計，不是宣稱廠商已有這些 API。

## 需求依據

- [最初分享對話](https://chatgpt.com/share/6ab674fd-2100-83ee-8420-f3f85f145d8d) 已在前次交付讀取。
- 本次使用者確認精簡範圍：單位小幫手、Tkinter、公司已有 AD／後端、Oracle、OpenAI 套件接公司端點、常用查詢＋白話、文字潤飾、TXT/CSV、排程通知、issue、點擊軟體更新。
- 使用者確認本次只交「更新規格包＋AGENTS.md，回公司實作」，不在此製作公司應用程式或可執行原型。
- DSE bot 是使用者對現有助理／流程的稱呼；本包不臆造其獨立產品 API，實際公司呼叫以原碼為準。

## 官方資料

| 參考 | 僅用來核對 |
|---|---|
| [達哥官方介紹](https://dvcbot.net/archives/1) | DaVinci 平台識別與公開能力介紹；不推論公司實例權限 |
| [Python Tkinter](https://docs.python.org/3/library/tkinter.html) | 事件迴圈與 thread 邊界；UI 仍需實測 |
| [OpenAI SDK 文件](https://developers.openai.com/api/docs/libraries) | 套件存在；本案實際方法與公司端點按已成功原碼適配 |
| [Oracle bind variables](https://python-oracledb.readthedocs.io/en/stable/user_guide/bind.html) | 参数值绑定；不把使用者值拼成 SQL |
| [Oracle 19c JSON](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/json-in-oracle-database.html) | CLOB JSON 與 IS JSON 約束的版本相容設計 |
| [Microsoft Windows Authentication](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/windowsauth?view=aspnetcore-10.0) | 既有 AD 身分可整合應用；本案不更換已存在登入 |
| [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) | 開發角色檔及可選模型設定；公司功能依版本和政策 |
| [VS Code subagents](https://code.visualstudio.com/docs/agents/run/subagents) | 可選的開發分工；AGENTS.md 自身不啟動 agent |
| [Ed25519 文件](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) | 簽署／驗證位元組的介面；不是現成桌面更新框架 |

版本號、時限、資料量、表名、API 與更新 layout 是本案設計預設。公司端已存在且合理的實作可在不降低驗收條件下對照沿用，不須照名稱重建所有模組。

## 2026-09-26 範圍增補

使用者選定「Plan＋選項確認」並要求修改規格。v2.1 增加自有桌面／後端流程，沒有宣稱達哥原生支援這些能力；持續自主 Goal 未納入。本次沒有新增廠商能力查核，原官方參考保留原查核日期。

## v2.2 使用情境確認

使用者確認主要痛點為同仁不知道怎麼問助理，常見工作是查資料後做日常報表，結果貼進既有 Excel。依核准計畫補常用工作、引導条件與表格複製；快速回報沿用原 issue。未新增廠商能力宣稱。

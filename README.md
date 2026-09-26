# 單位桌面小幫手｜精簡版規格包

規格版本：2.2｜日期：2026-09-26｜狀態：供公司端實作的規格，非已完成軟體。

本版取代先前「達哥 Multi-Agent 桌面工作台 v1」的開發範圍。以一位開發者可逐步維護為原則：保留 Tkinter，使用既有後端與 AD 登入，接公司助理與 Oracle，提供查詢、文字整理、排程、回饋及更新。

## 帶回公司怎麼用

1. 解壓本包，將內容合併到公司程式庫。既有 `AGENTS.md`、`.github`、API 與登入規則要合併，不能直接覆蓋。
2. 在 VS Code Copilot 選擇公司可用的 GPT 6 sol，貼上 [START-HERE.md](START-HERE.md) 的指令。若可選 custom agent，選 `UnitHelper-Coordinator`。
3. 先盤點舊程式、三項常用查詢及現有登入介面，再依 [IMPLEMENTATION.md](IMPLEMENTATION.md) 實作。缺公司資料時可以完成 Mock 與契約，不能假裝真實接通。
4. Oracle schema 是規格草案，需 DBA 確認。不能直接把未核對的 SQL 或更新包部署到 production。

## 檔案

| 檔案 | 用途 |
|---|---|
| [FULL-SPEC.md](FULL-SPEC.md) | 全部規格的單檔閱讀版，方便交給開發 agent |
| [SPEC.md](SPEC.md) | 產品範圍、畫面、功能與精簡原則 |
| [GUIDED-QUERIES.md](GUIDED-QUERIES.md) | 常用工作、引導查詢、貼入 Excel 與快速回報 |
| [PLAN-AND-CHOICES.md](PLAN-AND-CHOICES.md) | 先規劃、是非／單選／多選、確認執行與原生能力不足時的替代流程 |
| [BACKEND.md](BACKEND.md) | 既有後端整合、AD、Oracle、助理與自有 API |
| [OPERATIONS.md](OPERATIONS.md) | 排程、通知、問題回報、issue 管理 |
| [UPDATES.md](UPDATES.md) | 複製分發、軟體更新、簽章、失敗回復 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | 里程碑、驗收、遷移及待公司補齊項目 |
| [AGENTS.md](AGENTS.md) | 精簡版開發守則，避免重新擴成大型平台 |
| [database/ORACLE.md](database/ORACLE.md) | Oracle 表、欄位、索引與交易設計 |
| [examples/README.md](examples/README.md) | 查詢、排程、issue、設定與版本資訊範例 |
| [.github/agents](.github/agents) | 可選的 Copilot 開發角色；產品 runtime 不需要多代理 |
| [SOURCES.md](SOURCES.md) | 已確認需求與官方參考 |
| [VALIDATION.md](VALIDATION.md) | 本次文件與範例的驗證紀錄 |

## 與舊版的差異

- **保留並加強**：Tkinter、智能助理 API、SQLite 舊資料、既有搜尋與排程、簡單對話。
- **第一版重點**：Plan 預覽與確認、是非／單選／多選、指定單位／人員、三項核准 Oracle 查詢、TXT/CSV 整理、文字潤飾、中央排程通知、issue 回饋、使用者點擊更新。
- **延後**：產品內多 agent、跨人 agent 溝通、Skill 市集、OCR、多文件、信件擷取、Word/Excel 原檔排版編修、Git／shell 工具。
- 既有網路蒐集功能維持可用，不擴建新的爬蟲平台；新功能優先服務公司數據查詢。
- 不要求更換既有後端框架，也不另建一套 AD 帳密驗證。SQLite 不再承擔多人中央資料庫的角色。

新版是獨立交付包；舊包保留作歷史參考，不應將兩版的功能清單合併後全部交給 agent 實作。

## v2.1 新增

依使用者選定的「Plan＋選項確認」增加 UH-11、UH-12；保留一般模式的快速查詢，Plan 模式確認前不查業務資料。沒有原生 Plan／JSON 的助理也可用後端固定表單。新增 AT-16～AT-21，並同步公司 Copilot 指令與契約範例。持續自主 Goal 留待後續。資料夾名稱沿用 unit-helper-spec-v2；v2.1 封裝保留歷史參考。

## v2.2 新增

首版補齊「選工作→填條件→查詢→貼進 Excel」：UH-13 常用工作／引導查詢、UH-14 表格複製，以及 UH-08 快速回報入口。新增 AT-22～AT-27，AGENTS.md／Copilot 指令及契約同步。收藏、固定 Excel 範本產檔與評分儀表板仍延後。最新封裝 Unit-Helper-Spec-v2.2.zip；資料夾沿用 unit-helper-spec-v2。

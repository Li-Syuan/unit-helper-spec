# QA agent

**1.0.0rc5 候選版 · Windows x64 · Python 3.10.4 · WebView2 主介面／Tkinter 備用**

**[查看完整系統架構圖](docs/ARCHITECTURE.md)**：總覽、對話、代理執行、排程、資料與診斷六張圖，並列出現有模組及待接線邊界。

[離線互動架構說明 HTML](docs/ARCHITECTURE.html) 提供圖解、可展開流程、深淺閱讀與列印。GitHub 檔案頁顯示原始碼；下載 ZIP 解壓後，以瀏覽器開啟此檔即可閱讀，不需啟動 App。

填入 **endpoint、Assistant ID、API key**，完成明確啟動的能力檢查後，在同一個輸入框聊天或交辦工作。工作會先補問、產生可修改的計畫，按「確認執行」才開始；成果留在原對話。一位助理即可，不必先建立 Skill 或四位角色。

[Agentic AI 八頁簡報製作指令](docs/AGENTIC-AI-VISUAL-BRIEF.md)：可整份交給產圖 agent，含固定文案、構圖、十分鐘講述提示與能力界線。

[Agent 入門：十分鐘離線簡報](docs/AGENT-INTRO.html)：給非技術同事的概念分享，不含產品介紹。只需攜帶這個 HTML，用 Edge 開啟；支援翻頁、案例演示、講者提示及列印 PDF。

連線失敗時，在「設定助理 → 連線診斷」或原對話的「查看診斷」看失敗階段與下一步；可預覽、複製或另存修復工作單交給 Copilot。查看及匯出不呼叫模型，重測只測明確選定項目。聊天通過即可聊天；AD 僅在部署採用組織登入時接線。

## 日常入口

- **對話**：最近對話、搜尋、置頂與可收合資料夾；聊天、工作計畫、進度和成果在同頁。
- **我的工作**：工作／自動工作／待辦，優先顯示需要處理的項目。
- **設定**：助理啟用、記憶、外觀；進階功能從「更多工具」開啟。Skill 在輸入框旁，通知在頁首鈴鐺。

新對話的一次回覆同時判斷聊天或工作建議，不為普通聊天另加分類請求。辨識及規劃均停用工具；自主工作確認後只在核准範圍內搜尋、依序分工、整理，預設6動作／12模型請求／600秒。未知送出不自動重試，失敗不切示範。排程須成功試跑、人工核對及另外同意；App須開啟或留在系統匣。

![QA agent 工作區](docs/images/workspace-dark.png)

## 安裝與啟動

GitHub **Code → Download ZIP** 含完整69個鎖定wheels，統一放在 `offline-app/packages`。請解壓整個專案；Python3.10.4完整版（含Tk）、WebView2與.NET由部署者提供，不含在wheel包內。

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
start-app.bat
```

安裝驗證雜湊，不連外補件、不覆寫既有環境。已有符合鎖檔的 `.venv` 不必重裝，直接開 `start-app.bat`。`start-tk.bat` 為備用，`create-shortcut.bat` 建桌面捷徑，`diagnose.bat` 檢查環境。詳細見[離線來源](offline-app/README.md)及[開發指南](docs/DEVELOPMENT.md)。

設定助理時先「保存並繼續」。如需搜尋，先讀取並核准唯讀工具，再勾選基本檢查：最多8次合成模型請求（聊天／辨識2、工作格式3、自主決策3）；搜尋另行測一次。各項分開顯示，聊天通過即可聊天；能力不足不假裝全部啟用。金鑰存Windows認證管理員，CA預設系統信任。舊對話不改遠端thread，可選內容建立新版接續對話。

沒有金鑰可用明示的示範助理試「請整理本週工作報告」，或 `qa.bat --demo` 開離線CLI。示範不查即時資料、不啟用真實排程。普通入口不讀 `.env`；選用 Groq 的隔離入口仍為 `start-trial.bat`。

## 接手與驗證

- 給開發 Agent：[TO-AGENT.md](TO-AGENT.md)，環境與現場工作：[COMPANY-HANDOFF.md](COMPANY-HANDOFF.md)。VS Code Copilot的角色、手動prompt及 `/qa-map`、`/qa-fix`、`/qa-review` 精簡開發Skills見[接手入口](TO-AGENT.md#在-vs-code-copilot-接手)；不支援時可明確附上Markdown。
- 使用者：[使用手冊](docs/USER-GUIDE.md)、[資料使用](docs/DATA-USAGE.md)、[工作代理](docs/AGENT-WORK.md)、[CLI](docs/WORKBENCH.md)。
- 開發者：[AGENTS](AGENTS.md)、[架構](docs/PROJECT.md)、[目前驗證結果](docs/VALIDATION.md)。
- 擴充工作代理：[Hermes 開發參考包](doc/hermes/README.md)，含離線官方文件、固定來源與按功能拆分的工作單。這是開發資料，不會自動增加 App 功能。
- rc5 診斷與 WebView 合成旅程已驗證；完整回歸尚有一項既有 Windows 剪貼簿讀取 error 5，未改記通過。複製受阻可另存 Markdown，現場仍須確認。
- `test-company.bat` 做隔離的本機完整檢查與WebView合成旅程；日常改動用 `scripts/test.ps1` quick 或 targeted，不重複跑full。

這是受限自主工作候選版，**尚未完成正式1.0或全部Hermes功能**。實際達哥契約／搜尋來源品質、AD、人工使用性需要現場驗收。SMTP、任意shell／檔案工具、MCP與並行子代理未實作；詳見[Hermes相容性清單](docs/HERMES-COMPATIBILITY.md)。不隨Git提供金鑰、內部設定、Python環境或個人資料。

## 資料夾怎麼看

| 位置 | 用途 |
|---|---|
| `desktop_app/` | 現行介面、服務、正式圖示與程式 |
| `offline-app/packages/` | 唯一正式來源：69個離線wheels |
| `scripts/` | 環境、啟動、診斷、測試與打包工具 |
| `tests/`、`test_support/` | 現有行為驗證與合成資料，不需要交給使用者操作 |
| `docs/`、`company_templates/` | 使用手冊、契約、授權文字與接線範本 |
| `.venv/`、`.runtime/python3104/` | 此開發機的執行環境與基礎Python，不進Git；兩者相依，勿單獨刪除 |
| `artifacts/` | 本機驗證及失敗證據，不進Git；無需隨公司Code ZIP分發 |

舊離線包、獨立lab與重複交接已清理；舊原始碼由Git提交`301c3f8`查閱，不另保留archive副本。給接手Agent的提示統一使用`TO-AGENT.md`。

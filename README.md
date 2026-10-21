# QA agent

**1.0.0rc1 候選版 · Windows x64 · Python 3.10.4 · WebView2 主介面／Tkinter 備用**

## 三個參數開始、原對話續談、可控記憶

使用者在「設定助理」直接填 **endpoint、Assistant ID、API key**，明確測試兩輪後開始聊天。CA預設使用系統信任，不需另外填寫；不關閉TLS驗證。`deployment.json`只是選用的預填方式（[範本](deployment.example.json)），不是啟用前提，不覆寫手動保存的端點。實際設定不提交Git。

主側欄以第一則訊息自動取本機短標題，可搜尋、置頂、重新命名及切回對話，並以可收合資料夾自行分類，保留草稿與閱讀位置。「我的記憶」需預覽確認保存，新對話可選不用；每段對話固定記憶快照。長對話可選內容整理後接續，原文保留。詳見[使用手冊](docs/USER-GUIDE.md)與[部署指南](docs/DEVELOPMENT.md)。**這是候選版；實際達哥、搜尋來源與 AD 驗收完成前，不標示正式 1.0 上線通過。**

帶回現場直接交給開發 Agent：[TO-AGENT.md](TO-AGENT.md)，包含三欄接線、續談與 Skill 驗收，以及尚未實作的 SMTP 自動寄信規格。

## 自建 Skill＋單助理 Plan mode

在「我的 Skills」自行定義方法 → 選助理與條件 → 討論／修改計畫 → 一次確認執行 → 核對成果後另行授權每日排程。可用對話起草或空白表單，支援 Markdown 分享。一位助理即可；真實連線先明確啟動相容性測試，離線示範不需金鑰。詳見 [Skill 操作與格式](docs/SKILLS.md)。

## 交辦工作與 CLI

「交辦工作」讓你說需求、補條件、預覽試跑，再由人核對來源後啟用每日排程。WebView可留在系統匣，CLI與桌面共用服務。雙擊 `start-app.bat`，或執行 `qa.bat --demo` 做一次性離線展示。正式達哥服務仍需現場驗收；請以[最新驗證](docs/VALIDATION.md)為準。詳見[工作台與CLI](docs/WORKBENCH.md)。

## 離線登入展示

新增 `start-demo-login.bat`，admin/admin 只進入即用即棄的離線合成工作區；公司登入仍需 AD 接線並拒絕展示登入。詳見 [登入與App使用資格](docs/LOGIN-AND-APP-ACCESS.md)。

用一個桌面入口與AI 助理對話、整理文字、查詢資料及安排本機排程。本機流程及組織 Assistants 連接器已提供；預設使用明確標示的合成資料，組織部署相容性、AD 與 Oracle 仍需組織資訊及實測。

新版介面與離線兩模式流程驗證結果見 [驗證紀錄](docs/VALIDATION.md)。正式組織連線仍需獨立接線及驗收。

**想先完成每天八點的財經日報：**設定 endpoint／API key、加入現有搜尋助理 ID並核准搜尋工具 → 主對話按「交辦工作」→ 輸入需求、補齊條件 → 預覽 → 確認試跑 → 人工核對日期及來源 → 同意每日傳送並啟用。不必先建立四位角色；App 必須保持開啟或留在系統匣。「連線啟用檢查」列出缺少設定，另可明確讀取助理工具宣告，沒有背景模型呼叫。

搜尋前先到 **設定 → 連線啟用檢查 → 檢查搜尋助理連線**，核對並勾選組織允許的唯讀搜尋工具，明確保存核准。已確認日報／多助理搜尋步驟可呼叫 `/pluginapi`；普通聊天需另外勾選允許，主代理規劃仍停用工具。取得文字或工具回覆不等於新聞已驗證，組織真實搜尋仍需試跑。服務接線及可直接貼入的多代理測試題見 [接手與試跑指令](docs/COMPANY-IMPLEMENTATION.md)。

主畫面提供「一般聊天／整理任務草稿」，沒有夾檔。預設示範模式完全離線；設定 Assistants 協定並明確選取AI 助理後，使用真實組織連接器。建立任務逐步詢問對象、來源、類型與台北執行時間；預覽可編輯，按「確認儲存（不啟用）」才保存。這些草稿不會加入執行排程。切模式或助理會開始新的空白對話；舊歷史保留。

「規劃工作」進入既有分工工作區；批准後由 LangGraph 依序執行，成果與排程沿用既有服務。主畫面組織聊天沿用設定的 Profiles；Groq 仍僅在隔離試用入口使用。

啟動主介面需組織核准的 **Microsoft Edge WebView2 Runtime 與 .NET Framework 4.6.2 以上**；Python wheels 不包含這兩項 Windows 元件。既有 `.venv` 是否需要更新應以 doctor 的 lock 比對為準；依賴未變且比對通過就不用重裝。缺少 WebView2 時可雙擊 **start-tk.bat** 開舊介面；兩者不能同時開同一資料目錄。

![QA agent 深色工作區](docs/images/workspace-dark.png)

本版可在對話失敗後檢查／取回原請求，並由「管理本機資料」刪除成果等內容。每位AI 助理可從團隊卡片準備合成試聊，不自動送出。問題編號及安全日誌可從「說明與關於」匯出。

## 本次待辦與一鍵驗證

「我的待辦」增加真實未完成工作／主對話失敗入口，回來源補齊或查看阻塞與部分結果；個人下一步支援到期／說明搜尋，完成仍由人確認。

帶到公司請用本次完整可攜包，在新目錄安裝後執行 **`test-company.bat`**。它只做本機完整回歸與 WebView2 合成操作，真實公司服務仍須獨立驗收。詳細見 [一鍵操作](docs/ONE-CLICK-TEST.md) 與 [DVC契約核對](docs/DVC-REVIEW.md)。

## 開始使用

新增登入頁（AD 函數待提供）；右上角「作者」可展開姓名／工號／電話小卡。畫面預覽與接線方式見[登入工作單](COMPANY-HANDOFF.md#ad-登入與作者資訊)，不啟用 AD 時保留既有本機入口。公開版本只含空白作者範例。

目前 GitHub **Code → Download ZIP** 也含完整 App 所需的 69 個鎖定 wheels：共用 lab 既有 48 個，只新增缺少的 21 個。不是 Git LFS 指標，也不需要 Release 下載。解壓整個資料夾後直接使用 `install-offline.bat`，詳見 [Code ZIP 離線安裝](offline-app/README.md)。既有 [Release 離線包](https://github.com/Li-Syuan/unit-helper-spec/releases) 保持不變。

**組織索引缺少鎖定版本、或 PowerShell 腳本被限制時：**透過核准管道取得目前 main 的 Code ZIP 或完整正式離線 ZIP，解壓到新資料夾，保留組織原專案與 `.venv`。目前 clone 亦含所需 wheels；不要使用早於本次 Code ZIP 支援的 checkout。關閉舊 App，再於新資料夾的 CMD 執行（換成核准的 Python 路徑）：

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
.venv\Scripts\python.exe scripts\verify.py offline-rebuild
start-app.bat
```

每行成功後才進行下一行；`verify` 已包含一次完整回歸，不再另外跑 full。安裝會驗證完整 69 個 wheels 及鎖檔，不連外、不覆寫既有環境，也不調整 PowerShell 執行政策。詳細步驟與失敗處理見[離線安裝](docs/DEVELOPMENT.md#離線安裝)。

Clone 後，在專案根目錄指定組織核准的 Python **3.10.4** 完整安裝版（含 Tcl/Tk）：

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\Python3104\python.exe'
.\scripts\test.ps1 -Suite full
.\start-app.bat
```

日常開發使用 `.\scripts\test.ps1` 快速檢查；指定範圍及交付完整檢查見[開發指南](docs/DEVELOPMENT.md#測試與交付)，不需每次重跑全部。

已有專案 `.venv` 時，直接雙擊 **start-app.bat**。需要桌面捷徑可雙擊 **create-shortcut.bat**；環境有問題使用 **diagnose.bat**。安裝、離線套件、組織 CA 與診斷詳見 [開發指南](docs/DEVELOPMENT.md)。不隨 Git 提供 Python、虛擬環境、金鑰或使用者資料。

第一次使用：在「對話」選擇「整理任務草稿」，送出需求，再依提示補齊四項條件，編輯預覽並確認儲存。整段流程不需要 API key；任務保持未啟用。想試用原有查詢，進入「規劃與分工」，按 **試查一筆資料 → 送出 → 確認查詢**，即可看到合成表格。

## 用 Groq 試用真正 AI

在專案根目錄的 `.env` 填 `GROQ_API_KEY=你的金鑰`，雙擊 **[start-trial.bat](start-trial.bat)**，再進入「規劃與分工」。此入口選取 Groq 試用助理，可聊天、整理文字及改寫；建議先按「整理一段文字」，核對虛構會議筆記再按 Enter。Groq 試用入口的新版「對話」仍是離線示範；組織入口則依你選定的助理使用組織連接器。

試用固定連線 Groq，資料保存在獨立 `groq-trial` 子目錄，不載入連線設定或歷史。`.env` 為本機明文檔且被 Git 忽略，請勿分享；只使用個人測試資料。免費額度取決於 Groq 帳戶方案，超限會提示，不自動重試或升級。查詢仍是合成資料，正式模式繼續使用原本 start-app.bat。完整步驟見 [試用手冊](docs/USER-GUIDE.md#groq-外部-ai-試用)。

試用日報：輸入「每天早上八點查昨天 A 類數量合計，整理日報」→ 原對話補齊／核對條件 → 勾選每日範圍與資料傳送授權 → 確認啟用。接著按「現在測試一次」即可在原處看結果，不用等隔天。程式計算合計，Groq 整理文字；只用合成查詢，App 必須保持開啟。詳見 [日報操作](docs/USER-GUIDE.md#groq-日報排程)。

## Plan mode 與多助理協作

開啟 start-trial.bat，進入「規劃與分工」，在對話上方選「規劃工作」。輸入：

> 查昨天 A 類數量合計，請分析助理整理，再交覆核助理檢查，最後產生日報。先試跑，成功後我再設每天八點。

主代理會討論需求、追問條件並提出最多六步分工。在「分工進度」核對步驟、負責助理與資料範圍，按一次「確認執行」即授權本版指定資料傳送並依序完成；不會自動批准後續修訂。成功後可按「設為自動工作」，確認持續執行授權後測試、暫停及查看成果。排程使用批准過的版本，不每次重新規劃；異常會暫停並通知。

側欄「助理團隊」可搜尋、查看用途與分工角色、新增AI 助理或選擇主代理。側欄預設圖示＋文字，可收合成窄圖示列；滑鼠停留可查看名稱。服務接線者先處理 API 格式與能力驗證，一般同仁再輸入個人金鑰與 assistant ID，沿用這套工作畫面。

Groq 是同一測試模型的四個隔離角色，並非組織真實多 assistant ID。組織只需沿用流程與畫面，對照成功 API 接上 profiles 的 workflow_call，完成各助理能力與 session 隔離驗收後啟用。未驗證的助理不自動加入流程；目前支援文字、表格與唯讀 RAG，不含生圖或任意工具。

## 目前可以做什麼

- 個人待辦看板：選取對話文字加入、開始／完成、到期日及來源對話。
- 三張常用工作卡片，文字草稿自動保存並可於重開後恢復。
- 多助理對話、歷史與搜尋批次刪除；Enter 送出、Shift+Enter 換行。
- Plan 預覽、修改、批准及選項確認；未批准不執行。
- 單一 TXT／CSV 預覽、文字摘要／改寫、選定資料預覽後轉交。
- 三項合成查詢、表格分頁、CSV／Excel 複製、本機排程與通知。
- 本機問題回報、離線手冊、深淺主題與 Windows DPI 顯示處理。
- 側欄常駐通知與青藍未讀徽章；錯誤使用紅色，新通知可直接查看結果。

開啟後看頁首提示即可體驗。示範回覆不是真正 AI 分析；排程只在程式開啟時執行；問題回報只存本機。此版沒有中央協作、遠端更新或 EXE 打包。

## 找到需要的文件

想在組織試裝 LangChain／LangGraph，可下載 [獨立離線試驗包](experiments/langgraph-lab/README.md)：包含鎖定 wheels、安裝工具及無金鑰範例。它不更動目前 App 的依賴或執行流程。

| 你要做的事 | 入口 |
|---|---|
| 使用桌面、了解資料保存及刪除 | [使用手冊](docs/USER-GUIDE.md)、[資料說明](docs/DATA-USAGE.md) |
| 帶回組織交給 GPT 6 sol／Copilot | [組織接手工作單與可貼指令](COMPANY-HANDOFF.md) |
| 修改或維護專案 | [AGENTS.md](AGENTS.md)、[開發指南](docs/DEVELOPMENT.md) |
| 看架構、功能界線與驗證狀態 | [產品與架構](docs/PROJECT.md)、[驗證紀錄](docs/VALIDATION.md) |

舊規格、候選圖示及視覺稿保存在 [清理前版本 c13e583](https://github.com/Li-Syuan/unit-helper-spec/tree/c13e583)，不再混入目前工作目錄。Git 歷史未改寫；整理減少的是目前檔案，完整 clone 仍包含歷史。

## 成果與AI 助理 Instruction

0.14.0 結果預設先顯示成果、來源與覆核；「與上次比較」呈現同流程版本的可核對合計與筆數差值，並可留下可採用／需修改／無幫助的本機評價。比較不呼叫模型，空資料不當零，數值增減不等於改善或異常。

組織建立分工助理，請從 [Instruction 建立指南](docs/assistant-instructions/README.md) 開始，內含規劃、分析、覆核、彙整四份文件及選用的搜尋 rag 指示。尚未以組織 Luna／多 ID 實測，不保證零幻覺。

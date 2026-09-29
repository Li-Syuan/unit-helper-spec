# LangChain／LangGraph 離線試驗包

這是 **QA agent 以外的獨立試驗資料夾**，讓公司先驗證框架能否安裝及運作。安裝這個資料夾不會讓 QA agent 自動改用 LangGraph，也不會啟用新版對話草稿或公司排程。

## 公司下載後怎麼用

1. 從既有私人 GitHub clone／pull，或使用 **Code → Download ZIP** 並完整解壓縮。
2. 打開 `experiments/langgraph-lab`，保留全部檔案及 `packages` 子資料夾。也可以單獨複製整個資料夾到公司核准位置。
3. 公司先準備 **Windows x64、Python 恰好 3.10.4**。本包不附 Python 安裝程式，不需 Node.js、WebView2 或 API key。
4. 雙擊 **install.bat**，輸入核准的 `python.exe` 完整路徑，例如 `C:\Python3104\python.exe`。不能指向其他版本。脚本只在此資料夾建立 `.venv`，不動 QA agent 根目錄的 `.venv`、PATH 或系統設定。
5. 安裝完成會自動驗證。之後雙擊 **demo.bat** 體驗，或雙擊 **test-lab.bat** 重跑測試。

PowerShell 也可以明確指定直譯器：

```powershell
.\install.ps1 -PythonExe 'C:\Python3104\python.exe'
```

若公司政策不允許執行 PowerShell，請依公司流程處理；也可直接執行同一個固定 Python 入口：

```powershell
& 'C:\Python3104\python.exe' -I -X utf8 .\setup_entry.py
```

不需要修改執行政策或防毒。環境已存在時安裝程式會拒絕覆寫。安裝中途失敗請保留錯誤，讓 agent 檢查；不要改用連外補件或把套件装到正式 App 環境。

## 可以試到什麼

`demo.bat` 使用真正的 LangGraph、LangChain Runnable 與 SQLite checkpoint，業務資料與助理角色都是**固定本機模擬，沒有呼叫 AI**：

```text
固定分工預覽 → 等待確認 → 三筆合成資料 → 分析 → 覆核 → 摘要
                  └ 拒絕：結束，不執行查詢
```

- 尚未確認時不會執行後續節點。輸入 `y` 明確確認，`n` 拒絕。
- 等待確認時按 Enter 離開，再開 `demo.bat`，可從 SQLite 還原待確認進度。
- 結束後再開只顯示成果，不重跑；輸入 `new` 可讓下次開始新範例。
- 正常範例精確合計為 `6.60`。覆核不符就停止，不彙整假成功。
- 資料保存在本資料夾 `data/`，不接 QA agent 的 DB。文字中的命令或路徑只是內容，不會執行或讀取。

這驗證的是框架節點、批准與 checkpoint 能力；不是公司 AI 效果、真人 UI、多助理 ID、任意副作用的 exactly-once、故障自動恢復或排程驗收。範例沒有自動 retry、寄信、shell 或任意 SQL。

## 套件與離線界線

| 主要套件 | 鎖定版本 | 用途 |
|---|---|---|
| langchain | 1.4.3 | Agent 元件與統一介面 |
| langgraph | 1.2.12 | 流程節點、分支與人工確認 |
| langchain-openai | 1.6.6 | 後續相容模型串接；本次只驗證 import |
| langgraph-checkpoint-sqlite | 3.1.1 | 本機持久化 checkpoint |
| openai | 2.54.0 | 保持公司原先 `<3` 範圍 |

完整 **52 個 wheels，13,717,720 bytes（約 13.1 MiB）**，直接隨 GitHub 提供。`requirements.in` 記錄選版範圍，`requirements.lock` 鎖住所有版本及 SHA-256，`bundle-manifest.json` 記錄每個 wheel 的大小、雜湊與授權檔案位置。公司安裝只讀 lock，不重新挑最新版。

安裝前驗證完整性，再以 `--no-index --no-cache-dir --require-hashes` 安裝；缺件、lock 不符或 wheel 損壞即停止，不連外補件。這份包限 Windows x64／CPython 3.10.4，不适用 ARM、Linux、macOS 或其他 Python。

LangSmith、HTTP 工具、tokenizer 等是框架帶入的間接依賴；**下載套件不代表啟用雲端服務**。範例在程序內關閉 tracing、不讀 `.env` 或 API key；自動測試攔截網路操作，需保持零請求。未使用 tokenizer 編碼功能，未提供其可能另外下載的編碼資料；不要把 import 通過當成所有模型功能皆可離線。

套件由官方 PyPI 取得，保留原始 wheel bytes，內含 METADATA／授權檔案，位置見 manifest。LangSmith 與 sqlite-vec 的 wheel 未附獨立授權檔，另於 `licenses/` 保存官方上游授權及來源。授權以各上游原文為準；本資料夾沒有重新授權第三方套件。SHA-256 用來檢查傳輸完整性，不是發布簽章。

官方文件：[LangChain 安裝](https://docs.langchain.com/oss/python/langchain/install)、[LangGraph 安裝](https://docs.langchain.com/oss/python/langgraph/install)、[人工中斷與恢復](https://docs.langchain.com/oss/python/langgraph/interrupts)。

## 給公司 agent 的接手指令

> 先閱讀此 README，在獨立試驗環境執行 test-lab.bat，確認 Python 3.10.4、lock、pip check 及所有測試通過。不要把本資料夾的 requirements.lock 覆蓋專案根目錄鎖檔，也不要直接變更正式 App 環境。
>
> 再取得公司成功 API 範例、正式 endpoint、認證方式、assistant ID 的傳送位置、請求／回覆格式、session 隔離與原生工具副作用說明。langchain-openai 不表示公司 Assistant API 自動相容，不得猜 ID 等於 model。
>
> 先以一個核准助理測試單步呼叫，再依既有 Profiles／WorkflowService 邊界提出整合方案。保留一次明確批准、版本綁定、限定來源、取消、防重及失敗不 fallback。既有任務草稿 CHECK=0 不可直接放寬；App 接入、遷移、公司權限與排程須另行驗證。本試驗未授權新增雲端 tracing、外部資料傳送或啟用公司排程。

測試結果見 [VALIDATION.md](VALIDATION.md)。本機實測會另寫被 Git 忽略的 `verification.local.json`；其中包含本機直譯器路徑，分享前應檢查。

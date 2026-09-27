# 單位桌面小幫手 — 本機可執行版 0.3.0

Windows x64 / **Python 3.10.4** / Tkinter / SQLite / OpenAI SDK。
這個 repo 現在包含可執行程式，不只是 spec。預設示範身分、示範助理與合成資料，**沒有連到公司服務**。

## Clone 後開始

公司已有 Python 3.10.4 時，指定其完整路徑建立獨立環境：

```powershell
git clone https://github.com/Li-Syuan/unit-helper-spec.git
cd unit-helper-spec
.\scripts\setup.ps1 -PythonExe 'C:\公司核准的Python310\python.exe'
.\scripts\test.ps1
.\scripts\run.ps1
```

私人 repo 須使用有權限的 GitHub 帳號。路徑是範例，請替換；不需 activate，不改系統 PATH。PowerShell 腳本若被公司政策阻擋，交由 IT 核准，不要求更改永久 ExecutionPolicy。也可依 [ENVIRONMENT.md](ENVIRONMENT.md) 直接用 Python 指令。

## 可以操作

- 對話歷史、背景請求、取消；公司模式使用 `openai` Chat Completions 相容連接器。
- 一般／先規劃、是非／單選／多選；服務層批准、修訂、防重與取消。
- 單一 TXT／CSV 預覽、文字整理／改寫候選、保留原文、複製／另存。
- 三項合成查詢、條件引導、100 列分頁、全部／當頁選取列複製、CSV 匯出。
- 從成功查詢建立每日／每週本機排程；預覽啟用、立即執行、歷史與站內通知。
- 問題草稿及本機回報編號；沒有送出至管理平台。

示範助理只產生明確標示的示範文字／計數；**接上公司 chatbot 後才有真正 AI 摘要與改寫**。查詢用固定模板與表單，任意 SQL、自然語言自由產生 SQL 均未開放。

排程只在程式開啟時運作。設定／資料預設放 `%LOCALAPPDATA%\UnitHelperLocal`，不寫入 Git checkout；可透過 `UNITHELPER_DATA_DIR` 指定獨立目錄。不同 Windows 使用者自然使用各自目錄；這不是 AD 授權或多租戶安全隔離。

## 公司接手

1. [COMPANY-HANDOFF.md](COMPANY-HANDOFF.md)：六個接線工作包，含位置、內部資訊、驗收與命令。
2. [GPT6-SOL-HANDOFF.md](GPT6-SOL-HANDOFF.md)：可直接貼給公司開發 agent。
3. [LOCAL-SPEC.md](LOCAL-SPEC.md)：**本次已核准的本機實作範圍**。
4. [VALIDATION-LOCAL.md](VALIDATION-LOCAL.md)：實際測試證據與未驗收部分。
5. [docs/USER-GUIDE.md](docs/USER-GUIDE.md)：同仁操作說明。

本次不含 AD 真實登入、Oracle 真實資料、集中管理 API、遠端更新或 EXE 打包。`CompanyIdentity`／`OracleQueries` 未接線時直接拒絕使用。

## 規格歷史

`SPEC.md`、`BACKEND.md`、`OPERATIONS.md`、`UPDATES.md`、`IMPLEMENTATION.md`、`FULL-SPEC.md` 與 `Unit-Helper-Spec-v2.2.zip` 保留原規劃。其中中央排程、管理平台及更新系統是後續階段，不是 0.3.0 已完成內容。
`MANIFEST.sha256` 對應目前 repo 的交付檔；歷史 ZIP 內的 manifest 仍對應該 ZIP 的 v2.2 內容。

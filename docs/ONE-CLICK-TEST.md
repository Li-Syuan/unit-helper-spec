## GitHub Code ZIP 離線入口（2026-10-01）

公司允許 GitHub Code → Download ZIP 時，下載目前 main 並解壓**整個資料夾**到新位置；不需要 Release。根目錄 `install-offline.bat` 會驗證並共用 lab 的 48 個 wheels、加入 `offline-app/packages` 的 21 個，依 App 自己的 69 套件 lock 安裝；不使用 lab lock。不連網補件、不覆蓋既有 `.venv`，既有 wheelhouse 若失效仍停止。最短步驟及前置條件見 [Code ZIP 說明](../offline-app/README.md)。

## 離線登入展示

安裝後執行 `start-demo-login.bat`，帳密 admin/admin 只開暫存合成資料，退出後清除；公司連線與金鑰設定被禁用，不能混用公司設定或外部試用。公司AD入口與人事使用資格見 [登入說明](LOGIN-AND-APP-ACCESS.md)。

# 帶到公司的一鍵驗證

保留公司原專案、已修改 adapter、設定及環境。把完整離線包解壓到新資料夾，先關閉舊 App。

1. 公司提供 **Python 恰好 3.10.4 x64 完整安裝（含 Tk）**、Edge WebView2 Runtime、.NET Framework 4.6.2 以上，以及核准的正式 69 wheels。
2. CMD 執行 `install-offline.bat "C:\approved\Python3104\python.exe"`。已存在環境拒絕覆寫；缺件、雜湊或 lock 不符會停止，不連外補件。
3. 在新專案根目錄執行 **`test-company.bat`**：Python 語法 → doctor／pip／精確 lock → 完整離線回歸 → 真實 WebView2 合成旅程 → 原生展示登入／有草稿登出生命週期。首個失敗就停止，非零結束碼；本機通過不等於公司 API 通過。此命令不讀金鑰、不啟用日報排程、不呼叫內網。
4. 離線展示用 `start-demo-login.bat`，admin/admin 只開暫存合成資料。公司既有程式差異需先比對合併。
5. 正式使用先由公司維護者接好 AD 與人事 App 使用資格閘門，再設 identity_mode=company；未接線或未核准就停止，不能回退展示。
6. 使用 `start-app.bat` 完成公司登入，才在該身分設定核准 DVC endpoint／Assistant ID／key／CA；metadata、普通聊天及核准搜尋分開驗收，最後核對來源與已知答案。

`test-company.bat quick` 僅核心離線測試；`test-company.bat ui` WebView 與原生展示登入生命週期操作。不要把 quick 或 ui 說成 full。

報告：`artifacts/company-test/latest.json`、`artifacts/testing/latest.json`、`artifacts/web-smoke/result-workspace.json`、`artifacts/login-launch/result.json`。合成畫面在 `artifacts/web-smoke/`。可能包含本機路徑，分享前去識別。

## 公司搜尋助理另行驗收

`test-company.bat company-info` 只顯示未驗證界線，結束碼 2。預設不載入公司 hooks，也不讀使用者 profiles。先完成 AD／App 使用資格並登入公司模式，再在 UI 設定現有搜尋助理，分別驗 metadata、普通聊天，再核對並保存唯讀工具核准；未確認服務副作用前不執行 live。

在公司已核准真實測試後，可使用既有獨立入口（替換本機設定檔與 profile 識別，不填 API key）：

```bat
.venv\Scripts\python.exe scripts\check-assistants.py --live --profiles "C:\approved\assistants.json" --profile "LOCAL_PROFILE_ID" --output artifacts\company-chat.json
.venv\Scripts\python.exe scripts\check-assistants.py --live --search --profiles "C:\approved\assistants.json" --profile "LOCAL_PROFILE_ID" --output artifacts\company-search.json
```

上述會呼叫真實 Assistants 並可能建立遠端 thread／run、消耗額度；本次沒有執行。不要用它測有寫入副作用的工具。搜尋還需人工核對日期、來源、權限及事實，metadata 成功不代表搜尋成功。不要啟用財經日報排程作驗收替代。

AD／Oracle／舊資料與多 ID 隔離仍由公司填可信 hook、核准能力後按 `docs/ADAPTER-TEST-KIT.md` 獨立驗收，缺 hook 保持 `not_tested`。

## 我的待辦

「需要我處理」只讀跨對話待確認計畫、條件、未完成工作及主對話最近未解決請求。回來源補齊／核對，或看部分結果與阻塞；不在待辦頁直接派發。失敗歷史最多 50 筆，各流程確認與取消保障沿用原入口。主對話若輸入框尚有文字，來源切換會拒絕，以保留未送出內容。

「我的下一步」由人記錄具體行動、阻塞及完成紀錄，支援今天／逾期、未完成、全部及已完成篩選；台北日期、到期排序、標題及說明搜尋。待辦狀態不標記 AI 工作成功。來源刪除時保留副本，明示失效。Tk 備用維持原看板，工作成果可從活動紀錄開啟。

[新版待辦實際畫面（合成資料）](images/todo-inbox-dark.png)。

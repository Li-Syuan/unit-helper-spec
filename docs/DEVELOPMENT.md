## 本機問題紀錄

預設 `%LOCALAPPDATA%\UnitHelperLocal\logs\events.jsonl`（有 UNITHELPER_DATA_DIR 時跟隨指定目錄），單檔1MiB、最多3份輪替。只記安全代碼與專案檔名／行號；不記raw exception、對話、API key、URL或HTTP body。UI錯誤會給問題編號；網路階段與UI事件可能是不同編號，按時間相鄰事件比對。

「說明與關於 → 匯出除錯包」使用白名單再次過濾。沒有GUI時可執行 `.venv\Scripts\python.exe scripts/export-support.py --output QA-agent-support.zip`；目的檔須尚不存在，不讀公司服務或任意資料檔。這份包只供錯誤定位，不替代doctor與公司驗收；分享前依公司規定審查。

LangGraph正式依賴已在69個wheels中。更新原始碼不會更新已有venv；doctor lock比對通過則不需重裝，不通過請用完整正式包建立新環境，比對公司修改後再切换。不要讓agent反覆單獨安裝缺件，或用lab lock降版。

# 0.16.0 依賴與恢復驗證

正式 App 加入 LangGraph 與 SQLite checkpoint，requirements.lock 是 App 的完整 69 套件鎖檔，不能用獨立 lab lock 覆蓋。既有 .venv 升級前請關閉 App，再以該環境 Python 執行 `-m pip install -r requirements.lock`；公司離線使用核對過的完整 wheelhouse 與 `--no-index`，不連外補件。公司首次建立優先使用 install-offline.bat，不覆蓋既有環境。

新增回歸：tests.test_graph_runner、tests.test_assistants_gateway、tests.test_assistants_profiles、tests.test_company_journey、tests.test_dialogue_concurrency。完整回歸使用 `scripts/test.ps1 -Suite full`；日常依下方分層測試規則選測。scripts/web-smoke.py 使用臨時資料及實際 SDK MockTransport，涵蓋主畫面公司模式、多輪與小視窗；不代表公司真實 API 或人工 IME 驗收。

mock-assistants.py 只綁定 127.0.0.1，無真實金鑰。正式 App 不允許 HTTP endpoint；單元測試透過注入 client 驗證，不能用公開服務替換 mock。SDK 的公開 Assistants 棄用提示不代表公司私有平台已公告停用。


# WebView 開發與部署

直接與間接依賴共 69 個鎖定套件，精確版本以 requirements.lock 為準。主入口 `python -m desktop_app`；備用 `python -m desktop_app --ui tk`。新主畫面兩模式預設離線示範，可明確選公司助理；進階介面沿用原服務。

Windows需 WebView2 Runtime、.NET Framework 4.6.2以上，依公司流程提供；wheels不包含Windows元件。doctor新增唯讀偵測。缺元件時明示錯誤並提供Tk入口，不降回IE、不改TLS或防毒設定。

已有本機環境更新：`.venv/Scripts/python.exe -m pip install -r requirements.lock`；有核准CA依下方既有方式設定。離線先執行 `scripts/offline_bundle.py verify --directory wheelhouse`，通過後以 `--no-index --no-deps --find-links wheelhouse -r requirements.lock` 安裝。新機優先用install-offline.bat建乾淨環境，不能覆寫既有venv。

prepare-offline現只對沒有wheel發行的固定proxy_tools==0.1.0建立純Python wheel，其餘使用Windows相容binary wheels；全部納入manifest及lock指紋，安裝不編譯、不連外補件。

驗證：`.\scripts\test.ps1 -Suite targeted -Tests tests.test_dialogue,tests.test_web`；`python scripts/web-smoke.py`用暫存合成資料及明示mock回覆操作真正WebView2，透過CapturePreview存畫面，**不呼叫模型、不讀使用者資料**。完整回歸使用 `scripts/test.ps1 -Suite full`；不要求每次 UI 修改都重跑。真IME、人工使用性與公司多ID另驗收。

# 開發與部署指南

QA agent；版本以 README 為準。以下命令從專案根目錄執行；公司接線工作見 [接手工作單](../COMPANY-HANDOFF.md)，產品行為見 [PROJECT](PROJECT.md)。

## 個人 Groq 試用

start-trial.bat 使用同一 .venv，沒有新依賴或第二個環境。正常入口不變。專案 .env 僅填 GROQ_API_KEY，不提交 Git。`scripts/check-trial.py` 預設只檢查格式，不連外；明確加 `--live` 才會以合成短句測試 Groq，僅輸出安全狀態，不列金鑰／回覆內容。`--live --reports` 改跑最多三筆請求，檢查條件解析、追問及批准後日報；只用暫存資料庫、不改使用者排程，沒有自動重試。請在已確認帳戶方案後操作。

```powershell
.venv\Scripts\python.exe scripts/check-trial.py
.venv\Scripts\python.exe scripts/check-trial.py --live
.venv\Scripts\python.exe scripts/check-trial.py --live --reports
.\scripts\test.ps1 -Suite targeted -Tests tests.test_trial
.\scripts\test.ps1 -Suite targeted -Tests tests.test_report_engine,tests.test_report_views
```

HTTPX 使用 Python 系統預設信任庫（Windows ROOT／CA），保留主機名與憑證驗證；不略過錯誤、不新增憑證或防毒排除。正式公司 CA 設定仍遵循原 adapter 契約。變更試用目的地／模型時須修訂連線版本，舊對話不能默默改送。

## 環境與啟動

Windows x64、**Python 恰好 3.10.4** 完整安裝版，保留 Tcl/Tk 與 pip。使用公司核准直譯器；需要下載時使用 [Python 官方完整安裝程式](https://www.python.org/downloads/release/python-3104/)，不更改系統預設 Python 或 PATH。

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe'
.\scripts\test.ps1 -Suite full
.\scripts\run.ps1
```

setup 建立專屬 `.venv`，拒絕覆寫既有環境，不借用其他專案的 site-packages。鎖檔含直接／間接依賴及 pip、setuptools，共 69 個套件；用 requirements.lock 安裝，requirements.in 只是主要套件清單。更動依賴須更新 lock 並另建乾淨環境驗證；本次離線交付未改依賴，已另建臨時環境驗證完整套件包。

```powershell
# 額外乾淨環境，名稱須尚不存在
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -Environment .venv-verify
.\scripts\test.ps1 -Suite full -Environment .venv-verify
# 使用公司可信 PEM，不停用 TLS
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -CaBundle 'C:\approved\company-ca.pem'
```

套件索引／代理依公司核准設定。CA 選項只影響本次安裝。不要使用 trusted-host 或 verify=False。PowerShell 腳本受限時交 IT 核准；不修改執行政策。已有可用直譯器，也可逐條執行並檢查 exit code：

```powershell
& 'C:\approved\Python3104\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe scripts/test_runner.py --suite full
.\.venv\Scripts\python.exe -m desktop_app
```

公司連線設定與資料放 `%LOCALAPPDATA%\UnitHelperLocal`；測試可用 `UNITHELPER_DATA_DIR` 指定隔離位置。API key 存 Windows keyring，不能寫入 Git。專案搬家時重建虛擬環境，使用者資料不必搬進專案。

## 離線安裝

### 公司已取得完整正式 ZIP（建議）

適用於核准索引缺少 Bleach／OpenAI／LangGraph 鎖定版本，或 PowerShell 拒絕執行腳本的環境。不要單獨降版某個套件，也不要把獨立 lab 的 52 套件 lock 套到 App。

1. 由核准管道帶入正式 ZIP，確認來源及交付 SHA-256；完整解壓到**新的資料夾**。保留公司既有修改與 `.venv`，不要直接覆蓋。
2. 關閉舊 App。準備公司核准的 Python **恰好 3.10.4 x64** 完整安裝（含 Tk）、WebView2 與 .NET。這些系統元件不含在 wheel 包內。
3. 在新資料夾開啟 CMD，逐行執行，每行成功才繼續：

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
.venv\Scripts\python.exe scripts\verify.py offline-rebuild
start-app.bat
```

BAT 直接呼叫固定 Python 腳本，不需要 PowerShell。亦可用同一核准 Python 執行 `scripts\install-offline.py --offline-bundle wheelhouse`。路徑以雙引號包住；不需要啟用虛擬環境。`verify` 已包含完整回歸及環境檢查，不必再跑 full。安裝及本機測試不呼叫公司模型。

安裝先驗證根目錄 lock 與全部 69 個 wheels，再新建 `.venv`；使用 `--isolated --no-index --no-deps --no-cache-dir`，完成後執行 doctor、pip check 及精確 lock 比對。已有目標環境一律拒絕覆寫；安裝失敗會保留本次半成品供檢查，不會連外補件或自動刪除。修復套件包後，改在新解壓資料夾重試。安全摘要覆寫 `artifacts/installation/latest.json`。

完整測試先檢查環境，再探索測試。環境不符時，報告保留 `commands`，測試為 `not_run`，探索／選取數為 null；不能標記 full 通過。`pip check` 單独成功不代表 lock 已齊全，啟動器 `--check` 也不是完整依賴驗收。

不同專案副本預設仍使用 `%LOCALAPPDATA%\UnitHelperLocal`，務必先關閉舊 App，避免雙跑；安裝器不搬移或清除使用者資料。公司已修改的 adapter 應先由公司 agent 比對合併，不直接以交付包覆蓋。完整測試報告可能含機器路徑，分享前需去識別。

### 自行準備／沿用 PowerShell 安裝

在可信且有網路的準備機，以合格 `.venv` 下載現有鎖檔的完整 wheelhouse：

```powershell
.\scripts\prepare-offline.ps1 -Destination wheelhouse-company
# 若需要，可加 -CaBundle 'C:\approved\company-ca.pem'
```

目錄必須不存在。輸出全部 wheel 與 manifest.json，包含 CPython 3.10／Windows x64 目標、名稱／版本、檔案 SHA-256 與 requirements.lock 指紋。失敗的半成品不能使用，請用新目錄重試；雜湊是完整性檢查，並非發布者簽章。

經公司核准管道帶入同一版本專案、完整套件包及 Python 3.10.4 完整安裝程式，再執行：

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -Environment .venv -OfflineBundle 'D:\transfer\wheelhouse-company'
.\scripts\test.ps1 -Suite full
```

安裝前驗證檔案集合、套件版本、雜湊與 lock 指紋；缺件、損壞、額外檔案或版本不符即停止。只用 `--no-index` 本機安裝，不連外補件、不覆寫既有環境。套件包被 Git 忽略。Oracle 驅動、內部憑證與公司服務不是離線包內容。

## 捷徑與日常啟動

雙擊根目錄 start-app.bat 啟動；create-shortcut.bat 在 Windows 回報的目前使用者桌面建立 QA agent 捷徑，支援重新導向的桌面。捷徑直接執行專案 `.venv/Scripts/pythonw.exe -m desktop_app`，設定工作目錄及正式 ICO，不留下命令列視窗。

建立前檢查直譯器、Tk、PNG／ICO；缺少資源時不覆蓋捷徑。只更新本工具建立的項目，不覆蓋其他程式的同名捷徑。專案搬家並重建環境後，重跑捷徑工具即可；不搬移或刪除個人資料。

```powershell
.\start-app.bat --check
powershell.exe -NoProfile -File .\scripts\create-shortcut.ps1 -Destination 'C:\已存在的測試資料夾'
```

## 診斷與防毒排查

雙擊 diagnose.bat，或執行固定診斷腳本：

```powershell
.\.venv\Scripts\python.exe scripts/doctor.py --human --output artifacts/diagnostics/readiness.json
.\.venv\Scripts\python.exe scripts/doctor.py --config config.local.json --data-dir artifacts/diagnostic-data
.\.venv\Scripts\python.exe scripts/display-check.py --output artifacts/diagnostics/display.json
```

doctor 檢查 Windows、Python、Tk、依賴／lock、設定、必要變數是否存在、CA 及資料目錄臨時寫入；不讀取使用者 SQLite、不連網。分享報告只含白名單狀態、安全代碼及版本，不含金鑰、帳號、路徑、內部網址或原始錯誤。顯示診斷只收集 DPI、字型、Tk scaling 與視窗尺寸。兩者通過均不等於公司服務已驗收。

開發與測試採固定檔案和直接參數，不使用編碼 PowerShell 命令、巢狀 Shell 或非必要程序。Norton 成效目前仍為 **未能確認**；測試通過不能證明防毒不再警告。

若警告再次出現，記錄操作時間、程式路徑及 Norton 警示 ID，對照安全性歷程，停止重跑被阻擋的同一操作並交本人／IT 審核來源；其餘獨立工作可繼續。不關閉防毒、不增設排除、不改執行政策，也不預設是誤報。私有歷程留在 artifacts 或公司核准位置，不推 Git。

## 測試與交付

正式命令使用專案 Python 3.10.4。日常按修改範圍選一次適當檢查，不依序跑完所有入口：

| 修改範圍 | 要執行的檢查 |
|---|---|
| 純文件 | 本機連結及相關入口引用 |
| 文字／配色 | 受影響 targeted 測試及畫面 |
| 一般功能 | 受影響 targeted 測試及 quick 核心回歸 |
| 核心服務／遷移／依賴／發布 | full；需保存交付證據時改用 verify 一次 |
| WebView UI／bridge 或介面發布驗收 | 另外執行 web-smoke；不是每次修改的常駐步驟 |

```powershell
# 日常：非 GUI 核心離線檢查，不開 GUI、不連公司服務
.\scripts\test.ps1
# 指定模組，也可指定 TestCase 或個別 test 方法
.\scripts\test.ps1 -Suite targeted -Tests tests.test_appearance
# PowerShell 內以陣列傳入多個模組／案例
.\scripts\test.ps1 -Suite targeted -Tests tests.test_appearance,tests.test_web_palette
# 完整回歸及 doctor、pip check、lock 檢查
.\scripts\test.ps1 -Suite full
```

三種入口共用 `scripts/test_runner.py`，`tests/suites.json` 按 TestCase class 明確分類。新增模組或 class 必須分類，否則停止；選到 GUI 的 targeted 仍會開 GUI。GUI 串行，案例使用獨立資料。新增測試須對應具體行為或已發現問題，相同條件與斷言可合併；不為文案、按鈕或版本機械地新增一份測試，也不以數量持續增加當驗收條件。批准、防重、取消晚到結果、隔離、工具授權、遷移及刪除等保障不能移除。

執行時即時顯示進度，日常報告覆寫被忽略的 `artifacts/testing/latest.json`，列出所選範圍、數量、總耗時及最慢案例。quick 的本機改善目標為 60 秒內，實際耗時以報告為準。空集合、載入錯誤、失敗及非預期 skip 均不可算通過；quick／targeted 通過不能標為完整回歸。既有檢查通過且沒有新修改、失敗或未解疑慮時，不重跑同一範圍。

正式交付需要保存證據時，使用下列命令取代 `test.ps1 -Suite full`，不要兩者連跑：

```powershell
# 同一執行器完成 full 一次，保存環境與回歸證據
.\.venv\Scripts\python.exe scripts/verify.py development
# 檢查追蹤內容；修改完成且審核後才使用 --write 更新
.\.venv\Scripts\python.exe scripts/manifest.py
```

verify 拒絕空測試、非預期 skip、非零 exit code 或 freeze 與 lock 不符。正式證據存 docs/validation，保留時間與實際範圍，區分 mock、本機真實與公司真實驗證。正式交付才更新 [驗證摘要](VALIDATION.md)、[產品狀態](PROJECT.md) 與接手文件；日常選測不建立新的歷史材料。公司／人工 GUI／IME 等未測項目仍記 not_tested。

若 Windows 剪貼簿實測出現 `OpenClipboard failed`（舊版統一顯示 `clipboard busy`），保留 Windows 錯誤碼。先在互動桌面確認一般應用可複製／貼上，關閉正在占用剪貼簿的操作，再執行下列單項。錯誤碼 5 表示存取遭拒，不能因此直接判定占用、鎖屏或防毒誤報。不讀取／分享現有剪貼簿私有內容，不改防毒或存取政策。

```powershell
.\scripts\test.ps1 -Suite targeted -Tests tests.test_dialogs.DialogTests.test_long_message_theme_copy_and_close_without_mutation
```

單項成功只代表該項恢復；依實際修改範圍決定是否加跑其他檢查，不因單項重測自動再跑 full。正式交付或核心變更才用 `scripts/verify.py development` 更新完整證據。失敗仍保留非零結果，不能改用 mock、Tcl 快取、skip 或刪除測試。其他獨立檢查可繼續。

本機只保留日常使用的 `.venv`。乾淨重建及離線驗證環境完成驗證、保存紀錄並確認沒有程序使用後即清除；需要再次驗證時依鎖檔重建，不長期累積帶版本的環境。既有驗證 JSON 保留歷史實測結果，不代表對應環境仍存在。

開發機直譯器曾因 Windows Installer 問題，從官方 3.10.4 發行 MSI 解出至被忽略的 `.runtime/python3104`，目前 `.venv/pyvenv.cfg` 仍依賴該路徑，不能當作暫存刪除。這不是公司部署方式，公司仍用核准的完整安裝程式。

## 圖示來源與重建

正式 A 圖示原始 PNG、七尺寸 PNG／ICO 與 [生成提示詞](../desktop_app/assets/GENERATION-PROMPT.txt) 隨專案保留。候選及比較素材僅存 Git 歷史。操作線條图示由原始座標取樣，保留深淺及各倍率資源，不於執行期連網或生圖。

```powershell
powershell.exe -NoProfile -File scripts/export-icon.ps1
powershell.exe -NoProfile -File scripts/export-icon.ps1 -Source desktop_app/assets/light/qa-agent.png -Destination desktop_app/assets/light
.\.venv\Scripts\python.exe scripts/build-ui-icons.py
```

重建素材後檢查真實小尺寸與 DPI 画面，再更新 manifest。素材載入依程式位置，不依工作目錄；缺圖片仍需能操作。應用內與 Windows 工作列的實際外觀分開驗收。


## 多助理合成驗證

`.\scripts\test.ps1 -Suite targeted -Tests tests.test_workflows,tests.test_workflow_profiles,tests.test_workflow_ui` 不使用真實 API。`.venv/Scripts/python.exe scripts/check-workflows.py` 預設 not_tested、零請求；加 `--live` 才對 Groq 發出最多四次合成請求（規劃、分析、覆核、彙整），暫存資料庫結束即清除，不啟用使用者排程。可加 `--output artifacts/workflow-live.json` 保存白名單結果。公司驗收必須獨立完成，不能把此結果改名當公司證據。

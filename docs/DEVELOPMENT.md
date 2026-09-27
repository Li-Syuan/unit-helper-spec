# 開發與部署指南

QA agent 0.12.0。以下命令從專案根目錄執行；公司接線工作見 [接手工作單](../COMPANY-HANDOFF.md)，產品行為見 [PROJECT](PROJECT.md)。

## 個人 Groq 試用

start-trial.bat 使用同一 .venv，沒有新依賴或第二個環境。正常入口不變。專案 .env 僅填 GROQ_API_KEY，不提交 Git。`scripts/check-trial.py` 預設只檢查格式，不連外；明確加 `--live` 才會以合成短句測試 Groq，僅輸出安全狀態，不列金鑰／回覆內容。`--live --reports` 改跑最多三筆請求，檢查條件解析、追問及批准後日報；只用暫存資料庫、不改使用者排程，沒有自動重試。請在已確認帳戶方案後操作。

```powershell
.venv\Scripts\python.exe scripts/check-trial.py
.venv\Scripts\python.exe scripts/check-trial.py --live
.venv\Scripts\python.exe scripts/check-trial.py --live --reports
.venv\Scripts\python.exe -m unittest tests.test_trial -v
.venv\Scripts\python.exe -m unittest tests.test_report_engine tests.test_report_views -v
```

HTTPX 使用 Python 系統預設信任庫（Windows ROOT／CA），保留主機名與憑證驗證；不略過錯誤、不新增憑證或防毒排除。正式公司 CA 設定仍遵循原 adapter 契約。變更試用目的地／模型時須修訂連線版本，舊對話不能默默改送。

## 環境與啟動

Windows x64、**Python 恰好 3.10.4** 完整安裝版，保留 Tcl/Tk 與 pip。使用公司核准直譯器；需要下載時使用 [Python 官方完整安裝程式](https://www.python.org/downloads/release/python-3104/)，不更改系統預設 Python 或 PATH。

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe'
.\scripts\test.ps1
.\scripts\run.ps1
```

setup 建立專屬 `.venv`，拒絕覆寫既有環境，不借用其他專案的 site-packages。鎖檔含直接／間接依賴及 pip、setuptools，共 29 個套件；用 requirements.lock 安裝，requirements.in 只是主要套件清單。更動依賴須更新 lock 並另建乾淨環境驗證；本次整理沒有更動依賴或重建環境。

```powershell
# 額外乾淨環境，名稱須尚不存在
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -Environment .venv-verify
.\scripts\test.ps1 -Environment .venv-verify
# 使用公司可信 PEM，不停用 TLS
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -CaBundle 'C:\approved\company-ca.pem'
```

套件索引／代理依公司核准設定。CA 選項只影響本次安裝。不要使用 trusted-host 或 verify=False。PowerShell 腳本受限時交 IT 核准；不修改執行政策。已有可用直譯器，也可逐條執行並檢查 exit code：

```powershell
& 'C:\approved\Python3104\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/doctor.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m desktop_app
```

公司連線設定與資料放 `%LOCALAPPDATA%\UnitHelperLocal`；測試可用 `UNITHELPER_DATA_DIR` 指定隔離位置。API key 存 Windows keyring，不能寫入 Git。專案搬家時重建虛擬環境，使用者資料不必搬進專案。

## 離線安裝

在可信且有網路的準備機，以合格 `.venv` 下載現有鎖檔的完整 wheelhouse：

```powershell
.\scripts\prepare-offline.ps1 -Destination wheelhouse-company
# 若需要，可加 -CaBundle 'C:\approved\company-ca.pem'
```

目錄必須不存在。輸出全部 wheel 與 manifest.json，包含 CPython 3.10／Windows x64 目標、名稱／版本、檔案 SHA-256 與 requirements.lock 指紋。失敗的半成品不能使用，請用新目錄重試；雜湊是完整性檢查，並非發布者簽章。

經公司核准管道帶入同一版本專案、完整套件包及 Python 3.10.4 完整安裝程式，再執行：

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\approved\Python3104\python.exe' -Environment .venv -OfflineBundle 'D:\transfer\wheelhouse-company'
.\scripts\test.ps1
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

```powershell
.\scripts\test.ps1
# 保存 doctor、pip check、freeze 與完整回歸證據
.\.venv\Scripts\python.exe scripts/verify.py development
# 檢查追蹤內容；修改完成且審核後才使用 --write 更新
.\.venv\Scripts\python.exe scripts/manifest.py
```

verify 拒絕 0 tests、skip、非零 exit code 或 freeze 與 lock 不符。證據存 docs/validation，需保留版本／時間並區分 mock、本機真實與公司真實驗證。更新後維護 [驗證摘要](VALIDATION.md)、[產品狀態](PROJECT.md) 與接手文件；不要逐版複製整段歷史到每份文件。

若 Windows 剪貼簿實測出現 `clipboard busy`，先在互動桌面確認一般應用可複製／貼上，關閉正在占用剪貼簿的操作，再執行下列單項。這個訊息也可能是存取遭拒，不能只靠錯誤文字判定占用或防毒誤報。不讀取／分享現有剪貼簿私有內容，不改防毒或存取政策。

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dialogs.DialogTests.test_long_message_theme_copy_and_close_without_mutation -v
```

單項成功後再跑 `scripts/verify.py development` 更新完整證據；失敗仍保留非零結果，不能改用 mock、Tcl 快取、skip 或刪除測試。其他独立檢查可繼續。

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

`.venv/Scripts/python.exe -m unittest tests.test_workflows tests.test_workflow_profiles tests.test_workflow_ui -v` 不使用真實 API。`.venv/Scripts/python.exe scripts/check-workflows.py` 預設 not_tested、零請求；加 `--live` 才對 Groq 發出最多四次合成請求（規劃、分析、覆核、彙整），暫存資料庫結束即清除，不啟用使用者排程。可加 `--output artifacts/workflow-live.json` 保存白名單結果。公司驗收必須獨立完成，不能把此結果改名當公司證據。

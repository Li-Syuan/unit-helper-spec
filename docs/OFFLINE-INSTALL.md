# 公司離線安裝與環境診斷

所有環境使用 Windows x64、Python **3.10.4 完整安裝版（含 Tcl/Tk）**。這裡不安裝或修改系統 Python，也不修改 PATH。

PowerShell 若受公司政策限制，請由 IT 核准腳本；不需變更永久 ExecutionPolicy。

## 有網路的準備機

在專案根目錄，以已驗證的 `.venv` 建立套件包：

```powershell
.\scripts\prepare-offline.ps1 -Destination wheelhouse-v060
# 公司核准 CA 時，可附加 -CaBundle 'C:\approved\company-ca.pem'
```

輸出 `wheelhouse-v060/`，含鎖檔要求的全部 wheel 及 `manifest.json`。命令拒絕覆寫既有目錄；失敗的半成品不視為可用套件包。使用新目錄重試，例如 `-Destination wheelhouse/retry`，並指定該子目錄安裝。

包的目標為 CPython 3.10／Windows x64；來源使用 pip 既有的核准索引設定，TLS 不停用。`manifest.json` 記錄每個 wheel 的 SHA-256、套件名稱與版本，以及原始 `requirements.lock` 指紋。

將 **同一 Git 版本的專案、整個 wheelhouse-v060、公司核准的 Python 3.10.4 安裝程式**帶至公司。套件包不提交 Git；經公司核准管道傳遞。雜湊用於偵測損壞與版本不符，**不是發布者簽章**；請從可信準備機取得整包。

## 離線機重建

```powershell
.\scripts\setup.ps1 `
  -PythonExe 'C:\approved\Python3104\python.exe' `
  -Environment .venv -OfflineBundle 'D:\transfer\wheelhouse-v060'
```

建立環境前先檢查檔案集合、名稱、套件版本、雜湊與鎖檔指紋；任何缺件、損壞、不符或額外檔案都停止。安裝使用本機 wheel、`--no-index`，不連外補件。已存在的環境不覆寫；驗證用可改為 `.venv-offline060`。

安裝完成執行依賴檢查與環境診斷。若環境建立成功但本機公司設定缺少金鑰，診斷仍會明確失敗，請依各項結果補齊；不得將公司設定失敗解讀成套件安裝失敗後偷偷切示範模式。

## 一鍵診斷

雙擊 `diagnose.bat`，結果保存至忽略的 `artifacts/diagnostics/readiness.json`。也可指定設定／資料目錄：

```powershell
.venv\Scripts\python.exe scripts/doctor.py --human --output artifacts/diagnostics/readiness.json
.venv\Scripts\python.exe scripts/doctor.py --config config.local.json --data-dir artifacts/diagnostic-data
```

診斷無網路請求，檢查 Python、架構、Windows、Tk、鎖定套件、設定、必要環境變數是否有值、CA 能否載入、資料目錄能否建立暫存檔。只測寫入臨時檔，不開啟使用者 SQLite。

分享報告採固定欄位，只含檢查名稱、狀態、安全代碼及版本／架構，不含環境變數名稱或值、內部網址、帳號、路徑、對話或錯誤原文。公司 chatbot、AD、Oracle、Excel 永遠標記 `not_tested`，需由公司實測。

## 驗證命令

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_environment.py -v
.venv-offline060\Scripts\python.exe -m pip check
.venv-offline060\Scripts\python.exe -m unittest discover -s tests -v
```

離線安裝不涵蓋 Python 安裝程式、Oracle 驅動、公司內部憑證及公司服務驗收。這些必須經公司核准後另行提供。

0.6.0 實際包含 29 個 wheel，鎖檔 SHA-256：8a7c356f8c4f2dd1f8dd235e5757e1cc1ed53d1c3bb5647bcfd2e39fa7860d5c。已於全新 .venv-offline060 以 --no-index 安裝並完成 139 項測試及 lock 一致檢查；舊包不相容。

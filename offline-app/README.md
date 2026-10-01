# Code ZIP：完整 App 離線安裝

GitHub **Code → Download ZIP** 下載目前 main，解壓整個資料夾到新位置。不要只下載 experiment 或移動 wheels；不要覆蓋公司既有專案與 `.venv`。此入口不依賴 Release 或 Git LFS。

公司先提供核准的 **Windows Python 3.10.4 x64 完整安裝（含 Tcl/Tk、venv、pip）**。WebView 主介面另需 **Microsoft Edge WebView2 Runtime、.NET Framework 4.6.2 以上**；這些 Windows/Python 前置軟體不在 Code ZIP 中。缺軟體時交公司核准管道處理，不擅自連網安裝。需可寫入解壓資料夾及使用者暫存目錄。

在解壓後包含 `install-offline.bat` 的根目錄，使用 CMD：

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
test-company.bat
start-demo-login.bat
```

第一行必須改為公司實際核准的 Python 3.10.4 x64 路徑。每行成功才繼續；`test-company.bat` 已包含完整本機回歸、合成 WebView 操作與展示登入生命週期，不必另外重跑 full。展示帳密 admin/admin 僅用於暫存離線 fixture，登出即清除；不代表公司帳號或授權。公司 AD＋App 使用資格接好並驗收後，才進公司模式驗證真實 DVC。完整步驟見 [一鍵測試](../docs/ONE-CLICK-TEST.md)、[登入邊界](../docs/LOGIN-AND-APP-ACCESS.md)。

## 檔案與完整性

- `experiments/langgraph-lab/packages` 既有 52 個：正式 App 共用其中 48 個；其餘 4 個僅供 lab（langchain、langchain-openai、regex、tiktoken），不裝入 App。
- `offline-app/packages` 只新增正式 App 缺少的 21 個（3,101,202 bytes），含 pywebview、pythonnet、keyring 等。
- `bundle-manifest.json` 指定 69 個來源、版本及 SHA256。所有 wheels 的 tags 相容 Windows CPython 3.10.4 x64；仍以目標平台及完整 App `requirements.lock` 為準。
- installer 暫存組合 69 個 wheels，核對原正式包雜湊、lock 指紋及套件身份後，使用 pip `--no-index --no-deps`；安裝後核對 freeze 與 pip check，暫存 wheels 隨即移除。
- 若已有 root wheelhouse，仍驗證它，**不因 lock／雜湊錯誤改用其他來源**；缺檔、LFS 指標、不安全路徑或完整性錯誤均停止，不連網。既有 `.venv` 亦拒絕覆蓋。
- 原正式包的 license/notices 保留於 [THIRD-PARTY-NOTICES](../docs/THIRD-PARTY-NOTICES.md) 與 `docs/licenses`（包含 wheel 本身缺少的 upstream license）；此次沿用已核對的原二進位，不另造依賴版本。

錯誤時保留終端錯誤與 `artifacts/company-test/latest.json`；分享前遮密及去識別。公司 API、AD、人事資料與 Oracle 真實驗證仍未執行。VS Code Copilot 接手先開啟整個解壓資料夾，讀 AGENTS、README、ONE-CLICK-TEST、COMPANY-IMPLEMENTATION、DVC-REVIEW、VALIDATION；使用公司核准模型及權限，不宣稱 Copilot 可離線使用。

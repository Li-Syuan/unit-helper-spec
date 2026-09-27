# 開發環境與重建

## 必要條件

Windows x64，**Python 3.10.4（不能以 3.10.x 其他版本代替）**，安裝 Tcl/Tk 及 pip。
官方完整安裝程式：https://www.python.org/downloads/release/python-3104/
選 Windows installer (64-bit)；自訂安裝保留 Tcl/Tk，使用核准目錄，不勾 Add to PATH、不改其他專案的 Python。公司已有此版本直接使用。

專案沒有捆綁直譯器或虛擬環境。完整 direct/transitive 包含 pip 與 setuptools 固定於 requirements.lock；目前 OpenAI SDK 2.54.0、httpx 0.28.1、keyring 25.7.0，共 29 個鎖定套件。requirements.in 只記主要 runtime 套件，不用它代替 lock 安裝。

## 腳本

```powershell
.\scripts\setup.ps1 -PythonExe 'C:\Python3104\python.exe'
.\scripts\test.ps1
.\scripts\run.ps1
# 第二個乾淨環境（不存在的目錄）
.\scripts\setup.ps1 -PythonExe 'C:\Python3104\python.exe' -Environment .venv-verify060
.\scripts\test.ps1 -Environment .venv-verify060
```

setup 拒絕覆蓋既有環境；.venv 與 .venv-verify060 使用 include-system-site-packages=false。
企業 CA 情境可加 `-CaBundle 'C:\公司核准\roots.pem'`；只對這次 pip 設定 PIP_CERT，結束還原。請 IT 提供可信 CA／套件鏡像，不能使用 trusted-host 或 verify=False 繞過驗證。企業代理亦依 IT 既有環境設定。

PowerShell 腳本未核准時可改執行以下命令，需逐條確認 exit code 0：

```powershell
& 'C:\Python3104\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/doctor.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m desktop_app
```

doctor 真的建立 Tk root 並檢查確切版本／架構，不只是 import；不印出金鑰或環境變數值。
離線安裝請使用 [OFFLINE-INSTALL.md](docs/OFFLINE-INSTALL.md) 的 prepare-offline 與 setup -OfflineBundle 流程。它會核對鎖檔指紋、wheel 中繼資料與 SHA-256，再以無 index 模式安装；wheelhouse 不進 repo。不要跳過驗證直接安裝任意資料夾。

雙擊 diagnose.bat 會輸出易讀檢查與 artifacts/diagnostics/readiness.json。也可用 `python scripts/doctor.py --human --output artifacts/diagnostics/readiness.json`。分享報告不包含路徑、內部網址、帳號、秘密或原始例外；公司服務保持 not_tested。明確指定的 config／data-dir 可用於檢查公司的預定設定，無需先連網。

## 本次開發機紀錄

官方完整 python-3.10.4-amd64.exe 的 Authenticode 為有效 Python Software Foundation 簽章。silent installer 因本機 Windows Installer cache 路徑錯誤未完成；沒有宣稱安裝成功，也沒有改 PATH。
改用同一官方發行的 core/exe/lib/tcltk/pip/dev/tools/ucrt MSI，讀取其 File／Component／Directory 表與內嵌 CAB，解開至專案 `.runtime/python3104`，未註冊系統安裝。再以該確切直譯器建立兩個標準 venv，實際確認 Tk 8.6.12。
這是本機建置環境的例外處理，不是公司部署方式；公司使用核准的完整安裝。`.runtime` 與下載安裝程式都被 Git 忽略。
本機 pip 初始 CA 不足，使用 Windows 已信任憑證匯出成暫時 CA bundle 安裝，未停用 TLS。

0.6.0 本機正式基準為 .venv、全新 .venv-verify060 與全新 .venv-offline060，各 139 tests 通過。新離線包 wheelhouse-v060 共 29 個 wheel；不得重用舊版套件包。

0.7.0 沿用上述三個環境，各 150 tests 通過。requirements.lock 與 0.6.0 相同，不新增套件或重建離線包。

0.7.1 沿用上述三個環境，各 155 tests 通過；沒有新依賴或重建離線包。


0.8.0 沿用上述三環境，各 192 tests 通過，依賴與離線包不變。顯示診斷使用 `.venv/Scripts/python.exe scripts/display-check.py --output artifacts/diagnostics/display.json`；只記錄 DPI、Tk、字型與視窗尺寸，不讀取設定或使用者內容。

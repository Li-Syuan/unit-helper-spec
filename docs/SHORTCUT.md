# QA agent 桌面捷徑

先完成專案 `.venv` 環境建立，再雙擊根目錄的 **create-shortcut.bat**。工具會在 Windows 回報的目前使用者桌面建立 **QA agent** 捷徑，支援已重新導向至 OneDrive 的桌面。

捷徑使用專案的 `.venv/Scripts/pythonw.exe -m desktop_app`、專案工作目錄及 `desktop_app/assets/qa-agent.ico`，開啟程式時不留下命令列視窗。`start-app.bat` 仍可直接啟動。

建立前檢查 Python 恰為 3.10.4、64 位元、Tcl/Tk 可啟動，並確認 PNG／ICO 存在。環境或圖示缺失時不建立或更改捷徑。同名捷徑只有帶有本工具標記且目標符合專案啟動器格式時才更新；其他程式的同名捷徑會保留並顯示原因。

專案搬家後，先按 ENVIRONMENT.md 重建環境，再執行一次捷徑工具；舊捷徑會指向新位置。使用者資料仍使用原有資料目錄，本工具不搬移或刪除資料。

公司若限制 PowerShell 腳本執行，請 IT 核准此腳本；工具不變更永久執行原則。也可以繼續使用 start-app.bat。

測試或指定其他已存在的資料夾：

```powershell
powershell.exe -NoProfile -File .\scripts\create-shortcut.ps1 -Destination 'C:\已存在的資料夾'
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_shortcut.py -v
```

自動測試在暫存資料夾以 Windows COM 檢查捷徑的目標、參數、工作目錄、圖示、搬家更新及同名衝突；不在真實桌面建立測試捷徑。Windows 桌面與工作列最終外觀仍須另行實際檢視。

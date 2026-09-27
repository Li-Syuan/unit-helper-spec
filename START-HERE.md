# 開始這裡

本次交付已從 spec 前進到 **QA agent 0.5.0 本機桌面與公司接手準備包**。

依序讀 README.md → LOCAL-SPEC.md → VALIDATION-LOCAL.md → COMPANY-HANDOFF.md。
GPT 6 sol 的起始工作指令在 GPT6-SOL-HANDOFF.md。開發守則在 AGENTS.md。

舊 IMPLEMENTATION.md 的 M0～M4／AT-01～AT-27 是完整產品路線，不能當成本次全部已實作或要求現在建立中央平台。中央管理、AD／Oracle 實際接線、更新及打包需依交接文件另行完成。

公司先填 docs/COMPANY-INPUTS.md；動態查詢契約、測試工具包、離線安裝與現場驗收的入口集中在 README 的「公司接手準備包」。雙擊 start-app.bat 開應用，diagnose.bat 產生安全的本機環境報告。

## 0.5.0 深淺主題與候選圖示

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

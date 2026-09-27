# 開始這裡

本次交付已從 spec 前進到 **QA agent 0.7.0 本機桌面與公司接手準備包**。

依序讀 README.md → LOCAL-SPEC.md → VALIDATION-LOCAL.md → COMPANY-HANDOFF.md。
GPT 6 sol 的起始工作指令在 GPT6-SOL-HANDOFF.md。開發守則在 AGENTS.md。

舊 IMPLEMENTATION.md 的 M0～M4／AT-01～AT-27 是完整產品路線，不能當成本次全部已實作或要求現在建立中央平台。中央管理、AD／Oracle 實際接線、更新及打包需依交接文件另行完成。

公司先填 docs/COMPANY-INPUTS.md；動態查詢契約、測試工具包、離線安裝與現場驗收的入口集中在 README 的「公司接手準備包」。雙擊 start-app.bat 開應用，diagnose.bat 產生安全的本機環境報告。

## 0.5.0 深淺主題與候選圖示（歷史；0.6.0 已採用 A）

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

## 0.6.0 接手重點

已完成：A 正式圖示、使用者自管多助理、keyring、固定對話／Plan 路由、資料預覽轉交、Enter／Shift+Enter、獨立五步體驗、離線手冊及聲明。共用 endpoint／API key；名稱、assistant ID、備註由使用者管理。

修改入口：profiles.py 負責公司請求映射及憑證；assistant_views.py 為管理／轉交 UI；core.py schema 2 保存 binding/source，experience.py 管隔離導覽。公司請先提供遮蔽值的成功 API 範例，確認 ID 放 model 或獨立 body 欄位、session 規則及副作用能力。未配置 mapping 的新公司助理不能呼叫，不假裝用示範回答。具體步驟與命令見 docs/ASSISTANT-INTEGRATION.md。

環境新增 keyring==25.7.0，總鎖定套件 29 個；不得使用 keyrings.alt 或明文 fallback。完整離線包以新鎖檔重建，舊包指紋不符必須拒絕。正式驗證用 .venv、.venv-verify060、.venv-offline060，均恰好 Python 3.10.4。

完成條件：公司 API 對話隔離與回傳結果實測、AD／Oracle 核准接線、Excel／Windows 中文輸入法與縮放人工驗收。未實測項目仍保持 not_tested，不能以合成測試替代。中央協作、遠端更新、EXE、任意 SQL 及助理自動分工不在本版。

## 0.7.0 工作區改版（目前版本）

- 原生 Tkinter／ttk，未新增 runtime 套件。HTML／CSS 只是可離線開啟的視覺稿，入口 docs/design/workspace.html，不嵌入正式應用。
- 工作／管理／協助分組、原創線條 PNG、820px 聊天閱讀寬度、可選取的訊息卡片樣式、3～6 行整合輸入框及真實任務狀態。
- 工作詳情由明確選定的 task／plan ID 取得，顯示來源與助理版本；寬度至少 1380px 使用右欄，較窄以附屬視窗呈現。切換聊天不會改送正在執行的工作，已開啟詳情保留明確選定的來源。
- 開發改用固定檢查／測試腳本。沒有變更防毒設定、例外或執行政策；Norton 是否不再警告尚未確認，見 docs/NORTON-DEVELOPMENT.md。
- 沿用 Python 3.10.4 三個合格環境、29 個鎖定套件與 schema 2；公司 API、AD、Oracle、Excel 及原生中文 IME 仍需現場驗收。

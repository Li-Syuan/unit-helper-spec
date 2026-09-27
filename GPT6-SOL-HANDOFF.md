請接手這個 repo 的QA agent 0.7.0。你是 GPT 6 sol 開發 agent，請實際做接線與驗證，不重做 GUI 或另開平台。

先讀 AGENTS.md、README.md、LOCAL-SPEC.md、VALIDATION-LOCAL.md、COMPANY-HANDOFF.md、docs/current-state.md。保留 Windows x64、Python 恰好 3.10.4、Tkinter、現有 SQLite 與 OpenAI SDK 邊界。舊完整 spec 是後續路線；當前不做中央管理、遠端更新、產品 multi agents。

先讀 docs/COMPANY-INPUTS.md，取得 API／AD／Oracle 的最少必要資訊。可直接沿用 docs/QUERY-CATALOG.md 的動態欄位、docs/ADAPTER-TEST-KIT.md 的測試骨架與 docs/OFFLINE-INSTALL.md 的安裝工具；不用重做查詢 UI、測試 runner 或環境诊斷。

先以公司核准 Python 執行 scripts/setup.ps1、scripts/test.ps1，更新公司端的驗證記錄。不要使用外部專案環境。依序完成 COMPANY-HANDOFF 的六項工作：
1. 公司環境／第二乾淨環境基準。
2. 對照公司已成功的 chatbot 呼叫，依 docs/ASSISTANT-INTEGRATION.md 調整 profiles.py／gateways.py；核對 session 隔離及原生工具副作用。Plan 預覽固定本機表單，不呼叫可能產生副作用的 bot。
3. 接既有 AD／員工名單，補服務層授權與持續停用檢查，不把 demo identity 冒充 AD。
4. 接三項核准 Oracle 查詢，bind 與身份範圍由可信層處理，人工結果逐欄校對。
5. 舊資料與排程 read-only inventory、備份、dry-run、watermark、停舊啟新與回復測試；不刪舊資料。
6. 公司 GUI／Excel 真實驗收，之後依公司流程打包。

開始先盤點此工作區公司現有原始碼、成功 API 範例與環境。找得到就沿用；找不到就列出具體缺的內部資訊，一次問最少必要問題，繼續其他可做項目。不要猜 SQL、AD 欄位、助理 ID、URL 或密碼。秘密不輸出到對話／repo／log。

每項工作先列修改位置與驗收，再實作與跑測試；同步更新 docs/implementation-status.md 及公司實测記錄。mock_passed 與 real_passed 分列，skip 不算通過。當前基準測試必須持續通過；公司新增測試不得停用安全 gate。公司模式錯誤必須明確顯示，禁止 demo fallback。

可以依 AGENTS.md 用至多兩個互斥 subagent 工作包；沒有 subagent 能力就順序做。不要把自己分工的角色當產品 runtime 多代理。不要改公司原有規則，不執行未授權的正式發布／資料變更。

公司實測入口 scripts/company_check.py 預設不連線，缺項回報 not_tested。將 company_templates 的範本複製到 company_local，補有真實斷言的 hooks；確認測試 bot 無未授權副作用後，才明確加 --execute --capabilities-reviewed。不要把單純回傳 True、skip 或 mock 當公司通過。沒有能力確認時先完成離線契約與其他接線工作。

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

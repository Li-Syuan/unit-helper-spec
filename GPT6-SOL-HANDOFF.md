請接手這個 repo 的QA agent 0.5.0。你是 GPT 6 sol 開發 agent，請實際做接線與驗證，不重做 GUI 或另開平台。

先讀 AGENTS.md、README.md、LOCAL-SPEC.md、VALIDATION-LOCAL.md、COMPANY-HANDOFF.md、docs/current-state.md。保留 Windows x64、Python 恰好 3.10.4、Tkinter、現有 SQLite 與 OpenAI SDK 邊界。舊完整 spec 是後續路線；當前不做中央管理、遠端更新、產品 multi agents。

先讀 docs/COMPANY-INPUTS.md，取得 API／AD／Oracle 的最少必要資訊。可直接沿用 docs/QUERY-CATALOG.md 的動態欄位、docs/ADAPTER-TEST-KIT.md 的測試骨架與 docs/OFFLINE-INSTALL.md 的安裝工具；不用重做查詢 UI、測試 runner 或環境诊斷。

先以公司核准 Python 執行 scripts/setup.ps1、scripts/test.ps1，更新公司端的驗證記錄。不要使用外部專案環境。依序完成 COMPANY-HANDOFF 的六項工作：
1. 公司環境／第二乾淨環境基準。
2. 對照公司已成功的 chatbot 呼叫，調整 gateways.py；核對 session 隔離及原生工具副作用。Plan 預覽固定本機表單，不呼叫可能產生副作用的 bot。
3. 接既有 AD／員工名單，補服務層授權與持續停用檢查，不把 demo identity 冒充 AD。
4. 接三項核准 Oracle 查詢，bind 與身份範圍由可信層處理，人工結果逐欄校對。
5. 舊資料與排程 read-only inventory、備份、dry-run、watermark、停舊啟新與回復測試；不刪舊資料。
6. 公司 GUI／Excel 真實驗收，之後依公司流程打包。

開始先盤點此工作區公司現有原始碼、成功 API 範例與環境。找得到就沿用；找不到就列出具體缺的內部資訊，一次問最少必要問題，繼續其他可做項目。不要猜 SQL、AD 欄位、助理 ID、URL 或密碼。秘密不輸出到對話／repo／log。

每項工作先列修改位置與驗收，再實作與跑測試；同步更新 docs/implementation-status.md 及公司實测記錄。mock_passed 與 real_passed 分列，skip 不算通過。當前基準測試必須持續通過；公司新增測試不得停用安全 gate。公司模式錯誤必須明確顯示，禁止 demo fallback。

可以依 AGENTS.md 用至多兩個互斥 subagent 工作包；沒有 subagent 能力就順序做。不要把自己分工的角色當產品 runtime 多代理。不要改公司原有規則，不執行未授權的正式發布／資料變更。

公司實測入口 scripts/company_check.py 預設不連線，缺項回報 not_tested。將 company_templates 的範本複製到 company_local，補有真實斷言的 hooks；確認測試 bot 無未授權副作用後，才明確加 --execute --capabilities-reviewed。不要把單純回傳 True、skip 或 mock 當公司通過。沒有能力確認時先完成離線契約與其他接線工作。

## 0.5.0 深淺主題與候選圖示

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

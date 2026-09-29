# QA agent 0.17.0 驗證紀錄

本版新增公司啟用檢查、明確 assistant metadata GET 及單助理財經日報。沒有呼叫公司端點或使用真實金鑰；公司搜尋、工具派發與多 ID 能力均未以本機結果代替。

## 回歸與環境

正式 Windows x64、Python **3.10.4**，常駐 `.venv` 執行 460 項：**459 通過、1 錯誤、0 跳過**。doctor、pip check、freeze 與既有69項鎖檔一致；原始命令／結果見 [development.json](validation/development.json)。完整命令保留非零結束碼。

唯一錯誤是既有 `test_long_message_theme_copy_and_close_without_mutation` 的 Windows 剪貼簿讀回：`OpenClipboard failed (Windows error 5)`。沒有刪除或放寬測試，根因及真實貼上能力尚未確認，仍需可互動桌面驗證。

本版沒有新增依賴或重建環境。沿用0.16.0已完成的乾淨／完全離線69 wheels安裝證據：[clean-rebuild.json](validation/clean-rebuild.json)、[offline-rebuild.json](validation/offline-rebuild.json)；兩者是先前443項測試紀錄，**不是本版460項重建結果**。重新交付離線包僅更新已提交原始碼，wheels與lock不變。常駐仍只有`.venv`與其基礎直譯器。

## 本版新增證據

| 範圍 | 狀態與證據 |
|---|---|
| 公司啟用檢查 | mock_passed：純本機盤點、不讀金鑰、不派發；角色宣告不能冒充驗收，分享欄位不含植入秘密 |
| metadata GET | mock_passed：真SDK+MockTransport，僅一次retrieve、無thread/run/pluginapi；錯誤ID及認證錯誤拒絕，真實pending阻擋改設定並等待關閉 |
| 財經日報 | mock_passed：預覽零派發、十分鐘期限、固定request防重、公司版本綁定、無四角色前提、試跑後核對及持續同意才排程 |
| 排程與保存 | local_real_passed／mock_passed：真SQLite與可控時鐘；台北08:00、立即測試不改時間、重開不重播、每次隔離thread、失敗暫停及通知 |
| 取消 | mock_passed：晚到回覆不成功，取消後真實future尚未結束阻擋重疊 |
| 工具界線 | mock_passed：tool_choice=none；requires_action停止，零pluginapi呼叫；結果search仍為not_tested |

新增17項案例，保留原443項覆蓋。既有LangGraph、Assistants多輪、Plan批准、恢復、待辦、刪除與成果功能仍納入全套回歸。GUI中發現排程enabled的SQLite整數與前端布林契約不符，已修正為明確布林並補正反斷言；失敗紀錄保留本機開發log，不以首次嘗試宣稱通過。

## 實際介面

真正啟動WebView2，以合成資料／SDK模擬回覆操作DOM，**11組檢查通過**。新增旅程從主對話財經日報按鈕進入，預覽→試跑→核對→啟用→暫停；啟用不多跑一次，暫停後不殘留已啟用文字。公司設定盤點與metadata檢查均未建立模型run。

檢視深淺主題、1050×700、1280×860與最大化；小視窗成果與關閉／啟用入口可達，長內容使用可捲動主體。截圖為WebView2 CapturePreview，只包含App；見 [介面摘要](validation/web-display.json) 與 docs/images 的四張現行畫面。自動GUI操作不代表人工直觀性或中文IME通過。

## 待公司及人工驗收

- 公司API／CA／真實多ID／Internet Search／pluginapi：**not_tested**。使用者回報舊App已能搜尋，但本checkout未取得公司成功搜尋原始證據。工具已配置在助理內，仍可能需要客戶端requires_action往返；目前工具限制可能阻擋搜尋。
- 四角色Instruction／Luna內容品質：**not_tested**。planner為主代理，另三位為分析／覆核／彙整；尚無已驗證的第五位搜尋角色。合成題見 [公司指令](COMPANY-IMPLEMENTATION.md)。
- AD、owner隔離、Oracle、舊資料移轉：**not_tested**。
- 真人使用性、中文IME、Excel／Clipboard：**not_tested；本機Clipboard測試失敗**。
- Norton成效：**未能確認**。未關防毒、加排除、修改執行政策或停用TLS。

沒有啟用LangSmith、背景模型檢查或自動重試。收到文字只代表取得回覆，不能認定日期、行情、來源或自由文字已核實。App關閉不執行本機排程；取消不能保證遠端已停止。

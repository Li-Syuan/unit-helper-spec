# QA agent 0.18.0 驗證紀錄

本版加入人工核准搜尋、受限 pluginapi 往返、工具收據與 rag 搜尋指示。沒有呼叫公司端點或使用真實金鑰；公司搜尋、工具權限與多 ID 能力均未以本機結果代替。

## 回歸與環境

正式 Windows x64、Python **3.10.4**，常駐 `.venv` 最後完整執行 **495 項全部通過，0 跳過**。doctor、pip check、freeze 與既有69項鎖檔一致；原始命令／結果見 [development.json](validation/development.json)。

首輪494項出現一個context相容性失敗與既有剪貼簿錯誤 `OpenClipboard failed (Windows error 5)`，原始紀錄保存於本機 artifacts/validation-search-first-pass.json。已修正非rag角色保持原context契約，另加rag文件案例。最後完整回歸剪貼簿測試也通過；沒有移除／放寬測試或更改系統政策，先前存取遭拒根因仍未確認，人工Clipboard／Excel仍未驗收。

本版沒有新增依賴或重建環境。沿用0.16.0已完成的乾淨／完全離線69 wheels安裝證據：[clean-rebuild.json](validation/clean-rebuild.json)、[offline-rebuild.json](validation/offline-rebuild.json)；兩者是先前443項測試紀錄，**不是本版495項重建結果**。離線交付包更新已提交原始碼，wheels與lock不變。常駐仍只有`.venv`與其基礎直譯器。

## 本版新增證據

| 範圍 | 狀態與證據 |
|---|---|
| 公司啟用檢查 | mock_passed：純本機盤點、不讀金鑰、不派發；角色宣告不能冒充驗收，分享欄位不含植入秘密 |
| metadata GET | mock_passed：真SDK+MockTransport，僅一次retrieve、無thread/run/pluginapi；錯誤ID及認證錯誤拒絕，真實pending阻擋改設定並等待關閉 |
| 財經日報 | mock_passed：預覽零派發、十分鐘期限、固定request防重、公司版本綁定、無四角色前提、試跑後核對及持續同意才排程 |
| 排程與保存 | local_real_passed／mock_passed：真SQLite與可控時鐘；台北08:00、立即測試不改時間、重開不重播、每次隔離thread、失敗暫停及通知 |
| 取消 | mock_passed：晚到回覆不成功，取消後真實future尚未結束阻擋重疊 |
| 核准策略 | mock_passed：metadata候選／十分鐘token／明示同意，策略綁版本；更換目標清除核准、撤銷verified，設定修改與背景派發有共同鎖 |
| 工具界線 | mock_passed：僅確認日報／rag可使用允許清單；聊天與planner不開工具，混合未知工具整批零派發、參數／批次／大小限制 |
| 收據恢復 | mock_passed：兩批多call配對、已完成工具快取恢復、plugin／submit結果未明不retry、取消不提交晚到結果、錯誤thread拒絕 |
| 多助理搜尋 | mock_passed：真SDK＋真LangGraph＋合成HTTP，planner→rag→analysis→review→compose，僅rag派發一次搜尋；預覽顯示工具、一次確認防重 |

新增35項案例，保留原460項覆蓋。獨立程式審查發現重開policy未呈現、變更核准競態與工具description遺失，均已修正並補回歸。既有LangGraph、Assistants多輪、Plan批准、恢復、待辦、刪除與成果功能仍納入全套。

## 實際介面

真正啟動WebView2，以合成資料／SDK模擬回覆操作DOM，**12組檢查通過**。新增核准預設不勾／保存零派發／重開顯示策略，以及財經日報實際走一次Mock pluginapi、顯示提交收據、核對→啟用→暫停。啟用不多跑一次；設定盤點與metadata均未建立模型run。

檢視深淺主題、1050×700、1280×860與最大化；小視窗成果與關閉／啟用入口可達，長內容使用可捲動主體。截圖為WebView2 CapturePreview，只包含App；見 [介面摘要](validation/web-display.json) 與 docs/images 的四張現行畫面。自動GUI操作不代表人工直觀性或中文IME通過。

## 待公司及人工驗收

- 公司API／CA／真實多ID／Internet Search／pluginapi：**not_tested**。通用傳輸已依官方契約完成；需在公司核对實際function、schema、tools override與來源。不能把metadata或HTTP200視為權限／能力驗收。
- 角色Instruction／Luna內容品質：**not_tested**。planner為主代理，analysis／review／compose為三位子代理，可加入rag搜尋角色；合成題與公司試跑見 [公司指令](COMPANY-IMPLEMENTATION.md)。
- AD、owner隔離、Oracle、舊資料移轉：**not_tested**。
- 真人使用性、中文IME、Excel／Clipboard：**not_tested**；最後本機Clipboard合成測試通過，首輪曾存取遭拒。
- Norton成效：**未能確認**。未關防毒、加排除、修改執行政策或停用TLS。

沒有啟用LangSmith、背景模型檢查或自動重試。收到文字只代表取得回覆，不能認定日期、行情、來源或自由文字已核實。App關閉不執行本機排程；取消不能保證遠端已停止。

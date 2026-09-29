# QA agent 0.18.1 驗證紀錄

本版調整 WebView／Tk 深淺語意配色、訊息卡片與通知辨識，不新增依賴、不改 schema、模型派發或核准契約。搜尋能力及公司服務沿用先前界線，仍需公司實測。

## 回歸與環境

Windows x64、Python **3.10.4**，常駐 `.venv` 完整回歸 **498 項通過，0 跳過**。doctor、pip check、freeze 與既有 69 項鎖檔一致；命令、時間及輸出見 [development.json](validation/development.json)。保留原495項基準，新增通知語意與深淺對比驗證。

本輪未新建環境。先前0.16.0的乾淨／離線重建證據仍是443項：[clean-rebuild.json](validation/clean-rebuild.json)、[offline-rebuild.json](validation/offline-rebuild.json)，不能當成本版重新安裝結果。離線交付使用相同鎖定wheels。

## 配色與通知

- local_real_passed：Tk通知生命週期、取消中性提示、一般未讀青藍色、錯誤紅色。關閉通知與開啟清單不自動標讀。
- local_real_passed：WebView與Tk主題中，受測一般文字、狀態標籤及主操作按鈕的配色對比均至少4.5:1。首輪淺色次要文字在部分底色不足，已加深修正；這不代表完整無障礙驗收。
- local_real_passed：WebView已讀狀態使用實際`is_read`欄位；通知顏色來自所屬task，查看後未讀數更新。結果入口依原task種類開啟。
- 呈現規則：青藍操作／未讀、紫色團隊、琥珀待確認、藍色執行、綠色完成、紅色失敗、中性取消。搭配文字與圖示；綠色不代表自由文字或新聞事實已核實。

## 真實介面操作

實際WebView2、暫存合成資料及MockTransport，**15組旅程檢查通過**，见 [web-display.json](validation/web-display.json)。包含多輪對話、錯誤保留輸入、未啟用草稿、確認前零派發、查詢、多助理成果、回饋、核准搜尋與日報試跑→核對→排程→暫停。

新增檢查：深淺主題保留草稿／游標且零模型派發、預覽為琥珀、成果為綠色、四類狀態顏色各異、通知工作狀態與已讀狀態分離。檢視1050×700、1280×860及最大化；輸入／確認／取消入口可達。WebView2 CapturePreview只保存App內容；docs/images維持四張當前截圖，其他合成驗收畫面在忽略目錄artifacts/web-smoke。

UI程式操作與截圖檢視不等於真人直觀性驗收。資料庫、派發、LangGraph／Assistants／搜尋政策、恢復與防重仍包含於全套回歸，沒有呼叫真實公司服務。

## 未驗收範圍

- 公司API、CA、多ID、Internet Search、pluginapi真實相容與權限：**not_tested**。
- Luna角色內容品質、AD、owner隔離、Oracle、舊資料移轉：**not_tested**。
- 真人使用性、中文IME、Excel／人工剪貼簿：**not_tested**。
- Norton成效：**未能確認**；沒有修改防毒、執行政策或TLS設定。
- PyInstaller實際EXE：**not_tested**；本輪為介面配色修正。

App關閉不執行本機排程；取消不保證遠端停止。核准搜尋與取得回覆仍不是能力或事實驗收。

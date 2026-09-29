# QA agent 0.18.2 驗證紀錄

本版新增設定頁三款風格與六種深淺組合、預覽卡、即時套用、保存重試與恢復預設，不新增依賴、不改 schema、模型派發或核准契約。搜尋能力及公司服務沿用先前界線，仍需公司實測。

## 回歸與環境

Windows x64、Python **3.10.4**，常駐 `.venv` 完整回歸 **508 項通過，0 跳過**。doctor、pip check、freeze 與既有 69 項鎖檔一致；命令、時間及輸出見 [development.json](validation/development.json)。保留原498項基準，新增三款外觀、保存失敗重試、重開／恢復預設、風格對比與Tk狀態保留驗證。

本輪未新建環境。先前0.16.0的乾淨／離線重建證據仍是443項：[clean-rebuild.json](validation/clean-rebuild.json)、[offline-rebuild.json](validation/offline-rebuild.json)，不能當成本版重新安裝結果。離線交付使用相同鎖定wheels。

## 外觀選擇與保存

- local_real_passed：三款風格×深淺外觀均可套用；語意狀態色固定，選取標記與磁碟偏好一致。設定頁六種實際WebView截圖已檢視。
- local_real_passed／mock_passed：偏好損壞回到ocean；寫入失敗時保留本次外觀、saved=false與重試入口，重試成功清除舊失敗提示；原設定檔保留，恢復預設不清其他偏好。Tk以完整配對保存，重開沿用選擇。
- local_real_passed：保留草稿、選取、已開啟對話框及未送出的公司設定。首輪WebView發現首次背景刷新重建設定表單，已修正force render的signature紀錄，保留失敗證據於artifacts/theme-choice-first-pass.json，完整GUI重跑通過。
- 全部外觀操作零模型／查詢／排程派發；沒有變更公司設定。

## 配色與通知

- local_real_passed：Tk通知生命週期、取消中性提示、一般未讀青藍色、錯誤紅色。關閉通知與開啟清單不自動標讀。
- local_real_passed：WebView與Tk主題中，受測一般文字、狀態標籤及主操作按鈕的配色對比均至少4.5:1。首輪淺色次要文字在部分底色不足，已加深修正；這不代表完整無障礙驗收。
- local_real_passed：WebView已讀狀態使用實際`is_read`欄位；通知顏色來自所屬task，查看後未讀數更新。結果入口依原task種類開啟。
- 呈現規則：依風格的主操作色／固定青藍未讀、紫色團隊、琥珀待確認、藍色執行、綠色完成、紅色失敗、中性取消。搭配文字與圖示；綠色不代表自由文字或新聞事實已核實。

## 真實介面操作

實際WebView2、暫存合成資料及MockTransport，**16組旅程檢查通過**，见 [web-display.json](validation/web-display.json)。包含多輪對話、錯誤保留輸入、未啟用草稿、確認前零派發、查詢、多助理成果、回饋、核准搜尋與日報試跑→核對→排程→暫停。

新增檢查：深淺主題保留草稿／游標且零模型派發、預覽為琥珀、成果為綠色、四類狀態顏色各異、通知工作狀態與已讀狀態分離。檢視1050×700、1280×860及最大化；輸入／確認／取消入口可達。WebView2 CapturePreview只保存App內容；docs/images維持四張當前截圖，其他合成驗收畫面在忽略目錄artifacts/web-smoke。

UI程式操作與截圖檢視不等於真人直觀性驗收。資料庫、派發、LangGraph／Assistants／搜尋政策、恢復與防重仍包含於全套回歸，沒有呼叫真實公司服務。

GUI另一次重跑在分工成果切換遇到JavascriptException，當時工作已完成；紀錄在artifacts/theme-choice-timing-pass.json。測試移除固定兩秒即可看到成果的假設，改等實際DOM入口後再操作，最後完整重跑通過，沒有放寬批准或成果斷言。

## 未驗收範圍

- 公司API、CA、多ID、Internet Search、pluginapi真實相容與權限：**not_tested**。
- Luna角色內容品質、AD、owner隔離、Oracle、舊資料移轉：**not_tested**。
- 真人使用性、中文IME、Excel／人工剪貼簿：**not_tested**。
- Norton成效：**未能確認**；沒有修改防毒、執行政策或TLS設定。
- PyInstaller實際EXE：**not_tested**；本輪為介面配色修正。

App關閉不執行本機排程；取消不保證遠端停止。核准搜尋與取得回覆仍不是能力或事實驗收。

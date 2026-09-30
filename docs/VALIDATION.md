# QA agent 0.18.2 驗證紀錄

本版新增設定頁三款風格與六種深淺組合、預覽卡、即時套用、保存重試與恢復預設，不新增依賴、不改 schema、模型派發或核准契約。搜尋能力及公司服務沿用先前界線，仍需公司實測。

## 公司部署修正（2026-09-30）

公司去識別報告指出正式環境缺少LangGraph且核准索引缺指定Bleach版本。本機核對正式69個wheels與根lock一致，保留現有lock；不使用lab的52套件，也沒有調整公司索引。新增直接Python離線安裝入口，拒絕覆寫已有環境；full先檢查環境再探索測試，缺件保存commands並標記not_run。

- **local_real_passed**：Windows x64、Python恰好3.10.4，由`.runtime/python3104/python.exe`新建`.venv-deploy`，以正式wheels安裝，doctor／pip check／精確freeze-lock比對通過。包含LangGraph1.2.12、checkpoint-sqlite3.1.1、aiosqlite0.22.1、Bleach6.4.0、OpenAI2.54.0。安裝與診斷未呼叫公司服務。
- **mock_passed**：7项套件完整性與2项安裝器契約通過；既有env不覆蓋、缺件在建立前停止、安裝失敗停止、不連外fallback、lock不符拒絕。5項共用runner契約通過，full環境失敗不探索或執行測試。安裝子程序以`PIP_CONFIG_FILE=NUL`停讀pip設定，避免額外find-links來源；不改公司設定檔。
- **full_failed**：乾淨離線環境完整執行512項，511通過、1錯誤、0跳過；測試141.243秒，總計144.31秒。失敗為`tests.test_dialogs.DialogTests.test_long_message_theme_copy_and_close_without_mutation`，Windows `OpenClipboard`回傳error5；獨立複查仍失敗，未移除、skip或改為假通過。[offline-rebuild.json](validation/offline-rebuild.json)保留本次失敗證據，不能宣稱正式full驗收通過。原首輪紀錄亦留於忽略目錄artifacts/deployment。
- **not_tested**：公司真實API／權限／多ID／搜尋、人工GUI／IME／Excel仍未驗收。本輪未改UI／bridge，不重跑WebView smoke；先前畫面證據不代表本輪人工驗收。Norton成效未能確認。

部署包可用來修正公司依賴缺件；公司仍需在實際電腦重跑一次完整驗證，尤其剪貼簿讀回。安裝成功與完整回歸成功分開判定，不將本機框架或lab通過當成公司功能通過。

最後補強pip設定隔離後，已再次以相同69個wheels新建乾淨環境並通過安裝／doctor／pip／lock檢查；14項部署相關targeted檢查亦全數通過。實際結果附於offline-rebuild的deployment_followup，不覆寫full_failed。暫時`.venv-deploy`已於確認程序結束及路徑安全後清除，只保留原常駐`.venv`與其基礎直譯器。

## 測試收斂實測（2026-09-29）

本輪僅整理測試及交接規則，產品仍為0.18.2；未修改產品功能、schema或依賴。全部使用同一個Python3.10.4常駐環境，不新增虛擬環境、不呼叫公司服務。

| 範圍 | 案例數 | 實測時間 | 判定 |
|---|---:|---:|---|
| 整理前完整基準 | 508 | 225.67秒（含載入） | 全數通過 |
| 整理後日常quick | 344 | 21.86秒（測試本身20.65秒） | 全數通過、0跳過；未跑GUI與完整環境檢查 |
| 整理後full | 510 | 166.75秒（測試本身164.46秒） | 全数通過、0跳過；doctor/pip/lock通過 |

較早完整回歸曾量得174.661秒，本輪基準測試本身224.230秒，表示耗時有波動。主要節省來自日常不啟動GUI／環境檢查，以及交付不再連跑test full與verify；不宣稱full本身大幅加速。逐項耗時與最慢案例見[development.json](validation/development.json)。本轮quick與baseline原始量測留在被忽略的artifacts/testing。

整理前後覆蓋對照：

| 原覆蓋 | 整理後 |
|---|---|
| theme的2個舊偏好案例＋appearance的2個新偏好案例 | appearance中2個參數化案例，保留舊API、缺失／損壞／型別／roundtrip、原子寫入失敗、其他偏好及暫存清理 |
| theme與theme_choices_tk各一個閒置切換保留案例 | theme的一個六組配色旅程，保留兩入口、草稿／游標／選取／捲動／附件／Plan／對話框／徽章／零派發 |
| Tk套件中的純配色檢查 | 移至theme_semantics，quick執行，不建立視窗 |
| App＋第二Tk的樣式隔離 | 兩個獨立Tk解譯器檢查，不再建立App與資料庫 |
| 實際Windows認證管理員往返 | 分離到WindowsCredentialTests，只於full或明確targeted執行 |
| 批准／防重／取消／隔離／工具授權／遷移／刪除 | 原核心案例保留於quick及full |

合併3個重複測試單位，新增5個執行器契約案例，因此508→510；數量不是品質或完成門檻。新的案例驗證分類防漏、選測去重、失敗／skip／expectedFailure不得通過、GUI與網路阻擋、報告範圍及full僅執行一次。日常報告覆寫latest，不累积逐版文件。

PowerShell預設quick、多模組targeted及個別方法入口已實跑；verify實際執行同一full一次並保存本次證據。合成失敗曾發現WebView資源初始化受暫存cwd影響與Windows暫存目錄收尾問題，已修正測試隔離並通過重測；失敗紀錄保留artifacts/testing/runner-failure.json。未以skip或假成功處理。

本輪沒有變更UI／bridge，未重跑WebView smoke；下方WebView畫面證據沿用0.18.2外觀交付。公司、人工GUI、IME及Norton成效不因本輪回歸變成已驗收。

完整回歸後僅修正報告使用LF換行，保留原始量測值；受影響的5項執行器契約已再通過targeted驗證，沒有重跑產品全套。

先前0.16.0的乾淨重建證據仍為當時版本：[clean-rebuild.json](validation/clean-rebuild.json)。offline-rebuild已更新為上方2026-09-30部署修正的實測結果；9月29日測試收斂本身未改鎖檔或重建套件。

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

# QA agent 0.15.0 最新驗證

可選 LangChain／LangGraph 離線試驗包另見 [試驗驗證](../experiments/langgraph-lab/VALIDATION.md)：兩個全新 Python 3.10.4 x64 環境各 10 項通過，52 個 wheels 完整離線安裝。這不代表正式 App 已接入框架；本輪未改 App 執行程式或根依賴，原下列限制繼續保留。

日常 `.venv` 與純離線重建 `.venv-offlineverify` 均使用 **Python恰好3.10.4 x64**，完整回歸各 **409項：408通過、1錯誤、0跳過**。唯一錯誤是既有Windows剪貼簿讀回 `OpenClipboard failed (Windows error 5)`，未修改測試／加skip／冒稱通過。當時桌面處於鎖定狀態；這是觀察條件，沒有宣稱已證明根因。解鎖後仍需重測。紀錄：[日常](validation/web-development.json)、[離線](validation/web-offline.json)。

doctor的Python／Tk／WebView2／.NET／41個鎖定套件及pip check通過；離線安裝使用--no-index、--no-deps、--no-cache-dir，沒有借用外部site-packages。鎖檔最後只統一LF換行，版本未再改變；wheel manifest已依最終指紋重算並驗證。已確認兩個暫存驗證環境沒有執行程序或連結跳轉並清除，只留日常.venv與其基礎直譯器.runtime/python3104。

新兩模式11個服務案例通過：多輪、切模式／助理隔離、四階追問、預覽零存檔、確認固定不啟用、取消、改稿失效、防重、儲存失敗、正式provider停用無fallback、不可信欄位與排程格式拒絕。Web橋接13項涵蓋既有Plan、查詢、轉交、草稿、防重與純文字Markdown。

以日常環境真正啟動WebView2並操作DOM，驗證：新主畫面多輪→切模式清畫面→四項追問→預覽→取消零任務→確認後只保存enabled=0；進階三次查詢旅程在批准前零派發；明示合成mock子代理的分工批准→成果→回饋。沒有外部模型／公司呼叫。畫面用WebView2 CapturePreview擷取，已檢視深／淺、一般1280×860、小尺寸1050×700與最大化內容。這不是Windows框線外觀、真IME、人工使用性或公司服務驗收。證據：[介面摘要](validation/web-display.json)。

公司API／AD／Oracle／多assistant ID、真人IME／Excel、人工走查及Norton成效維持 **not_tested／未能確認**。不能由本機示範通過推定正式服務可使用。下面保留上一個發布版的基準證據；本次以此節為準。

# QA agent 0.14.0 驗證摘要

## 0.14.0 最新驗證

最終完整離線包的乾淨 Python 3.10.4 x64 環境：385項完整回歸全數通過、0 skipped，doctor／pip check／freeze與鎖檔一致。包含保留的364項基準，以及成果12、UI4、Instruction5項。最新原始紀錄見[offline-rebuild.json](validation/offline-rebuild.json)。日常環境先前383項及新增項目單獨測試亦通過。未放寬、刪除或跳過原有基準測試，遷移斷言更新為schema6。公司Luna／API／AD／Oracle仍為not_tested。

已檢視真Tk深淺成果畫面，1050×700要求在目前DPI下受最小尺寸調整為1050×720；1280×860與最大化1350×1050均檢查操作可達、內文捲軸及草稿保留。這是程式GUI操作，不代替同仁人工走查。證據在display-current.json的outcomes_0_14_0。

比較測試另含排程失敗重試仍沿原排程來源，不混入手動工作；比較測試含同期間、前一日日期變動、固定日期不同、版本／綁定／類別／排程隔離、高精度差值、空資料、截斷、NULL及欄位不符；回饋含改選／清除、失敗保留、背景保存與失敗重試、來源刪除保留。schema5失敗交易回復及可讀備份已驗證，既有schema1～4遷移测试保留。

以下0.13.0環境與公司未測限制為前次基準，最新以本節及離線重建紀錄為準。

目前保留對話式 Plan、多助理協作、固定流程排程、通知及 schema 5；本版新增可收合圖示側欄、助理團隊及分工進度，改為一次明確「確認執行」。沿用 Python 恰好 3.10.4、Windows x64、唯一 .venv 與原有鎖定套件，沒有新增依賴或 schema；離線交付另建臨時乾淨環境實測。

## 本機回歸

離線交付的全新 Python **3.10.4 x64** 環境完成 **364 項全數通過、0 skipped**。29 個鎖定套件由本地 wheelhouse 安裝（--no-index、--no-deps、--no-cache-dir），安裝前包雜湊與 lock 指紋檢查通過；doctor、pip check、freeze 與 lock 比對均通過。實際直譯器、時間、命令與完整輸出見 [offline-rebuild.json](validation/offline-rebuild.json)。沒有重用日常 .venv 的 site-packages。

離線環境也實際開啟 Tk 桌面，以暫存資料完成「合成查詢草稿 → 預覽零派發 → 確認 → 一筆成功查詢」，無公司／外部 AI 請求。安裝包排除 Python 直譯器、.venv、.env、金鑰與使用者資料；Python 完整安裝程式仍由公司提供。公司 API／AD／Oracle 的真實驗收保持 not_tested。

先前日常環境曾有一項 Windows 剪貼簿讀回 error 5，紀錄仍保留於 [development.json](validation/development.json)。本次在新離線環境原樣重跑該測試已通過；未 mock、skip 或放寬斷言，亦未修改 Windows／防毒政策。先前拒絕存取的根因尚未確認，不能歸因為更換套件或保證不再出現。重測入口見 [開發指南](DEVELOPMENT.md#測試與交付)。

保留前版 347 項，新增 17 項涵蓋側欄／團隊、分工呈現、一次確認及圖形資源釋放。驗證腳本失敗時也保存證據並回傳非零退出碼。

新增驗證涵蓋側欄收合偏好、保存失敗、草稿／附件／選取保留、缺圖示退回文字、助理搜尋與真實能力狀態、既有助理編輯入口、規劃入口零派發、響應欄數、完整成果、失敗／取消狀態、雙擊只執行一次及小視窗操作可達。

初次完整回歸曾遇到 Tcl「Fail to allocate bitmap」。獨立最小案例確認 Windows Tk 重複載入 ICO 累積 GDI／USER handles；改用多尺寸 PNG iconphoto（仍有真實 Windows 主／附屬視窗大小圖示），ICO 繼續提供捷徑。另清理關閉時 Tcl class binding／變數 trace 回呼。重複開關及切換後資源穩定、App／Tk 弱引用釋放，完整 364 項不再 native crash。未藉由刪測試或分程序隔離掩蓋問題。

通知覆蓋右下角位置、未讀徽章、重複刷新、逾時／懸停、關閉保留未讀、啟動不重播、查看結果與原因、多則合併、99+、來源刪除、長文保留及 timer 清理；收合時徽章改為數字，仍可查看通知。

新增覆蓋：主代理追問／修訂、未批准零執行、各助理資料隔離、綁定及能力失效、未知工具與格式拒絕、精確 facts、取消晚到結果、防重、交易回復、schema 4 遷移與前版遷移、來源刪除、排程啟停／重啟／跨日重試、同一失敗步驟只建一個後繼工作。真 Tk 測試涵蓋模式與草稿保存、送出後清除與晚到保存、選取保留、原始表格跨頁複製及公式防護。

通知不產生工作、模型呼叫或排程，不改既有通知產生条件。

## Groq 與公司界線

先前 `scripts/check-workflows.py --live` 已使用暫存資料庫、合成查詢及最多四次真實請求，完成規劃 → 查詢 → 分析 → 覆核 → 日報，再建立並暫停合成排程。結果見 [workflow-trial.json](validation/workflow-trial.json)，本輪 UI 改版未重送外部請求。此入口預設不加 --live 為 not_tested、零請求。

前幾次真實試跑因模型把 facts 多包一層而被拒絕；明確提供預期結構後重新試跑通過，沒有修改數值檢查或用假回覆替代。Groq 使用同一模型的四個隔離角色；本次一次成功不能保證每次自然語言解析及自由文字正確，也不代表公司多個 assistant ID 或原生工具已驗收。

| 項目 | 結果 |
|---|---|
| 有限流程、批准、防重、取消、隔離與失敗保留 | mock_passed／local_real_passed |
| Groq 規劃及三位子代理合成日報 | external_real_passed；只用合成資料，不改使用者排程 |
| 公司不同 assistant ID、RAG 與 session／副作用 | not_tested；須完成公司 adapter 能力驗收 |
| AD／Oracle 真實資料及授權 | not_tested；沿用公司工作單 |
| 真中文輸入法／Excel 貼上 | not_tested；程式測試不替代人工驗收 |
| 不看手冊的同仁走查 | not_tested；不能以程式 GUI 測試宣稱直觀性已通過 |
| 隔日實際八點與 Norton 成效 | not_tested；受控時鐘不等同隔日等待，未修改防毒設定 |

## 介面與相容

收合側欄的品牌圖示已修正為置中，展開時恢復圖示＋文字排列。以真 Tk、深淺主題、1050×700 及目前 150% 倍率確認：修正前品牌中心偏左 14 實體像素，修正後與側欄及功能按鈕中心一致。`tests.test_team_navigation` 10 項通過；離線交付時另完成上述 364 項完整回歸。

本機真 Windows／Tk 的深淺通知畫面已實際檢視：1050×700 邏輯視窗、150% 顯示下，徽章可見、彈窗位於工作區右下角且按鈕可達；新通知前後輸入焦點一致、無模態 grab，主視窗最小化時彈窗仍可見且主視窗保持最小化。數據見 [display-current.json](validation/display-current.json) 的 notifications_0_12_1。這是合成資料與程式操作證據，不代替公司實測或同仁人工可用性驗收。

用暫存資料開啟真 Tk，已檢視深淺主題、1050×700、1280×860及最大化；送出、修改和確認按鈕可達，另檢視步驟編輯及助理詳情視窗。助理團隊小視窗單欄、一般視窗雙欄；窄圖示側欄與未讀徽章可見。量測見 [display-current.json](validation/display-current.json) 的 workspace_0_13_0。只保留四張當前精選圖：深淺 Plan、助理團隊及窄側欄；舊圖由 Git 歷史查看。未宣稱已完成所有實際 Windows 倍率或跨螢幕重排驗收。

schema 1～4 先備份、再交易升級為 5；舊公司資料庫不在本次操作範圍。若需降版，須停用新版並由維護者回復一致性備份，不直接降低 user_version。[乾淨重建](validation/clean-rebuild.json) 為先前環境證據；[離線重建](validation/offline-rebuild.json) 已更新為本次交付實測，依賴沒有變更。

## 人工走查

1. 開 start-trial.bat，選「規劃工作」，描述昨天 A 類日報；補條件、修改一次計畫。
2. 核對目標助理與來源，按一次「確認執行」，查看每步及最終成果，打開原始表格複製／匯出。失敗只停止並保留成果，不自行重送。
3. 設定每日八點，現在測試一次並暫停；重開找到結果及同一排程。
4. 測試取消、失敗後明確重試、刪除來源後獨立流程仍可管理。
5. 依 [公司工作單](../COMPANY-HANDOFF.md) 接上核准助理與資料，記錄實際卡住位置和核對結果後才標 company_real_passed。

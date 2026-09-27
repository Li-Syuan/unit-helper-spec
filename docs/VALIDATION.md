# QA agent 0.11.0 驗證摘要

本版新增原對話確認、查詢結果與自動工作，SQLite 升級 schema 4；沒有新增套件或虛擬環境。正式驗證使用 `D:/unit-helper-spec/.venv/Scripts/python.exe`，恰好 CPython 3.10.4、Windows x64。

## 本輪回歸

2026-09-27 完整 **299 項測試通過，0 skipped**；命令、直譯器與完整輸出見 [development.json](validation/development.json)。`scripts/verify.py development` 的環境診斷、pip check、鎖檔一致性及完整 unittest 均通過。保留既有263項行為基準，新增36項操作服務與真Tk旅程測試；輸入区改為1～4行後同步更新展開／收回斷言。

首輪發現活動頁偏好未登記、條件式按鈕舊斷言及文字整理誤判為查詢，未記為通過；修正後重跑。獨立流程檢查發現舊修訂取消、新舊解析刷新、Plan／卡片交易及來源提示問題，均納入修正與測試。

29 個鎖定套件不變，沿用唯一開發環境。舊 [乾淨重建](validation/clean-rebuild.json) 與 [離線重建](validation/offline-rebuild.json) 各192項是既有0.8.0證據，不代表本輪重跑；不重建離線包。

## 旅程與界線

| 項目 | 結果與限制 |
|---|---|
| 首次查詢 | local_real_passed：真 Tk 按範例、送出、確認；此前零查詢，原對話得到表格；不需 API key |
| 補條件／批准 | local_real_passed：catalog 欄位、純驗證、修訂、過期、目的綁定、取消及雙擊防重；先批准才派發 |
| 文字整理 | mock_passed／local_real_passed：真 Tk Enter 送出、範本只填草稿；普通文字不因含查詢字眼被攔截 |
| 日報 | external_real_passed：Groq 解析完整需求／缺條件追問，確認後合成查詢→真實摘要→通知，立即執行不改原時間；[安全紀錄](validation/report-trial.json) |
| 公司與外部隔離 | mock_passed：未配置公司模式不呼叫 Groq；模型 messages 與操作／表格分離；僅明示的轉交或日報授權送資料 |
| 失敗與取消 | local_real_passed／mock_passed：部分失敗保留表格、晚到結果不覆寫；解析及取消後仍在處理的 future 阻擋刪除 |
| 重開與刪除 | local_real_passed：操作連結恢復不派發；刪來源保留獨立查詢／自動工作，來源標示已刪除 |
| schema 遷移 | local_real_passed：schema 1／2／3 升至4、可讀備份、交易故障回復、原資料保留；Plan與操作連結同交易後才派發 |
| 既有服務 | local_real_passed／mock_passed：待辦、草稿、多助理、Plan／選項、檔案、精度、表格、刪除、排程／通知與工具完整回歸 |
| 真 Tk 顯示 | local_real_passed（程式操作與目視截圖）：深淺、1050×700、1280×860及最大化；詳見下節 |
| 不看手冊的人工走查 | not_tested：尚無使用者／獨立人工實際操作，不能以自動測試宣稱直觀性已驗收 |
| 公司 chatbot／AD／Oracle | not_tested：需內部資訊與公司驗收；Groq不算公司通過 |
| 真中文 IME／Excel | not_tested：保留既有程式測試，真輸入法選字與Excel貼上需人工核對 |
| 隔日08:00與Norton | not_tested：受控時鐘不等於隔日等待；沒有可核對防毒紀錄，未更動防毒設定 |

外部請求全部使用虛構文字與合成資料、暫存資料庫；沒有修改使用者的正式對話、自動工作或公司設定。早期解析不符預期曾失敗，沒有假回覆替代；修正提示後明確重測通過。不保證自然語言每次解析完全正確，確認卡始終需要核對。

## 顯示證據

正式啟動 DPI 模式 system，本機 Windows 倍率150%。實際尺寸：1050×700邏輯→1575×1050，1280×860→1920×1290；最大化由可用工作區决定。原始截圖使用程式自身視窗及暫存合成資料，未擷取私人桌面。

[顯示量測](validation/display-current.json) 與 [使用手冊四張精選畫面](USER-GUIDE.md#介面參考)。完整檢查圖存忽略目錄 artifacts/action-preview，不累積到Git。100／125／150／200%尺寸換算測試保留，真Windows100／125／200%與跨螢幕即時重排仍not_tested。

## 人工接手走查

請讓未看手冊的同仁依序完成，記錄卡住位置與是否需要口頭提示：

1. 開啟 start-app.bat，試查一筆資料，確認後找到前五列與完整表格，返回原對話。
2. 輸入缺條件查詢，在原處補齊並確認；取消一次再修改，確認不會多跑。
3. 開啟 start-trial.bat，用虛構內容整理；選取一句加入待辦。
4. 說出每天八點日報需求，核對並勾選授權、確認啟用；現在測試一次、看結果、暫停。
5. 重開後找到同一自動工作；刪來源對話，確認工作仍在且來源已刪除。

紀錄只有實際完成後才能改為人工通過。公司項目填 [接手工作單](../COMPANY-HANDOFF.md)。

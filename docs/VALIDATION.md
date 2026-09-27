# QA agent 0.12.1 驗證摘要

目前保留對話式 Plan、多助理協作、固定流程排程及 schema 5；0.12.1 增加右下角通知彈窗與側欄未讀徽章。沿用 Python 恰好 3.10.4、Windows x64、唯一 .venv 與原有鎖定套件，沒有新增依賴、schema 或驗證環境。

## 本機回歸

完整 **347 項測試通過，0 skipped**。以 `.venv/Scripts/python.exe scripts/verify.py development` 執行環境診斷、pip check、鎖檔比對及完整 unittest；直譯器、時間、命令與輸出見 [development.json](validation/development.json)。保留原有 336 項涵蓋範圍，新增 11 項真 Tk 通知測試。

通知覆蓋右下角位置、未讀徽章、重複刷新、逾時／懸停、關閉保留未讀、啟動不重播、查看結果與原因、多則合併、99+、來源刪除、長文保留及 timer 清理。完整回歸後微調展開更多工具時通知仍排在前方，另外跑 `tests.test_notifications tests.test_action_ui` 共 30 項通過。

新增覆蓋：主代理追問／修訂、未批准零執行、各助理資料隔離、綁定及能力失效、未知工具與格式拒絕、精確 facts、取消晚到結果、防重、交易回復、schema 4 遷移與前版遷移、來源刪除、排程啟停／重啟／跨日重試、同一失敗步驟只建一個後繼工作。真 Tk 測試涵蓋模式與草稿保存、送出後清除與晚到保存、選取保留、原始表格跨頁複製及公式防護。

通知不產生工作、模型呼叫或排程，不改既有通知產生条件。

## Groq 與公司界線

`scripts/check-workflows.py --live` 已使用暫存資料庫、合成查詢及最多四次真實請求，完成規劃 → 查詢 → 分析 → 覆核 → 日報，再建立並暫停合成排程。結果見 [workflow-trial.json](validation/workflow-trial.json)。此入口預設不加 --live 為 not_tested、零請求。

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

本機真 Windows／Tk 的深淺通知畫面已實際檢視：1050×700 邏輯視窗、150% 顯示下，徽章可見、彈窗位於工作區右下角且按鈕可達；新通知前後輸入焦點一致、無模態 grab，主視窗最小化時彈窗仍可見且主視窗保持最小化。數據見 [display-current.json](validation/display-current.json) 的 notifications_0_12_1。這是合成資料與程式操作證據，不代替公司實測或同仁人工可用性驗收。既有四張精選截圖保留，不累積本輪截圖至 Git。

用暫存資料開啟真 Tk，已檢視深淺主題、1050×700、1280×860及最大化；送出、修改和批准按鈕可達，另檢視步驟編輯視窗。量測見 [display-current.json](validation/display-current.json) 的 workflow_0_12_0。精選工作區圖已替換為新版 Plan 畫面，紅色錯誤提示圖保留；沒有累積歷代截圖。未宣稱已完成所有實際 Windows 倍率或跨螢幕重排驗收。

schema 1～4 先備份、再交易升級為 5；舊公司資料庫不在本次操作範圍。若需降版，須停用新版並由維護者回復一致性備份，不直接降低 user_version。原有 [乾淨重建](validation/clean-rebuild.json) 與 [離線重建](validation/offline-rebuild.json) 為先前環境證據，這次依賴未變、未重建環境。

## 人工走查

1. 開 start-trial.bat，選「規劃工作」，描述昨天 A 類日報；補條件、修改一次計畫。
2. 核對目標助理與來源，批准試跑，查看每步及最終成果，打開原始表格複製／匯出。
3. 設定每日八點，現在測試一次並暫停；重開找到結果及同一排程。
4. 測試取消、失敗後明確重試、刪除來源後獨立流程仍可管理。
5. 依 [公司工作單](../COMPANY-HANDOFF.md) 接上核准助理與資料，記錄實際卡住位置和核對結果後才標 company_real_passed。

# QA agent 0.8.1 驗證摘要

本版整理目前目錄與接手入口，不改 UI 行為、SQLite schema、使用者資料或依賴。測試與素材仍按實際證據區分，不能把本機通過視為公司接線完成。

## 本輪回歸

2026-09-27，使用 `D:/unit-helper-spec/.venv/Scripts/python.exe`，恰好 CPython 3.10.4、Windows x64。執行 `scripts/verify.py development`：doctor、pip check、freeze 與 requirements.lock 比對全部成功，完整 **192 項測試通過，0 skipped**。

- [開發環境完整輸出](validation/development.json)：本輪更新。
- [乾淨重建環境輸出](validation/clean-rebuild.json) 與 [離線重建環境輸出](validation/offline-rebuild.json)：保留 0.8.0 基準，各 192 項通過；不是本輪重建／重跑。依賴未變，不重建環境與離線包。
- 29 個鎖定套件、全部既有測試、公司測試範本、合成 fixtures、授權文字與正式執行素材保持不變。

## 覆蓋與驗收界線

| 項目 | 證據與限制 |
|---|---|
| SDK 契約 | mock_passed：真 SDK 搭配合成 transport；請求、解析、401、逾時、空回覆、格式錯誤、隔離與 TLS。不是公司 API 實測 |
| 本機服務 | local_real_passed：SQLite、Plan 未批准零派發、修訂／過期／防重、選項、取消後 future 收尾、多助理固定路由及轉交 |
| 檔案／表格 | local_real_passed：大小／編碼、精確字串、公式防護、CSV／TSV、選取與跨頁輸出；Excel 自動轉型另驗 |
| 排程／通知 | local_real_passed：可控制時鐘的每日／每週、漏跑、重啟防重、日期映射、啟停與失敗通知 |
| 對話刪除 | local_real_passed：單筆／批次／搜尋、目前／最後一筆、執行與取消收尾阻擋、預覽過期、交易回復、重複確認、晚到結果及轉交副本 |
| Tk 與工具 | local_real_passed（程式操作）：真 Tk 控制項、原地提示、主題與狀態保持、離線手冊、Windows clipboard、品牌素材、COM 捷徑建立／搬移／同名保護、固定啟動檢查 |
| 憑證 | local_real_passed：Windows keyring 獨立測試項目保存／讀取／更換／移除，測後清除；拒絕明文 fallback，不使用真實 API key |
| 公司服務 | not_tested：chatbot、AD／員工名單、Oracle 尚需內部資訊及核准接線 |
| 人工操作 | not_tested：OS 滑鼠鍵盤全流程、真實中文 IME、Excel 真實貼上、工作列／桌面最終外觀 |
| Norton | not_tested／未能確認：沒有可核對防毒歷程；測試成功不代表警告消失，未變更防毒或執行政策 |

公司驗收填寫 [接手工作單](../COMPANY-HANDOFF.md)。一般 doctor 不呼叫公司助理或資料庫，company_check 未配置項目保持 not_tested。

## 顯示證據

沿用未改動 UI 的既有量測：[啟動基準](validation/display-baseline-v080.json)、[本機 150%](validation/display-v080.json)、[合成 100%](validation/display-sim100-v080.json)。四張現行介面參考集中於 [使用手冊](USER-GUIDE.md#介面參考)，拍攝版本為 0.8.0，不冒稱本輪新截圖。

- 本機實際 150%：感知模式 system、Tk scaling 約 1.998、DPI 約 143.86，工作區 2560×1528；一般 1920×1290、最小 1575×1050、最大化 2560×1494。本文／輸入固定微軟正黑體 12 點，不隨最大化拉伸字型。
- 已有深淺一般／最小／最大化、管理／刪除、長 Plan、選項與表格的原始量測；本版只保留深色、淺色、管理與刪除四張圖，其他畫面可從 Git 歷史查閱。
- 自動測試涵蓋 100／125／150／200% 換算與素材載入；真 Windows 100／125／200% 與跨倍率螢幕移動仍 not_tested，模擬不能代替實際切換。跨螢幕即時重排不在本版。

公司可執行 `.venv/Scripts/python.exe scripts/display-check.py --output artifacts/diagnostics/display.json`，在目標螢幕比較一般／最大化；詳見 [開發指南](DEVELOPMENT.md)。

## 倉庫整理檢查

清理基準為 [c13e583](https://github.com/Li-Syuan/unit-helper-spec/tree/c13e583)。目前分支移除歷史文件、舊 DTO 範例／Oracle 設計、規格 ZIP、候選圖示、舊截圖與 HTML／CSS 視覺稿；不建立 archive 副本、不改寫 Git 歷史。

| 項目 | 整理前 | 整理後 |
|---|---:|---:|
| Git 管理檔案 | 398 | 298 |
| Markdown 文件（含 Copilot） | 42 | 17 |
| 根目錄 Markdown | 18 | 3 |
| 介面截圖 | 45 | 4 |

移除 103 個舊檔，新增 3 份整併文件。數量只計 Git 管理內容，不含 `.venv*`、`.runtime`、wheelhouse 或使用者資料；完整 clone 的歷史下載體積不因此同步縮小。

檢查保留 Markdown 的本機連結；應用手冊章節、素材及不同工作目錄載入由完整回歸覆蓋。以 c13e583 逐檔比對確認 tests、test_support、company_templates、授權文字、依賴及正式 runtime 素材未改；程式只變更版本常數，兩個啟動入口僅更新文件提示。

`start-app.bat --check` 成功；`scripts/doctor.py --human --output artifacts/diagnostics/readiness-v081.json` 成功且公司項目仍 not_tested。manifest 重建後再次校驗。診斷分享報告留在忽略目錄，不新增重複發布材料。

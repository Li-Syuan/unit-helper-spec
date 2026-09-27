# QA agent 0.9.1 驗證摘要

本版將已選深淺品牌圖示套用至側欄、主視窗及附屬視窗；沿用個人待辦、工作卡片、文字草稿、公司 adapter、Plan gate、查詢與排程。schema 維持 3，不新增資料遷移或套件。

## 本輪回歸

2026-09-27，使用 `D:/unit-helper-spec/.venv/Scripts/python.exe`，恰好 CPython 3.10.4、Windows x64。執行 `scripts/verify.py development`：doctor、pip check、freeze 與 requirements.lock 比對成功，完整 **228 項測試通過，0 skipped**；保留原有 192 項所涵蓋的行為。

- [本輪開發環境完整輸出](validation/development.json)。
- [乾淨重建](validation/clean-rebuild.json) 與 [離線重建](validation/offline-rebuild.json) 保留 0.8.0 各 192 項基準，不代表本輪重跑。29 個鎖定套件未變，本輪不重建環境或離線包。
- 啟動檢查、手冊章節、Markdown 本機連結及 manifest 分別校驗。

## 覆蓋與驗收界線

| 項目 | 證據與限制 |
|---|---|
| 主題圖示 | local_real_passed：兩款七尺寸 PNG／ICO、透明外角、保存主題開啟、切換更新原有／後開視窗與側欄、缺淺色包提示並退回深色；切換零工作派發 |
| 待辦 | local_real_passed：真 SQLite 與 Tk 新增、長文字／日期驗證、搜尋、排序、狀態切換、刪除取消、重複保存、來源刪除後保留；台北日期邊界使用可控制時鐘 |
| 工作卡片 | local_real_passed：只填草稿、原稿與附件保留、同助理新對話、用途顯示；預覽及新增待辦零模型派發 |
| 草稿 | local_real_passed：延遲保存、重開恢復、附件重選提示、快速切換、失敗重試、送出失敗補存、晚到寫入失效、Plan 編輯隔離、刪除競態與正常關閉補存 |
| 遷移及交易 | local_real_passed：schema 1／2 升級與備份、schema 2 故障回復、現有資料保留；工作／Plan 受理與草稿移除同交易，失敗回復且零派發 |
| SDK 契約 | mock_passed：真 SDK 搭配合成 transport；請求、解析、401、逾時、空回覆、格式錯誤、隔離與 TLS。不是公司 API 實測 |
| 既有本機服務 | local_real_passed：Plan gate、修訂／過期／防重、選項、取消收尾、多助理路由、資料轉交、對話批次刪除與交易回復 |
| 檔案／查詢／排程 | local_real_passed：UTF-8、CSV／TSV、精確字串及公式防護、動態參數、每日／每週、漏跑／重啟防重及通知；Excel 實際貼上另驗 |
| Tk 與工具 | local_real_passed（程式操作）：真 Tk、主題與狀態保持、Enter／Shift+Enter 既有保護、離線手冊、Windows clipboard、素材、COM 捷徑建立／搬移／同名保護及固定啟動檢查 |
| 憑證 | local_real_passed：Windows keyring 獨立合成項目保存／讀取／更換／移除並清除；不使用真實 API key |
| 公司服務 | not_tested：chatbot、AD／員工名單、Oracle 尚需內部資訊及核准接線 |
| 人工操作 | not_tested：OS 滑鼠鍵盤全流程、真實中文 IME、Excel 真實貼上、工作列／桌面最終外觀 |
| Norton | not_tested／未能確認：沒有可核對防毒歷程；未變更防毒或執行政策，測試通過不代表警告消失 |

公司驗收填寫 [接手工作單](../COMPANY-HANDOFF.md)。doctor 不呼叫模型或資料庫；company_check 未配置項目保持 not_tested。

## 顯示證據

以獨立暫存資料與合成內容，程式操作真 Tk 並擷取本應用視窗，檢視深淺主題的一般、1050×700 邏輯尺寸與最大化聊天／待辦，以及待辦編輯與草稿畫面。共 14 張檢查圖留於忽略的 artifacts；倉庫只保留 [使用手冊](USER-GUIDE.md#介面參考) 中四張本版精選畫面，替換舊圖。

- [本輪視窗量測](validation/display-current.json)：正式 DPI 啟動方式由 unaware 設為 system，本機實際倍率 150%，Tk scaling 約 1.998，DPI 約 143.86。一般 1920×1290、最小 1575×1050、最大化 2560×1494 實體像素。
- 看板可用寬度不足 900 邏輯像素切換狀態分頁；一般與最大化呈現三欄。小視窗的輸入區、送出與草稿提示保留空間。
- 另以最小視窗檢查「已加入我的待辦」提示、送出及草稿狀態均可見，保存提示不強制切換頁面。
- 自動測試涵蓋 100／125／150／200% 換算與素材；真 Windows 100／125／200% 及跨倍率螢幕移動仍 not_tested，不以模擬代替。
- 截圖檢視與程式操作不等於人工鍵盤／IME 驗收。公司可依 [開發指南](DEVELOPMENT.md) 執行 display-check，在目標螢幕核對。

## 資料及交付

待辦與 AI 工作分開保存；使用者標為完成不會變更工作結果。刪除來源對話會同時清除草稿，另存待辦仍可編輯，來源標示已刪除。原始附件、匯出及備份保持原界線。

不新增執行期依賴、中央服務或背景通知，不接觸公司原始資料庫。文件保持目前功能與公司接線入口，未重新累積歷史規格或候選素材。

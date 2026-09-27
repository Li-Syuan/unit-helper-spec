# QA agent 0.9.2 驗證摘要

本版新增隔離的 Groq 外部 AI 試用入口；沿用深淺品牌圖示、個人待辦、工作卡片、文字草稿、公司 adapter、Plan gate、查詢與排程。schema 維持 3，不新增資料遷移、套件或虛擬環境。

## 本輪回歸

2026-09-27，使用 `D:/unit-helper-spec/.venv/Scripts/python.exe`，恰好 CPython 3.10.4、Windows x64。執行 `scripts/verify.py development`：doctor、pip check、freeze 與 requirements.lock 比對成功，完整 **241 項測試通過，0 skipped**；包含原有 228 項與新增 13 項試用測試。

- [本輪開發環境完整輸出](validation/development.json)。
- [乾淨重建](validation/clean-rebuild.json) 與 [離線重建](validation/offline-rebuild.json) 保留 0.8.0 各 192 項基準，不代表本輪重跑。29 個鎖定套件未變，本輪不重建環境或離線包。
- 啟動檢查、手冊章節、Markdown 本機連結及 manifest 分別校驗。

## 覆蓋與驗收界線

Groq 試用新增驗證：

- mock_passed：真 OpenAI SDK 搭配合成 transport，固定目的地／模型、對話隔離、401／403／429／500、逾時、連線失敗、空回覆、格式錯誤、不完整回覆與工具要求拒絕；零自動重試、錯誤不含服務原文。
- local_real_passed：.env 格式／大小／重複鍵／不展開變數、唯讀 profiles、Windows 信任庫且 TLS 強制驗證；真 Tk 啟動不派發、公司設定未讀寫、獨立子目錄、Enter 送出與 Plan 批准後單次派發。
- external_real_passed：真實 Groq 短句連線，以及真 Tk 中兩筆虛構筆記摘要／接續追問；只記安全狀態於 [外部試用紀錄](validation/external-trial.json)。這是第三方外部服務，不能歸為 company_real_passed。
- 深淺試用聊天與設定的 1050×700 邏輯尺寸截圖留在忽略的 artifacts/trial-preview，已目視檢查按鈕及標示；未把私有 .env 或回覆日誌提交。
- 真實中文 IME、公司 chatbot／AD／Oracle、Excel 與 Norton 成效仍 not_tested；沒有更動防毒設定。

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

一般工作區沿用 0.9.1 的顯示證據：以獨立暫存資料與合成內容，檢視深淺主題的一般、1050×700 邏輯尺寸與最大化聊天／待辦，以及待辦編輯與草稿畫面。共 14 張檢查圖留於忽略的 artifacts；倉庫只保留 [使用手冊](USER-GUIDE.md#介面參考) 中四張精選畫面。本輪新增試用畫面檢查見上方，沒有重做這組截圖。

- [本輪視窗量測](validation/display-current.json)：正式 DPI 啟動方式由 unaware 設為 system，本機實際倍率 150%，Tk scaling 約 1.998，DPI 約 143.86。一般 1920×1290、最小 1575×1050、最大化 2560×1494 實體像素。
- 看板可用寬度不足 900 邏輯像素切換狀態分頁；一般與最大化呈現三欄。小視窗的輸入區、送出與草稿提示保留空間。
- 另以最小視窗檢查「已加入我的待辦」提示、送出及草稿狀態均可見，保存提示不強制切換頁面。
- 自動測試涵蓋 100／125／150／200% 換算與素材；真 Windows 100／125／200% 及跨倍率螢幕移動仍 not_tested，不以模擬代替。
- 截圖檢視與程式操作不等於人工鍵盤／IME 驗收。公司可依 [開發指南](DEVELOPMENT.md) 執行 display-check，在目標螢幕核對。

## 資料及交付

待辦與 AI 工作分開保存；使用者標為完成不會變更工作結果。刪除來源對話會同時清除草稿，另存待辦仍可編輯，來源標示已刪除。原始附件、匯出及備份保持原界線。

不新增執行期依賴、中央服務或背景通知，不接觸公司原始資料庫。文件保持目前功能與公司接線入口，未重新累積歷史規格或候選素材。

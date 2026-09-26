# 常用工作、引導查詢與 Excel 複製（v2.2）

## 1. 目的與範圍

UH-13 讓不熟悉助理問法的同仁不用輸入提示詞，就能選工作、填條件並取得資料。UH-14 讓同仁將結果貼進既有 Excel 報表。快速回報沿用 UH-08。這些是現有工具的操作入口，不建立另一套助理或查詢引擎。

首頁／新對話提供「查公司資料」「整理內容」「修改文字」，保留自由輸入與一般／先規劃切換。「整理內容」「修改文字」分別打開既有輸入／預覽流程，不增加 Office 原檔編修。收藏查詢、Excel 自動操控、固定範本產檔與評分儀表板不在首版。

## 2. 常用查詢與引導操作

1. 點「查公司資料」取得 GET /queries，只顯示本人有權且 enabled 的三項核准查詢；按目錄 display_order 排列，同序以 query_id 排序。
2. 每項顯示工作名稱、用途、一個問法範例及預期欄位。真實名稱與口徑由公司補齊，示範占位不可正式啟用。沒有可用查詢時顯示說明與回報入口，不讓模型猜替代資料來源。
3. 根據模板參數產生日期／文字／單選／多選欄位；必填與錯誤就地提示。選項值只取自受控目錄且必須符合 parameter_schema，不能由模型臨時擴大範圍。單位等 server 注入參數不可顯示成可編輯欄位。
4. 同一表單底部顯示查詢名稱、固定版本、日期範圍與已填條件。一般模式按「查詢」直接送出，無第二層確認；先規劃模式按「產生計畫」，沿用 Plan 卡與確認端點，不能轉直接查詢規避確認。
5. 一般模式成功後顯示表格，可另按「解釋結果」。資料表可先獨立使用，不必等摘要成功才複製。Plan 若含摘要則沿用 query → summarize 行為。

日期欄位依公司核准口徑；只在目錄宣告 date_range 對應的參數上提供「今天／昨天／自訂」，不對任意參數猜日期。預設昨天，立即顯示轉換後的絕對日期與時區；自訂可改。後端重新計算與驗證相對日期；畫面跨日則刷新摘要，使用者再次按查詢／確認才送出，不靜默換日期。範圍採既有 inclusive-start/exclusive-end。

表單沿用既有 typed values 和 QuestionForm 的校驗服務；固定查詢表單可以一次顯示所有欄位，對話內選項仍遵守每卡最多三題。切換查詢清除不相容欄位並告知，不能把上一查詢參數偷偷帶到另一模板。送出中防雙擊並沿用 request ID；後端每次仍驗權與查詢狀態。

## 3. 查詢目錄與 API

GET /queries 新增可選 display 物件；沿用 name、description、parameter_schema、output_columns，禁止返回 server_sql、連線或 scope 內部設定。display 包含：

- purpose、example_prompt、display_order。
- parameters：以參數名稱為 key，值為 label、help、control(text/datetime/single_choice/multi_choice)、options（可選，[{label,value}]）。選項值必須與參數 schema 的型態及 enum 相符；multi_choice 只對 array 參數。缺省按 schema 型態顯示基本欄位，不自動猜選項。
- date_range（可選）：start_parameter、end_parameter、timezone、presets、default_preset；presets 首版只容許 today/yesterday/custom，default_preset=yesterday；只有起訖參數符合已核准日期語意才配置。

output_columns 擴充 label 與 copy_as_text（可選 boolean）；陣列順序即顯示與輸出順序。copy_as_text 用於識別碼、高精度數字等不可任意轉型欄位，不改來源資料型態。label 缺省 name。這些展示 metadata 固定於 query version，保存結果時一併保存；舊結果不隨新版目錄改欄序／標題。沒有新 metadata 的舊模板可用基本表單，原用戶端忽略新欄位即可。

一般模式仍用 POST /queries/{id}/runs；Plan 以既有 request 端點新增可選 query_ref、parameters 作為明確的查詢候選，mode=query、interaction_mode=plan。後端據此產生固定計畫並驗證目錄，不需 LLM 選模板，不把候選視為批准。query_ref 與 parameters 成對提供，且僅允許 mode=query；缺省時保留原自然語言流程。

日期快捷選擇在 runs／requests 增加可選 date_selection={preset,preview_local_date}；preset 為 today/yesterday/custom，日期字串 YYYY-MM-DD 是畫面預覽基準日。today/yesterday 由後端按目錄時區計算起訖，核對 client parameters 及當地日期；不一致回 409 date_preview_stale 並要求刷新，不執行。custom 使用明確起訖並驗證範圍，不因跨日拒絕固定日期；無此欄位視為原有明確參數。Plan snapshot 保存 date_selection，confirm 再驗相對日期基準。

GET /tasks/{id}/result 的 columns 加 label/copy_as_text，沿用 rows、cursor、row_count、truncated 等。snapshot 由成功 task ID 固定識別；同一 task 完成後結果不可原地替換，重跑建立新 task。不新增剪貼簿 API 或中央資料表；display 從受控 query catalog 載入，現有結果 JSON 保存欄位 metadata。

## 4. 複製結果

表格新增「複製全部結果」「複製選取列」及「包含欄名」勾選，預設包含。選取只限目前頁面，換頁清除選取並更新筆數；首版沒有跨頁選取或使用者重新排列欄位。複製全部表示同一 snapshot 已取得的全部列（最多既有 1,000 列），不是只複製畫面 100 列，也不宣稱取得被截斷的剩餘資料。

按鈕旁顯示準備複製的筆數。背景分頁取得同 task 的 snapshot，沿用授權／期限檢查；中途讀取失敗、撤權或過期不提交部分內容到剪貼簿，也不另跑 SQL。整批準備完成後回到 Tk 主執行緒寫剪貼簿。選取列複製前亦重新確認該 task 結果仍可讀；已複製出去的資料無法靠後續撤權收回。

複製格式為 Unicode TSV：欄間 Tab、列間 CRLF，不附 Markdown 圍欄或助理摘要。欄序取 snapshot，null 複製為空欄；空字串與 null 在貼上表格中均呈空白，來源 snapshot 仍保留差異。日期採來源 ISO 字串，Decimal／識別碼不經浮點轉換，沒有千分位／四捨五入／本地化重寫。

任何本次選取的欄名或值含 Tab、CR、LF、NUL 時，停止該次複製，提示改用現有 CSV 匯出，不悄悄刪字、不冒險拆成錯誤行列。檢查僅涵蓋此次要複製的資料。

文字欄經去除前導空白後若以 =、+、-、@ 開頭，於輸出原字串前加單引號，沿用 CSV 共用的公式防護服務；原 snapshot 不變。真數值欄只有通過型態驗證才按數值處理，不把任意字串當數值跳過防護。畫面提示已保護的儲存格數，不能默默宣稱貼上值完全未改。若公司既有 CSV 防護更嚴格則對照採用並記錄，不能降低本規格驗收。

涉及 copy_as_text 欄位時，顯示「貼上前請將 Excel 對應欄設為文字，避免工號／長數字改變」。是否保持內容須以公司實際 Excel 貼上驗證；不保證任意目標格式自動保留型態。高精度數字以文字保真；需要計算時由使用者按報表需求另行轉換。不操控 Excel、不覆寫活頁簿。

無資料或未選列時停用相應按鈕；truncated 時持續標示「僅複製已取得的 N 筆，結果非完整資料」。成功顯示筆數及是否含欄名，不把標題算資料列。剪貼簿被占用／寫入失敗要明示，可由使用者重試；不顯示假成功。CSV 匯出保留原入口。

## 5. 快速回報與驗收

結果旁「沒有解決我的問題」只打開既有 issue 草稿，預填問題類型及版本／功能／trace ID；描述由本人補充。資料／對話 refs 仍預設不勾選，沒有新的自動提交、模型評分、事件蒐集或統計表。

依 IMPLEMENTATION.md AT-22～AT-27 驗收。主要使用情境是同仁不打提示詞，透過工作名稱與選項完成一次查詢，將結果貼到公司既有 Excel。試用記錄實際卡點，之後再決定是否加入收藏查詢。

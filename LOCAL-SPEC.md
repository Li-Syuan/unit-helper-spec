# QA agent 本機桌面 0.5.0 範圍與行為契約

此文件優先於 v2.2 中涉及中央後端、遠端更新的假設；其餘完整產品規劃保留作後續路線。

## 分層

| 模組 | 責任 |
|---|---|
| desktop_app/ui.py | Tk 畫面、主執行緒事件、背景 IO 回傳、表格／預覽 |
| desktop_app/core.py | Store、任務／Plan gate、受限工作流程、本機排程與通知 |
| desktop_app/choices.py | 持久化 typed 選項、owner／版本／期限／一次提交 |
| desktop_app/gateways.py | 身分、公司 OpenAI 相容助理、查詢介面與合成實作 |
| desktop_app/files.py | UTF-8 上傳驗證、CSV／TSV 安全輸出 |
| desktop_app/query_schema.py | 動態欄位、純型別驗證、顯示與日期映射 |
| desktop_app/config.py | 本機設定、資料路徑、單一執行個體鎖 |

UI 不直接持有 SQL、密碼或 HTTP 細節。公司差異先集中 gateways.py；未來需要獨立 adapter 檔可在保持介面下拆出，不重寫 UI。

## 對話、Plan 與選項

對話歷史完整保存，送給 SDK 時使用指定對話的不可變快照；同一對話尚有工作則拒絕重疊提交。總內容超限拒絕，不靜默裁切。
一般模式明確送出即執行。先規劃模式只建立本機固定候選，不呼叫 bot。只有 `confirm_plan` 成功才建立工作；24 小時期限、修訂比對、原子交易與 request ID 防止舊卡片／雙擊重跑。修改需重新批准。流程限查詢、查詢後摘要、對話、摘要、改寫。

選項有 yes_no／single_choice／multi_choice；最多 3 題，每題 2～6 選項。未選不當同意，未知值與數量不符拒絕；owner、version、expiry、request ID 由本機服務檢查。取消後不可提交。選項答案不等於任意工具授權。「是，設排程」只開設定，仍建立停用草稿並另確認啟用。重開待答表單可保存答案，**不重播先前 UI callback**，使用者回原工作繼續。

取消在派發界線前阻止新助理呼叫；界線後可能已送出至公司，不能保證遠端撤回。晚到結果不寫回已取消工作。已完成查詢表格可保留，摘要失敗不重跑查詢。未結束的真實 future 會阻擋切換設定，即使工作已標取消。關閉等待遠端 drain 後才釋放資料目錄鎖。
沒有持續自主 Goal、通用 shell／任意 SQL、產品 runtime 多 agent。

## 檔案與結果

單一 TXT／CSV，2 MiB、UTF-8／UTF-8 BOM；TXT 最多 50,000 字，CSV 最多 10,000 列／100 欄。標題空白／重複、列寬不一致、NUL、錯誤編碼拒絕。預覽 TXT 前 2,000 字、CSV 前 20 列，送出完整內容；超過助理設定上下文上限則拒絕。沒有多文件、Office 原檔排版修改。

三項 DEMO01～03 為獨立合成查詢。固定日期區間起含迄不含，1～90 日，category all/A/B。最多 1,000 列與 2 MiB，截斷有標記。正式 Q01～03／Oracle 保持停用。
表格 100 列一頁，全部複製跨所有頁；選取列只限當页、換頁清除選取。輸出只讀同一 snapshot，不另查資料。數值用精確十進位字串，拒絕 float。公式型文字加前置 apostrophe；TSV 分隔字元拒絕並提示改 CSV；CSV 有 BOM、標準 quoting。程式保留精確字串，**Excel 自動推斷可能改變代碼／長整數，貼上前要設文字格式；真正 Excel 貼上尚待公司驗收**。不以 `="..."` 公式包裹值。

## 本機排程

每日／每週、HH:MM、星期 0～6；台北 UTC+8 固定時區。成功查詢才可建立，初始停用；啟用前顯示未來三次 UTC 時間及參數。固定參數或每次前一日；後者必須由模板宣告 date_range，依該次預定執行時間解析起含迄不含日期。未宣告者不能使用；舊 DEMO 排程僅對 DEMO01～03 保留明確相容映射。

程式每 3 秒檢查，`unique(schedule_id,scheduled_at)` 防重。同排程不重疊。關閉期間最新 24 小時最多補跑一次，較舊紀錄以壓縮略過標記保存。重開未完成工作標失敗、不自動重送。停用期間不追補。這是單機防重，不宣稱跨機 exactly-once 或分散式 lease。

通知規則：非空且內容 hash 改變；或單一數值首次達標／由未達標轉達標。取得時間不納入 hash。失敗通知一次。只有唯讀查詢的 ConnectionError／TimeoutError 可有限重試，最多 3 次；公司助理一律不自動 retry。站內通知未讀數可見，無郵件或 OS 背景常駐服務。

## 資料與回報

獨立 `local-v1.sqlite3`、schema user_version=1、WAL；首次建檔，不接觸舊公司 SQLite。較新 schema 拒絕開啟。單一資料目錄只能一個程式使用；不把本機檔案當授權系統。
回報 draft 可讀取修改，local_saved 只表示保存在此電腦；編號 LOCAL-*。不自動附加對話、資料或檔案，不冒稱管理者已收到。未實作處理狀態同步／修正版本管理。
資料移轉、中央 API、AD、Oracle、簽章更新及 EXE 打包均另列交接；禁止將原 v2.2 相關 AT 記成已通過。

## 0.4.0 公司接手準備

catalog 的參數定義支援 text/date/integer/decimal/single_choice/boolean、required/default 與適用範圍。UI、Plan 修改與預覽、結果條件及排程共用定義；decimal 保持文字，未知欄位／模板或不支援定義拒絕。adapter.validate 仍為純驗證且保有查詢商業規則；一般送出／批准與排程服務均檢查。細節見 docs/QUERY-CATALOG.md。

本機診斷不連網、逐项收集結果與白名單分享報告；company_acceptance 不因本機通過而改為通過。離線套件包綁定 requirements.lock 指紋與各 wheel SHA-256，缺失或損壞停止，無連外 fallback。雜湊保護傳輸完整性，不是公司發布簽章。

test_support 包含可重用 adapter 契約，company_templates 提供待填測試骨架，company_check 必須明確啟動且完成公司能力審查才載入可信 hooks。無 hooks 或缺項是 not_tested，不能以 demo／skip 替代公司驗收。不包括正式 AD、Oracle 或舊資料移轉。

## 0.5.0 深淺主題與候選圖示

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

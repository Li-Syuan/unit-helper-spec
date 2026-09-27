# QA agent 本機桌面 0.8.0 範圍與行為契約

此文件優先於 v2.2 中涉及中央後端、遠端更新的假設；其餘完整產品規劃保留作後續路線。

## 分層

| 模組 | 責任 |
|---|---|
| desktop_app/ui.py | Tk 畫面、主執行緒事件、背景 IO 回傳、表格／預覽 |
| desktop_app/guidance.py | 八頁原地提示、狀態說明及對應手冊入口；只讀取 UI 現況 |
| desktop_app/experience.py | 離線手冊、關於與環境診斷入口；不再啟動獨立體驗 |
| desktop_app/core.py | Store、任務／Plan gate、受限工作流程、本機排程與通知 |
| desktop_app/choices.py | 持久化 typed 選項、owner／版本／期限／一次提交 |
| desktop_app/gateways.py | 身分、公司 OpenAI 相容助理、查詢介面與合成實作 |
| desktop_app/files.py | UTF-8 上傳驗證、CSV／TSV 安全輸出 |
| desktop_app/query_schema.py | 動態欄位、純型別驗證、顯示與日期映射 |
| desktop_app/config.py | 本機設定、資料路徑、單一執行個體鎖 |

UI 不直接持有 SQL、密碼或 HTTP 細節。公司請求映射與憑證集中 profiles.py，SDK 傳输維持 gateways.py；未來需要獨立 adapter 檔可在保持介面下拆出，不重寫 UI。

## 0.7.1 原地操作提示

啟動直接進入正常工作區；不再建立歡迎視窗、獨立體驗程序、暫存體驗工作區或五步控制器。一般示範助理及 DEMO 合成查詢繼續保留，操作會保存在目前個人歷史，所有示範標示保持明確。

對話、查資料、計畫與任務、查詢結果、我的排程、通知、設定、問題回報共八頁，在既有頁首說明區呈現簡短提示，說明目前狀態、下一步或阻擋原因；旁邊提供收合／展開及對應手冊章節。側欄「操作提示」切換目前頁面。提示不另外占用大型面板，也不需照固定導覽順序完成。

提示只讀取目前選定的對話／工作／資料狀態，不會建立對話、填入草稿、執行查詢、批准 Plan、發送資料或呼叫公司服務。更新或切換提示不得重建工作區或清除草稿、附件、文字／表格選取、游標、捲動及 Plan 修訂。必要身分與示範標示、錯誤、批准與轉交確認不受收合影響。

各頁偏好以 `ui-preferences.json` 的 `page_hints` 物件保存，頁面鍵對應布林值，true 表示展開；缺少或無效值預設展開。保存失敗保留當次選擇並顯示提示。舊 `onboarding` 欄位保留原值，但不再讀取或更新。不更動連線設定、服務契約、SQLite schema 或依賴。

## 對話、Plan 與選項

對話歷史完整保存，送給 SDK 時使用指定對話的不可變快照；同一對話尚有工作則拒絕重疊提交。總內容超限拒絕，不靜默裁切。
一般模式明確送出即執行。先規劃模式只建立本機固定候選，不呼叫 bot。只有 `confirm_plan` 成功才建立工作；24 小時期限、修訂比對、原子交易與 request ID 防止舊卡片／雙擊重跑。修改需重新批准。桌面流程限查詢、對話、摘要、改寫；查詢後整理須預覽並確認轉交。舊獨立 Engine 契約保留 query_summarize，但桌面的 routed Engine 拒絕直接自動整理。

選項有 yes_no／single_choice／multi_choice；最多 3 題，每題 2～6 選項。未選不當同意，未知值與數量不符拒絕；owner、version、expiry、request ID 由本機服務檢查。取消後不可提交。選項答案不等於任意工具授權。「是，設排程」只開設定，仍建立停用草稿並另確認啟用。重開待答表單可保存答案，**不重播先前 UI callback**，使用者回原工作繼續。

取消在派發界線前阻止新助理呼叫；界線後可能已送出至公司，不能保證遠端撤回。晚到結果不寫回已取消工作。已完成查詢表格可保留，摘要失敗不重跑查詢。未結束的真實 future 會阻擋切換設定，即使工作已標取消。關閉等待遠端 drain 後才釋放資料目錄鎖。
沒有持續自主 Goal、通用 shell／任意 SQL、產品 runtime 多 agent。

## 0.8.0 對話刪除契約

最近對話的右鍵提供單筆刪除；「管理對話」可依標題搜尋、勾選多筆與全選目前搜尋結果。變更搜尋條件會清除已被隱藏的選取，不把看不到的對話暗中加入刪除。確認顯示對話名稱與數量、訊息／Plan／工作／通知數量，預設焦點在取消，明示永久刪除與無法由應用復原。

Engine.preview_conversation_deletion(ids) 回傳 token、conversations、counts、task_ids、plan_ids；Engine.delete_conversations(token) 回傳同摘要及 deleted_ids。token 在服務端保存選定 ID 與完整資料快照指紋，10 分鐘有效，成功後失效；過期、重複或資料變更須重新預覽。確認時在引擎鎖內重新檢查，以單一 BEGIN IMMEDIATE 交易完成整批刪除；失敗全部回復，不改 schema。

範圍限選定對話、訊息、專屬 Plan、工作輸入／結果及其通知，以及該對話記憶體草稿／附件引用；待批准 Plan 一併刪除而不執行。排隊、執行中或取消後仍有未結束 future 的選定對話會阻擋整批刪除，不能只檢查畫面狀態，不能自動取消。其他對話的工作可以繼續；不正常的跨工作、Plan 或排程關聯拒絕刪除，不擴大範圍。

原始檔、匯出檔、既有備份、獨立查詢／排程、問題回報、選項表單、其他對話及轉交副本保留。轉交副本的來源不存在時顯示「來源對話已刪除」。公司端歷史不在範圍內；此操作不是安全抹除，也不自動新建含原內容的備份。

刪除後關閉選定資料的詳情及未送出轉交預覽，清除對應草稿及附件引用。刪除目前對話後切到最近保留對話；全部刪除後建立一個空白新對話，其他對話的草稿及附件保持不變。已刪對話不可由舊畫面或舊 Plan 再派發。

## 0.8.0 顯示與 DPI 契約

在建立 Tk 前設定 System DPI awareness；啟動環境已有更高感知模式時保留，不強制覆寫。display.py 集中處理顯示倍率與尺寸換算；以 100% 的邏輯像素為基準換算固定尺寸，避免字體放大而容器不變，或字型與容器重複縮放。微軟正黑體主要操作 11 點、聊天本文 12 點、次要提示至少 10 點。

圖示依倍率使用隨附的本機多尺寸素材；常用 24 邏輯像素圖示對應 24／30／36／48 像素，品牌沿用多尺寸資源，不放大小圖充當高解析。一般、拉大與最大化均由原生文字及控制項重排，不把介面當圖片拉伸。小螢幕／高倍率視窗須限制在可用工作區內，內容必要時可捲動，保留送出、取消、批准及刪除確認的操作路徑。

記錄 DPI 感知、螢幕倍率、Tk scaling、實際字型與視窗尺寸，診斷不包含公司內容。本機舊啟動路徑確認為 unaware；最大化的字型點數未改變，因此不能將最大化本身認定為模糊原因，也不宣稱 DPI 是唯一因素。跨不同倍率螢幕的即時 DPI 重排仍需另案驗收。

## 檔案與結果

單一 TXT／CSV，2 MiB、UTF-8／UTF-8 BOM；TXT 最多 50,000 字，CSV 最多 10,000 列／100 欄。標題空白／重複、列寬不一致、NUL、錯誤編碼拒絕。預覽 TXT 前 2,000 字、CSV 前 20 列，送出完整內容；超過助理設定上下文上限則拒絕。沒有多文件、Office 原檔排版修改。

三項 DEMO01～03 為獨立合成查詢。固定日期區間起含迄不含，1～90 日，category all/A/B。最多 1,000 列與 2 MiB，截斷有標記。正式 Q01～03／Oracle 保持停用。
表格 100 列一頁，全部複製跨所有頁；選取列只限當页、換頁清除選取。輸出只讀同一 snapshot，不另查資料。數值用精確十進位字串，拒絕 float。公式型文字加前置 apostrophe；TSV 分隔字元拒絕並提示改 CSV；CSV 有 BOM、標準 quoting。程式保留精確字串，**Excel 自動推斷可能改變代碼／長整數，貼上前要設文字格式；真正 Excel 貼上尚待公司驗收**。不以 `="..."` 公式包裹值。

## 本機排程

每日／每週、HH:MM、星期 0～6；台北 UTC+8 固定時區。成功查詢才可建立，初始停用；啟用前顯示未來三次 UTC 時間及參數。固定參數或每次前一日；後者必須由模板宣告 date_range，依該次預定執行時間解析起含迄不含日期。未宣告者不能使用；舊 DEMO 排程僅對 DEMO01～03 保留明確相容映射。

程式每 3 秒檢查，`unique(schedule_id,scheduled_at)` 防重。同排程不重疊。關閉期間最新 24 小時最多補跑一次，較舊紀錄以壓縮略過標記保存。重開未完成工作標失敗、不自動重送。停用期間不追補。這是單機防重，不宣稱跨機 exactly-once 或分散式 lease。

通知規則：非空且內容 hash 改變；或單一數值首次達標／由未達標轉達標。取得時間不納入 hash。失敗通知一次。只有唯讀查詢的 ConnectionError／TimeoutError 可有限重試，最多 3 次；公司助理一律不自動 retry。站內通知未讀數可見，無郵件或 OS 背景常駐服務。

## 資料與回報

獨立 `local-v1.sqlite3`、schema user_version=2、WAL；本應用 schema 1 升級前以 SQLite backup 備份，再以交易遷移。無可靠助理歸屬的舊對話保留閱讀／轉交，不接觸舊公司 SQLite。較新 schema 拒絕開啟。單一資料目錄只能一個程式使用；不把本機檔案當授權系統。
回報 draft 可讀取修改，local_saved 只表示保存在此電腦；編號 LOCAL-*。不自動附加對話、資料或檔案，不冒稱管理者已收到。未實作處理狀態同步／修正版本管理。
公司舊資料移轉、中央 API、AD、Oracle、簽章更新及 EXE 打包均另列交接；禁止將原 v2.2 相關 AT 記成已通過。

## 0.4.0 公司接手準備

catalog 的參數定義支援 text/date/integer/decimal/single_choice/boolean、required/default 與適用範圍。UI、Plan 修改與預覽、結果條件及排程共用定義；decimal 保持文字，未知欄位／模板或不支援定義拒絕。adapter.validate 仍為純驗證且保有查詢商業規則；一般送出／批准與排程服務均檢查。細節見 docs/QUERY-CATALOG.md。

本機診斷不連網、逐项收集結果與白名單分享報告；company_acceptance 不因本機通過而改為通過。離線套件包綁定 requirements.lock 指紋與各 wheel SHA-256，缺失或損壞停止，無連外 fallback。雜湊保護傳輸完整性，不是公司發布簽章。

test_support 包含可重用 adapter 契約，company_templates 提供待填測試骨架，company_check 必須明確啟動且完成公司能力審查才載入可信 hooks。無 hooks 或缺項是 not_tested，不能以 demo／skip 替代公司驗收。不包括正式 AD、Oracle 或舊資料移轉。

## 0.5.0 深淺主題與候選圖示（歷史；0.6.0 已採用 A）

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

## 0.6.0 接手重點（歷史；獨立體驗已於 0.7.1 移除）

已完成：A 正式圖示、使用者自管多助理、keyring、固定對話／Plan 路由、資料預覽轉交、Enter／Shift+Enter、獨立五步體驗、離線手冊及聲明。共用 endpoint／API key；名稱、assistant ID、備註由使用者管理。

修改入口：profiles.py 負責公司請求映射及憑證；assistant_views.py 為管理／轉交 UI；core.py schema 2 保存 binding/source，experience.py 管隔離導覽。公司請先提供遮蔽值的成功 API 範例，確認 ID 放 model 或獨立 body 欄位、session 規則及副作用能力。未配置 mapping 的新公司助理不能呼叫，不假裝用示範回答。具體步驟與命令見 docs/ASSISTANT-INTEGRATION.md。

環境新增 keyring==25.7.0，總鎖定套件 29 個；不得使用 keyrings.alt 或明文 fallback。完整離線包以新鎖檔重建，舊包指紋不符必須拒絕。正式驗證用 .venv、.venv-verify060、.venv-offline060，均恰好 Python 3.10.4。

完成條件：公司 API 對話隔離與回傳結果實測、AD／Oracle 核准接線、Excel／Windows 中文輸入法與縮放人工驗收。未實測項目仍保持 not_tested，不能以合成測試替代。中央協作、遠端更新、EXE、任意 SQL 及助理自動分工不在本版。

## 0.7.0 工作區改版（沿用）

- 原生 Tkinter／ttk，未新增 runtime 套件。HTML／CSS 只是可離線開啟的視覺稿，入口 docs/design/workspace.html，不嵌入正式應用。
- 工作／管理／協助分組、原創線條 PNG、820px 聊天閱讀寬度、可選取的訊息卡片樣式、3～6 行整合輸入框及真實任務狀態。
- 工作詳情由明確選定的 task／plan ID 取得，顯示來源與助理版本；寬度至少 1380px 使用右欄，較窄以附屬視窗呈現。切換聊天不會改送正在執行的工作，已開啟詳情保留明確選定的來源。
- 開發改用固定檢查／測試腳本。沒有變更防毒設定、例外或執行政策；Norton 是否不再警告尚未確認，見 docs/NORTON-DEVELOPMENT.md。
- 沿用 Python 3.10.4 三個合格環境、29 個鎖定套件與 schema 2；公司 API、AD、Oracle、Excel 及原生中文 IME 仍需現場驗收。

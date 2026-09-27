# QA agent 0.11.0：產品與架構

本文件是現行行為契約。程式與 UI 已完成本機功能；公司接線見 [工作單](../COMPANY-HANDOFF.md)，實測與未測項目見 [驗證摘要](VALIDATION.md)。

## 分層

新增選用的 Groq 個人試用入口 start-trial.bat。trial.py 管固定端點／模型、有限 .env 讀取與唯讀助理清單；--groq-trial 與 --config 互斥。App 使用獨立 groq-trial 子目錄及預設合成查詢／身分，不讀公司 config 或 profiles。原入口與 adapter 契約保持不變，無新套件；本機升級 schema 4 保存對話來源。不是恢復舊導覽流程。

| 模組 | 責任 |
|---|---|
| desktop_app/ui.py | Tk 畫面、主執行緒事件、背景 IO 回傳、表格／預覽 |
| desktop_app/guidance.py | 原地提示、狀態說明及對應手冊入口；只讀取 UI 現況 |
| desktop_app/experience.py | 離線手冊、關於與環境診斷入口；不再啟動獨立體驗 |
| desktop_app/core.py | Store、任務／Plan gate、受限工作流程、本機排程與通知 |
| desktop_app/local_work.py | 待辦、版本化草稿及本機保存契約 |
| desktop_app/todo_views.py | 待辦看板、窄版分頁、編輯與來源入口 |
| desktop_app/draft_views.py | 延遲保存、失敗重試、恢復與關閉補存 |
| desktop_app/work_cards.py | 公司可調整的三張文字工作卡片 |
| desktop_app/choices.py | 持久化 typed 選項、owner／版本／期限／一次提交 |
| desktop_app/gateways.py | 身分、公司 OpenAI 相容助理、查詢介面與合成實作 |
| desktop_app/files.py | UTF-8 上傳驗證、CSV／TSV 安全輸出 |
| desktop_app/query_schema.py | 動態欄位、純型別驗證、顯示與日期映射 |
| desktop_app/config.py | 本機設定、資料路徑、單一執行個體鎖 |

UI 不直接持有 SQL、密碼或 HTTP 細節。公司請求映射與憑證集中 profiles.py，SDK 傳输維持 gateways.py；未來需要獨立 adapter 檔可在保持介面下拆出，不重寫 UI。

## 工作區與原地操作提示

啟動直接進入對話，提供試查一筆資料、整理一段文字及自行輸入。四個主入口為對話、我的待辦、自動工作、活動紀錄；更多工具保留查詢、結果及進階紀錄，設定與回報在底部。無獨立體驗模式。

ActionService 保存 conversation_actions：來源對話、kind、request、spec、binding、revision、draft/submitted/cancelled 及 task／schedule／plan 連結。真實執行狀態即時讀既有紀錄；schedule_sources 是可失效來源，不是執行歸屬。查詢及排程工作不強加 conversation_id。messages 僅聊天歷史，卡片、表格、通知不自動送模型。

create/update/get/list 管草稿與來源；preview 純驗證並產生10分鐘記憶體確認快照；confirm 重新驗證修訂與綁定，使用固定request ID、Engine鎖及交易同時保存工作／排程與連結。重開草稿重新預覽，不自動批准；已受理不重建。Plan 使用既有修訂與批准契約，每次新修訂另建卡片，舊卡失效。

begin_parse/end_parse 追蹤實際解析工作，apply_parse 驗修訂與來源存在；取消或刪除後舊结果不寫回。刪除快照包含操作記錄，進行中及取消後未結束的即時工作／解析阻擋刪除。刪除清連結，獨立表格及排程保留，排程來源變空並顯示已刪除。

Text 時間線以穩定事件及 marks 增量更新，原生同頁操作區可收合；前三種工作入口只準備草稿。表單沿 catalog，完成条件自動本機預覽，使用者才可確認。Groq 試用可解析需求；公司解析能力預設關閉，不 fallback 外部。頁首提示可收合且保存偏好，必要標示不隱藏。

## 對話、Plan 與選項

對話歷史完整保存，送給 SDK 時使用指定對話的不可變快照；同一對話尚有工作則拒絕重疊提交。總內容超限拒絕，不靜默裁切。
一般模式明確送出即執行。先規劃模式只建立本機固定候選，不呼叫 bot。只有 `confirm_plan` 成功才建立工作；24 小時期限、修訂比對、原子交易與 request ID 防止舊卡片／雙擊重跑。修改需重新批准。桌面流程限查詢、對話、摘要、改寫；查詢後整理須預覽並確認轉交。舊獨立 Engine 契約保留 query_summarize，但桌面的 routed Engine 拒絕直接自動整理。

選項有 yes_no／single_choice／multi_choice；最多 3 題，每題 2～6 選項。未選不當同意，未知值與數量不符拒絕；owner、version、expiry、request ID 由本機服務檢查。取消後不可提交。選項答案不等於任意工具授權。「是，設排程」只開設定，仍建立停用草稿並另確認啟用。重開待答表單可保存答案，**不重播先前 UI callback**，使用者回原工作繼續。

取消在派發界線前阻止新助理呼叫；界線後可能已送出至公司，不能保證遠端撤回。晚到結果不寫回已取消工作。已完成查詢表格可保留，摘要失敗不重跑查詢。未結束的真實 future 會阻擋切換設定，即使工作已標取消。關閉等待遠端 drain 後才釋放資料目錄鎖。
沒有持續自主 Goal、通用 shell／任意 SQL、產品 runtime 多 agent。

## 對話刪除

最近對話的右鍵提供單筆刪除；「管理對話」可依標題搜尋、勾選多筆與全選目前搜尋結果。變更搜尋條件會清除已被隱藏的選取，不把看不到的對話暗中加入刪除。確認顯示對話名稱與數量、訊息／Plan／工作／通知數量，預設焦點在取消，明示永久刪除與無法由應用復原。

Engine.preview_conversation_deletion(ids) 回傳 token、conversations、counts、task_ids、plan_ids；Engine.delete_conversations(token) 回傳同摘要及 deleted_ids。token 在服務端保存選定 ID 與完整資料快照指紋，10 分鐘有效，成功後失效；過期、重複或資料變更須重新預覽。確認時在引擎鎖內重新檢查，以單一 BEGIN IMMEDIATE 交易完成整批刪除；失敗全部回復，不改 schema。

範圍限選定對話、訊息、專屬 Plan、工作輸入／結果及其通知，以及該對話的持久化草稿、記憶體草稿／附件引用；待批准 Plan 一併刪除而不執行。另存待辦保留，來源入口顯示「來源對話已刪除」。排隊、執行中或取消後仍有未結束 future 的選定對話會阻擋整批刪除，不能只檢查畫面狀態，不能自動取消。其他對話的工作可以繼續；不正常的跨工作、Plan 或排程關聯拒絕刪除，不擴大範圍。

原始檔、匯出檔、既有備份、獨立查詢／排程、問題回報、選項表單、其他對話及轉交副本保留。轉交副本的來源不存在時顯示「來源對話已刪除」。公司端歷史不在範圍內；此操作不是安全抹除，也不自動新建含原內容的備份。

刪除後關閉選定資料的詳情及未送出轉交預覽，清除對應草稿及附件引用。刪除目前對話後切到最近保留對話；全部刪除後建立一個空白新對話，其他對話的草稿及附件保持不變。已刪對話不可由舊畫面或舊 Plan 再派發。

## 顯示與 DPI

在建立 Tk 前設定 System DPI awareness；啟動環境已有更高感知模式時保留，不強制覆寫。display.py 集中處理顯示倍率與尺寸換算；以 100% 的邏輯像素為基準換算固定尺寸，避免字體放大而容器不變，或字型與容器重複縮放。微軟正黑體主要操作 11 點、聊天本文 12 點、次要提示至少 10 點。

圖示依倍率使用隨附的本機多尺寸素材；常用 24 邏輯像素圖示對應 24／30／36／48 像素，品牌沿用多尺寸資源，不放大小圖充當高解析。一般、拉大與最大化均由原生文字及控制項重排，不把介面當圖片拉伸。小螢幕／高倍率視窗須限制在可用工作區內，內容必要時可捲動，保留送出、取消、批准及刪除確認的操作路徑。

記錄 DPI 感知、螢幕倍率、Tk scaling、實際字型與視窗尺寸，診斷不包含公司內容。本機舊啟動路徑確認為 unaware；最大化的字型點數未改變，因此不能將最大化本身認定為模糊原因，也不宣稱 DPI 是唯一因素。跨不同倍率螢幕的即時 DPI 重排仍需另案驗收。

## 檔案與結果

單一 TXT／CSV，2 MiB、UTF-8／UTF-8 BOM；TXT 最多 50,000 字，CSV 最多 10,000 列／100 欄。標題空白／重複、列寬不一致、NUL、錯誤編碼拒絕。預覽 TXT 前 2,000 字、CSV 前 20 列，送出完整內容；超過助理設定上下文上限則拒絕。沒有多文件、Office 原檔排版修改。

三項 DEMO01～03 為獨立合成查詢。固定日期區間起含迄不含，1～90 日，category all/A/B。最多 1,000 列與 2 MiB，截斷有標記。正式 Q01～03／Oracle 保持停用。
表格 100 列一頁，全部複製跨所有頁；選取列只限當页、換頁清除選取。輸出只讀同一 snapshot，不另查資料。數值用精確十進位字串，拒絕 float。公式型文字加前置 apostrophe；TSV 分隔字元拒絕並提示改 CSV；CSV 有 BOM、標準 quoting。程式保留精確字串，**Excel 自動推斷可能改變代碼／長整數，貼上前要設文字格式；真正 Excel 貼上尚待公司驗收**。不以 `="..."` 公式包裹值。

## Groq 試用日報

只在隔離的 Groq 工作區使用 ReportEngine；一般工作區使用 Engine。intent_drafts 的能力開關只允許 Groq 固定綁定與合成目錄。送出明確查詢／排程需求後以 strict schema 解析，程式再檢查格式；缺少條件留空追問。已知合成範例不呼叫模型。公司模式使用表單，不假稱解析已驗證。

ActionService 的 report 確認強制每日前一日、三項合成模板及 Groq 固定綁定，使用者另勾選持續傳送授權。一次確認建立啟用排程及來源，不立即執行。原對話可現在測試一次及暫停；立即測試不更改 next_fire。原有 preview_report／confirm_report 與獨立視窗保留相容測試，不作主要使用路徑。

沿用 schedules.parameters 的 _report 版本／binding，每次 occurrence 計算前一日。先存完整snapshot，以Decimal精確計算後只送來源、模板、條件、時間、筆數及合計。空結果不呼叫AI；截斷／格式錯誤／超限拒絕。摘要失敗整體failed但表格保留；取消晚到不覆寫，每次結果通知一次，不自動重試。

## 本機排程

以下是一般查詢自動工作；Groq 明確授權日報例外見上節。每日／每週、HH:MM、星期 0～6；台北 UTC+8 固定時區。對話確認卡可從已核對條件或成功結果建立，確認才啟用、不立即執行。進階舊入口仍從成功查詢建立停用草稿，另行啟用。固定參數或每次前一日；後者必須由模板宣告 date_range，依該次預定執行時間解析起含迄不含日期。未宣告者不能使用；舊 DEMO 排程僅對 DEMO01～03 保留明確相容映射。

程式每 3 秒檢查，`unique(schedule_id,scheduled_at)` 防重。同排程不重疊。關閉期間最新 24 小時最多補跑一次，較舊紀錄以壓縮略過標記保存。重開未完成工作標失敗、不自動重送。停用期間不追補。這是單機防重，不宣稱跨機 exactly-once 或分散式 lease。

通知規則：非空且內容 hash 改變；或單一數值首次達標／由未達標轉達標。取得時間不納入 hash。失敗通知一次。只有唯讀查詢的 ConnectionError／TimeoutError 可有限重試，最多 3 次；公司助理一律不自動 retry。站內通知未讀數可見，無郵件或 OS 背景常駐服務。

## 資料與回報

獨立 `local-v1.sqlite3`、schema user_version=4、WAL；本應用 schema 1／2／3 升級前以 SQLite backup 備份，再以交易遷移。無可靠助理歸屬的舊對話保留閱讀／轉交，不接觸舊公司 SQLite。較新 schema 拒絕開啟。單一資料目錄只能一個程式使用；不把本機檔案當授權系統。
回報 draft 可讀取修改，local_saved 只表示保存在此電腦；編號 LOCAL-*。不自動附加對話、資料或檔案，不冒稱管理者已收到。未實作處理狀態同步／修正版本管理。
公司舊資料移轉、中央 API、AD、Oracle、簽章更新及 EXE 打包均另列交接；未接線或未實測項目不得記成已通過。

## 接線工具

catalog 的參數定義支援 text/date/integer/decimal/single_choice/boolean、required/default 與適用範圍。UI、Plan 修改與預覽、結果條件及排程共用定義；decimal 保持文字，未知欄位／模板或不支援定義拒絕。adapter.validate 仍為純驗證且保有查詢商業規則；一般送出／批准與排程服務均檢查。細節見 [查詢契約](QUERY-CATALOG.md)。

本機診斷不連網、逐项收集結果與白名單分享報告；company_acceptance 不因本機通過而改為通過。離線套件包綁定 requirements.lock 指紋與各 wheel SHA-256，缺失或損壞停止，無連外 fallback。雜湊保護傳輸完整性，不是公司發布簽章。

test_support 包含可重用 adapter 契約，company_templates 提供待填測試骨架，company_check 必須明確啟動且完成公司能力審查才載入可信 hooks。無 hooks 或缺項是 not_tested，不能以 demo／skip 替代公司驗收。不包括正式 AD、Oracle 或舊資料移轉。


## 個人工作流程

我的待辦與 Engine 的 tasks 分離。todos 保存標題（1～120 字）、說明（最多 50,000 字）、todo／ongoing／done、選填 YYYY-MM-DD、來源對話 ID、建立／更新／完成時間與保存防重 ID。來源不使用連動刪除；對話刪除後待辦保留，來源失效明示。狀態不觸發模型、查詢或排程，台北日期只作到期標記。

`todo_views.py` 在可用寬 900 邏輯像素以上用三欄，以下用狀態分頁。標題搜尋、顯示已完成及三欄排序沿用使用者選擇，重複刷新不重建未變卡片。常用文字卡片定義於 `work_cards.py`，只填入可修改草稿，既有草稿／附件存在時開同一助理的新對話。

`draft_views.py` 約一秒 debounce，依對話記錄文字、用途、先規劃及是否曾有附件，不保存檔案路徑或內容。Store reservation 使舊寫入失效；接受工作／Plan 後清除，刪除草稿包含於原刪除快照和同一交易。正常關閉補存，失敗須提示；Plan 修訂仍明確保存。重開舊綁定只能閱讀，不改送目標。

## 助理連線與資料轉交

`profiles.py` 管理共用 endpoint、金鑰索引、多助理名稱／ID／備註與連線版本；金鑰由 Windows keyring 保存，舊環境變數只相容讀取，不自動匯入、不明文 fallback。公司成功 API 範例未確認前，wire_mode 保持 unconfigured，不猜 ID 傳送位置。

每段對話固定 profile_id／revision；改 endpoint 或 assistant ID 使舊綁定失效，名稱／備註不換版本。切換助理另開對話，草稿及附件不自動轉交；Plan 保留目標版本，批准與派發時重驗。公司 session 若非 stateless messages，須沿 adapter 邊界擴充並驗證隔離。

查詢結果與對話選定內容先指定目的助理、預覽再確認；建立獨立新對話並記來源。最多 50,000 字，超限拒絕、不默默截斷；失敗保留來源。一般查詢排程不自動送模型；Groq 明確授權日報依上節限送合計。細節見 [助理接線](ASSISTANT-INTEGRATION.md)。

## 維護入口与完成界線

`assistant_views.py` 為管理／轉交、`conversation_views.py` 為刪除、`workspace.py` 為訊息與工作詳情；`branding.py`、`display.py`、`theme.py`、`preferences.py` 管品牌與外觀，`keyboard.py` 管送出與 IME 保護。保持此分層，不因接公司服務重做 UI。

深淺主題原地更新控制項與品牌圖示（含已開啟附屬視窗）；assets/light 保存淺色包，缺少時提示並使用深色包，桌面捷徑維持深色。不清除草稿、選取、附件、Plan 或背景工作；偏好獨立存在 ui-preferences.json，損壞用深色，保存失敗保留本次變更並提示。原生系統對話框遵循 Windows 外觀。

| 狀態 | 能力 |
|---|---|
| 本機已實作 | 四主要入口與更多工具 UI、助理管理、Plan、選項、TXT／CSV、合成查詢、轉交、排程／通知、回報、刪除、深淺與 DPI |
| 工具已準備，待公司接線 | chatbot API 契約、AD／名單與 owner 授權、Oracle 三查詢、公司資料移轉 |
| 仍待真實驗收 | 公司服務、Excel、中文 IME、公司設備倍率與跨螢幕；詳見驗證摘要 |
| 後續才做 | 中央管理／協作、遠端更新、EXE、持續 Goal、多 agent 自主分工、信件／OCR、多文件與 Office 原檔編修 |

Python 3.10.4 與 29 個鎖定套件維持不變。schema 4 加入 conversation_actions／schedule_sources，沿用 todos／drafts，無中央同步。歷史規劃由 Git 保存，不當成目前交付能力。

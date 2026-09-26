# 公司端實作、驗收與交付

## 1. 實作順序

本次交付是 spec＋開發指令，沒有公司原碼、秘密或服務連線。下列程式工作由公司端 agent 執行；此文件不聲稱已完成。

| 階段 | 工作與產物 | 結束條件 |
|---|---|---|
| M0 盤點 | 讀初版 Tkinter、SQLite、排程、成功助理呼叫及既有後端／AD；列 current-state、三項查詢清單（含工作名稱、欄位及日期口徑）、migration mapping | 能說明原功能與整合點；不確定項具體列出，不猜程式結構 |
| M1 跑通核心 | 保留初版，抽出桌面 API client 與背景工作；接既有登入、私有對話、查詢表格；用 Mock 先串完一般／Plan 切換、固定選項表單與確認 gate、常用工作入口 | 同仁完成「問題→選項補條件→計畫預覽→確認→表格」，未確認不派發查詢且一般模式仍可用 |
| M2 真實資料與文字 | Oracle 三項模板、公司助理 adapter、TXT/CSV 預覽／整理、文字修改／複製／另存、查詢結果貼入 Excel | 真實查詢與人工結果一致；權限、缺資料及截斷都正確；驗證 Plan 文字介面的副作用隔離，無法證明時採固定表單 |
| M3 排程與回饋 | 中央 scheduler、通知、旧排程防雙跑、issue 提交與既有管理頁 | 可設定查詢排程、重啟不重複，回報有編號與狀態 |
| M4 分發與更新 | Launcher/Updater、內網版本發布、簽章、回復、乾淨 Windows 試用 | 複製安裝可用，按更新成功；錯誤情境不毀資料 |

沒有 API／Oracle 內部資料，只阻擋對應 real integration；Mock、schema、UI、參數驗證與 fault tests 可繼續。先交能操作的垂直流程，不為 M4 建一大堆尚未用到的抽象。

## 2. 輕量模組界線

沿用公司 repo 風格；新增邏輯可對應 desktop(ui/api_client/local_store)、backend(routes/services/auth_adapter)、assistant_adapter、query_service、scheduler、issues、releases、updater。不是要求重建這些資料夾或換框架。

Tk callback 不直接查 Oracle；後端 schema 不包含 Tk widget；助理不能直接接 SQL credentials。優先用既有 logging、migration、測試與發行工具，新增依賴才鎖定公司核准版本。

同一開發 agent 即可順序完成。若 Copilot 可用 subagents，Coordinator 最多委派兩個互不寫同檔的工作包，自己負責契約、根設定與整合。開發分工不意味產品 runtime 要實作多代理。

## 3. 驗收矩陣

| AT | 需求 | 真正要證明的行為 |
|---|---|---|
| AT-01 | UH-01 | 有效 AD、錯單位、不在名單、停用、離職及過期快取；只有符合條件者可新建工作 |
| AT-02 | UH-02 | 兩位同仁的 session／歷史隔離；斷線／取消不假稱完成；未提供工具時不虛構查詢 |
| AT-03 | UH-03 | 三項模板各至少三組條件，與人工 Oracle 結果一致；缺條件會問；模型 SQL 字串被拒 |
| AT-04 | UH-03 | 參數注入、偽造單位 scope、越權 query、查無資料、timeout、truncated、Decimal／日期／null、CSV 公式注入 |
| AT-05 | UH-04 | UTF-8/BOM TXT/CSV、預覽／移除、錯格式、編碼錯、超大小／列數／context、無資料；不偷偷部分分析 |
| AT-06 | UH-05 | 原文保留，改寫預覽可複製／另存；同名覆寫有確認；不聲稱支援 DOCX/XLSX 原檔 |
| AT-07 | UH-06 | 草稿三次預覽、固定日期 vs 滾動日期、enable/disable、run-now、每日／每週、時間轉換 |
| AT-08 | UH-06、UH-07 | 雙 worker claim、失去 lease、重啟、漏跑、overlap；同 occurrence 一個 task、一個結果通知；撤權停用 |
| AT-09 | UH-07 | 首次非空、無變化、變化、門檻越界、空結果、失敗；桌面離線後補看，不重複通知 |
| AT-10 | UH-08 | 本人可回報／追蹤，其他人不可看；重送不重複；未勾附加的對話不外送；重複 issue 不洩露另一人內容 |
| AT-11 | UH-08 | 管理者分類、合併、狀態／原因、修正 release 關聯；解決後可追蹤版本，審計不含 secrets |
| AT-12 | UH-09 | 乾淨 Windows 複製啟動，從 0.1.0 更新 0.1.1；成功切換、草稿／歷史／排程一致 |
| AT-13 | UH-09 | 錯簽章／hash／platform、降版、過期、ZIP escape、斷線、滿碟、雙開、切換各點終止、啟動失敗回復 |
| AT-14 | UH-09、UH-10 | 不相容 migration 被擋；舊 SQLite backup 可還原；匯入防重；local→central 排程切換不雙跑 |
| AT-15 | 全部 | 高 DPI 100/150/200%、繁中 IME、長歷史分頁、後台查詢時 UI 可用；無 credentials 進 logs／zip／prompt |
| AT-16 | UH-11 | Plan 建立／修改／補條件時 Oracle、legacy 工具、schedule enable 呼叫數為 0；惡意模型輸出不能越過 dispatch gate；一般模式既有唯讀流程仍可用 |
| AT-17 | UH-11 | 確認只執行畫面同一修訂／hash／日期；雙擊、雙視窗、斷線重送只建一個 execution task；修改／跨日／過期／撤權／來源刪除後拒絕舊確認 |
| AT-18 | UH-12 | 是非／單選／多選、選取數與 required、補充文字、鍵盤／IME；預選不提交、執行不預選同意；拒絕未知或重複選項、跨人、過期及舊 form_version |
| AT-19 | UH-11、UH-12 | 純文字無 JSON 的 bot 可走固定表單；結構候選錯誤只修正一次再 fallback；工具副作用未知時 Plan 不呼叫該 bot；不用原生 Plan 也完成預覽流程 |
| AT-20 | UH-06、UH-11、UH-12 | query 成功後回答「是」只取得唯一 disabled 排程草稿，「否」不建立；仍需原排程預覽及確認啟用；Plan 確認不能代替排程批准 |
| AT-21 | UH-11、UH-12 | 桌面／worker 重啟可恢復待答、計畫和已批准 task；等回覆不占 lease、不自動同意；取消及晚到結果不復活；摘要失敗保留表格且明確標示；總呼叫及執行 deadline 有界 |
| AT-22 | UH-13 | 不輸入提示詞完成指定查詢；只列 enabled 且本人授權模板；缺展示 metadata 的舊模板可用基本表單，無可用查詢有明確說明 |
| AT-23 | UH-13、UH-11、UH-12 | 日期預設與自訂、必填／格式錯誤、跨日刷新、換模板不殘留條件；一般模式一次查詢、Plan 仍需 confirm；偽造候選不能越權 |
| AT-24 | UH-14 | 全部跨頁／目前頁選取、換頁清選、欄名開關、固定欄序及筆數；相同 task snapshot，複製不跑新 SQL；中途失敗不複製部分資料 |
| AT-25 | UH-14 | 公司實際 Excel 貼上中文、前導零、長識別碼、高精度值、日期、空值與公式樣式文字；依文字欄指引保真、危險文字不執行且來源不變 |
| AT-26 | UH-14 | 空結果、無選列、truncated、Tab／CR／LF／NUL、快照過期／撤權、剪貼簿被占用；明確拒絕或提示，不假成功，CSV 入口仍可用 |
| AT-27 | UH-08 | 「沒有解決我的問題」只開草稿，未提交無 issue；未勾選的內容不附加；本人可用既有去重提交，不新增自動滿意度蒐集 |

每項保存日期、環境、實際步驟／命令、結果、必要截圖／trace ID。狀態使用 not_started、in_progress、mock_passed、real_passed、blocked；不能將 Mock 或文件檢查當公司環境通過。

## 4. 驗收資料与測試方式

使用 deterministic fake clock 與合成資料測排程，不真的等隔天。查詢契約先用 fixture；公司 real tests 再以唯讀帳號執行三項查詢。更新測試使用測試專用 signing key 和獨立 sandbox 目錄，不能用正式私鑰或替換現有軟體。

測試重点是權限與結果、排程防重、更新失敗保護；不為每個 getter 或按鈕文字大量寫無意義測試。QA 不能聲稱「看程式應該可以」等於真 GUI／Oracle／更新實測。

先給你本人，再給少量指定同仁試用。每個人完成查詢、文字整理、排程、回報及更新各一次，記錄實際卡住處；MVP 的改善優先順序以 issue 與使用情況決定，不自動加入延後功能。

## 5. 公司端需要補齊的資料

| 必要資料 | 用途 | 未知時可以繼續什麼 |
|---|---|---|
| 原碼入口、依賴、SQLite schema、舊 runner | 相容改造、遷移與回歸 | 建契約／Mock，不捏造舊資料格式 |
| 既有後端框架與登入接法 | 真正重用 AD／session | AuthAdapter contract，不能自建密碼庫 |
| Oracle 版本、三項查詢的表／欄／join／口徑／授權 | 填 QUERY-CATALOG、真實結果校對 | 三個 disabled slots 與合成資料 |
| 公司助理成功呼叫樣例、session／能力／plugin 副作用 | Adapter 與隔離、重試策略 | Mock 與錯誤映射 |
| 內網更新來源、簽章密鑰管理、安裝目錄規範 | Launcher/Updater 真實發布 | 測試 key／本機測試 server 演練 |
| 使用名單、留存、結果可送助理的範圍 | 資料與上線控制 | 預設拒絕未授權資料 |

上述資訊回公司核對，不要求在這個對話交出秘密。實作前建立 `docs/current-state.md` 與 `docs/implementation-status.md`（由開發 agent 建立），每個 blocker 列出影響範圍。

## 6. 交付要求

公司端最終交付原碼、鎖版依賴、實際測試紀錄、後端 migration／rollback、查詢目錄、發行包、簽章發布步驟、第一版 bootstrap 分發說明及已知限制。重點是讓一人可維護：沿用既有服務、三項查詢、兩種角色、簡單管理頁、一條可驗證的更新路徑。

## 7. v2.1 契約與相容交付

先定義 [PLAN-AND-CHOICES.md](PLAN-AND-CHOICES.md) 的 server DTO／gate，再接 Tkinter 計畫卡與選項卡；不先靠 prompt 模擬限制。migration 為新增表與可空欄位，舊請求 interaction_mode 缺省 normal；舊 client 與新後端須回歸。Planner／表單可沿用 service 層，不要求安裝 agent framework。公司端必須用呼叫紀錄或 spy 證明「未确认不執行」，不能只測按鈕是否停用。

## 8. v2.2 實作與試用

先以既有 query catalog 補展示資料及表單，再實作 snapshot 複製與快速回報。依 AT-22～AT-27 保存 Mock／實際 Excel／公司查詢證據；Excel 版本、目的欄格式與實際貼上步驟要列明。不以產生 TSV 字串代替真實貼上驗收。三項公司的工作名稱與欄位未確認時維持 disabled，只做合成範例。

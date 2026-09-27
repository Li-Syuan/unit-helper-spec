# 實作狀態 — QA agent 0.8.0

| 工作 | 狀態與界線 | 主要檔案 |
|---|---|---|
| 對話清理 | 單筆／搜尋多選預覽刪除；10 分鐘快照 token、真實 future 阻擋與整批交易；檔案／備份／獨立查詢排程／轉交副本保留；本輪證據見 VALIDATION-LOCAL | core、桌面刪除入口、USER-GUIDE |
| DPI 與清晰度 | Tk 前 System aware、保留較高模式；集中尺寸換算、多尺寸本機圖示及小工作區捲動；真實多倍率／跨螢幕結果另列，不以模擬當通過 | display、theme、UI-DESIGN |
| Python／鎖版／第二環境 | 0.8.0 三環境各 192 tests／0 skipped，doctor／pip check／freeze lock 通過；依賴未變 | scripts、requirements.lock |
| 原地操作提示 | 八頁頁首提示、收合偏好與對應手冊；取代歡迎與獨立體驗，提示不派發工作；真 Tk 回歸與自身畫面已驗，見 VALIDATION-LOCAL | guidance、ui、preferences、USER-GUIDE |
| 對話／歷史／背景／取消 | 本機已完成；Enter 送出／Shift+Enter 換行／Ctrl+Enter，IME 人工驗收待完成 | ui、theme、core |
| OpenAI 相容 SDK | adapter + MockTransport 通過；公司實測未做 | gateways |
| Plan／是非／單選／多選 | 本機固定流程、服務 gate、修訂／期限／防重 | core、choices、ui |
| TXT／CSV／文字預覽輸出 | 本機已完成；真摘要／改寫需公司 API | files、ui、gateways |
| 三查詢／表格／CSV／TSV | 合成資料通過；真 Oracle／Excel 待驗收 | gateways、files、ui |
| 本機排程／通知 | 可控制時鐘的防重、漏跑、停用與通知測試通過 | core |
| 回報草稿 | 編號／重開修改／本機完成；無管理平台 | core、ui |
| AD／名單／多使用者授權 | 未配置則拒絕；正式接線待公司 | CompanyIdentity |
| Oracle 真實模板 | 停用；需公司核准 SQL／服務 | OracleQueries |
| 舊版資料／排程移轉 | 未碰原 DB；需盤點／備份／dry-run／停舊啟新 | COMPANY-HANDOFF |
| 真實 GUI 滑鼠驗收／Excel | Tk 控制項、兩種尺寸截圖檢視及動作可見性已測；OS 人工與 Excel 待公司 | tests/test_ui、USER-GUIDE |
| 中央 API／管理／更新／EXE | 本次不實作 | 原 v2.2 為後續路線 |

後續接手 agent 應在這裡補「實際完成條件與證據」，不能把新增 adapter 檔案當成整合成功。

0.8.0 沿用 schema 2、Python 3.10.4 與 29 個鎖定套件，沒有新的執行期依賴。本輪完整測試為三環境各 192 tests；實際 150% 視窗與合成倍率分開記錄，詳見 VALIDATION-LOCAL.md。

## 0.4.0 接手準備（歷史）

| 工作 | 實際完成與界線 | 入口 |
|---|---|---|
| 動態表單／Plan／排程 | 六種型別，模板失效拒絕、舊 DEMO 相容、不同日期映射；本機合成測試通過 | query_schema、QUERY-CATALOG |
| 串接工具包 | 可重用 SDK／查詢契約與待填公司 hook，正式服務仍未測試 | ADAPTER-TEST-KIT |
| 一鍵診斷 | 真環境檢查與分享白名單報告，沒有公司連線 | diagnose.bat、doctor |
| 離線安裝 | 20-wheel 包驗證，.venv-offline2 已由包重建；當時重驗 111 tests、lock 一致 | OFFLINE-INSTALL |
| 公司接手工作單 | 必要輸入、六項接線與現場驗收；未填不視為完成 | COMPANY-INPUTS、COMPANY-HANDOFF、COMPANY-ACCEPTANCE |

完整證據入口：docs/validation/development.json、clean-rebuild.json、offline-rebuild.json；請核對報告內版本，不以較早版本結果代表本輪驗證。0.4.0 當時依賴無新增；不把骨架、合成測試或本機通過當真實公司通過。

## QA agent 0.4.1

圖示生成、七尺寸 ICO、主／附屬視窗、側欄、對話署名與啟動名稱已更新；捷徑建立工具通過 5 項真 COM 測試，使用者桌面已建立 QA agent 捷徑。資料目錄／schema／依賴未變，原始圖及提示詞已進 repo。三環境最終各 103 項測試。Windows 工作列／桌面外觀及公司服務仍依 BRANDING.md／VALIDATION-LOCAL.md 分開記錄未實測部分。

## 0.5.0 深淺主題與候選圖示（歷史）

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

## 0.6.0 完成紀錄（歷史）

| 工作 | 完成與界線 | 修改入口 |
|---|---|---|
| 多助理／憑證 | 清單、預設、停用、連線版本、Windows keyring；新公司映射待成功樣本 | profiles、assistant_views、ASSISTANT-INTEGRATION |
| 固定對話／Plan | binding/source、改連線舊 Plan 拒絕、背景派發固定目標、草稿隔離 | core、ui |
| 結果／對話轉交 | 選取→指定助理→完整預覽→確認→新對話，超限拒絕、失敗保留來源 | assistant_views |
| 歡迎與五步體驗 | 當時使用獨立程序／臨時資料；0.7.1 已移除，改為正常工作區提示 | experience、preferences |
| 手冊／資料说明／授權 | 應用內離線章節、完整 29 個套件授權文字、關於與回報入口 | USER-GUIDE、DATA-USAGE、THIRD-PARTY-NOTICES、licenses |
| 鍵盤 | Enter／Shift+Enter／Ctrl+Enter、防重、IME guard；原生中文 IME 待人工 | keyboard |
| 依賴／資料升級 | 29-wheel 新包與兩個全新 venv 重建；schema 2 升級前備份 | requirements.lock、core、setup |
| 正式 A 圖示 | 七尺寸 PNG／ICO、視窗、侧欄、桌面捷徑 | assets、BRANDING |

本版三環境各 139 tests、0 skipped。公司 API／AD／Oracle／Excel、原生中文輸入法與 OS 最終外觀不冒稱通過；人工清單见 COMPANY-ACCEPTANCE。

## 0.7.0 工作區改版（沿用）

- 原生 Tkinter／ttk，未新增 runtime 套件。HTML／CSS 只是可離線開啟的視覺稿，入口 docs/design/workspace.html，不嵌入正式應用。
- 工作／管理／協助分組、原創線條 PNG、820px 聊天閱讀寬度、可選取的訊息卡片樣式、3～6 行整合輸入框及真實任務狀態。
- 工作詳情由明確選定的 task／plan ID 取得，顯示來源與助理版本；寬度至少 1380px 使用右欄，較窄以附屬視窗呈現。切換聊天不會改送正在執行的工作，已開啟詳情保留明確選定的來源。
- 開發改用固定檢查／測試腳本。沒有變更防毒設定、例外或執行政策；Norton 是否不再警告尚未確認，見 docs/NORTON-DEVELOPMENT.md。
- 沿用 Python 3.10.4 三個合格環境、29 個鎖定套件與 schema 2；公司 API、AD、Oracle、Excel 及原生中文 IME 仍需現場驗收。

新增工作區測試 7 項、啟動檢查 4 項，保留既有 139 項覆蓋。真 Tk 視窗、合成流程及真 COM 通過；Norton 成效未能確認，不能寫成防毒驗收通過。

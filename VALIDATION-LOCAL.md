# 本機實作驗證紀錄 — QA agent 0.7.1

本次完成 Windows x64／CPython **3.10.4**／Tk **8.6.12** 的三個既有獨立 venv 重驗（開發環境、0.6.0 線上／離線重建環境）。每個環境 **155 項測試通過，0 skipped**；pip check 成功，pip freeze --all 與 requirements.lock 完全一致。

## 可核對證據

- [開發環境原始輸出](docs/validation/development.json)
- [第二乾淨環境原始輸出](docs/validation/clean-rebuild.json)
- [離線重建環境原始輸出](docs/validation/offline-rebuild.json)
- 證據含 UTC 執行時間、實際直譯器完整路徑、版本、架構、Tk、全部套件、逐項測試及 exit code。
- 開發直譯器：`D:/unit-helper-spec/.venv/Scripts/python.exe`。
- 重建直譯器：`D:/unit-helper-spec/.venv-verify060/Scripts/python.exe`。
- 離線重建直譯器：`D:/unit-helper-spec/.venv-offline060/Scripts/python.exe`。
- 三者各自 site-packages，`include-system-site-packages=false`，由同一官方 CPython 3.10.4 建立；沒借用 Conda 或其他專案環境。
- `scripts/setup.ps1 -PythonExe .runtime/python3104/python.exe -Environment .venv-verify060 -CaBundle .runtime/windows-ca.pem` 實際成功；公司使用自身核准的直譯器／CA。

重跑並保存證據：

```powershell
.\.venv\Scripts\python.exe scripts/verify.py development
.\.venv-verify060\Scripts\python.exe scripts/verify.py clean-rebuild
.\.venv-offline060\Scripts\python.exe scripts/verify.py offline-rebuild
```

verify 會拒絕 0 tests、任何 skip、非零 exit code 或套件與 lock 不符。程式不需要真實 API 金鑰即可通過基準。

## 各項驗證邊界

| 項目 | 本次結果 |
|---|---|
| 環境／依賴 | local_real_passed：三環境確切版本、64 位元、真 Tk root、pip check、鎖檔一致 |
| SDK | mock_passed：真 OpenAI SDK + httpx.MockTransport；request／headers／assistant ref、session 資料隔離、401、timeout、空白／異常格式／工具回覆、TLS／CA、禁重導與 retry |
| Plan／任務 | local_real_passed：未批准零 dispatch、修訂／過期／取消、並行重複批准、防重、真 future drain、摘要部分失敗保表格 |
| typed 選項 | local_real_passed：owner、是非／多選、數量／未知值、過期、取消、持久化及 idempotency |
| TXT／CSV／輸出 | local_real_passed：大小／UTF-8 BOM／錯編碼／欄數、精確字串、公式防護、CSV quoting、全部／選取／跨頁、snapshot 不變 |
| 排程／通知 | local_real_passed：可控制時鐘測每日／每週、前一日解析、漏跑、重啟、防重、停用、非空改變／門檻、失敗通知，不等待隔天 |
| Tkinter 桌面 | local_real_passed（程式操作）：真 Tk widgets，對話→Plan 修改批准→查詢→分頁→Windows 剪貼簿、回報草稿、排程與通知、選項對話框、可見八頁、關閉等待／重開保存 |
| UI 外觀／最小視窗 | local_real_passed：檢視應用自身合成資料畫面截圖，涵蓋 1280×860 與 1050×700；原地提示、主要按鈕可見與快捷送出 gate 測試。截圖見 docs/UI-DESIGN.md |
| OS 滑鼠／鍵盤人工流程 | not_tested：Computer Use helper 仍因 `apply deny-read ACLs` 無法啟動；本次透過真 Tk 控制項操作與自身視窗截圖檢視，不冒稱 OS 滑鼠全流程通過 |
| 公司 chatbot | not_tested：沒有公司端點／成功樣本／金鑰；示範文字不是 AI 生成 |
| AD／員工名單 | not_tested：只验证 demo 明示及正式未配置拒絕；非真 AD 登入 |
| Oracle | not_tested：三個合成查詢／參數驗證通過，未執行公司 SQL |
| Excel 真實貼上 | not_tested：Windows clipboard/TSV 通過，未在 Excel 驗證資料自動轉型 |
| 舊公司資料移轉、打包、中央更新 | out_of_scope：沒有執行 |

## 發現與修正

整合檢查修正跨功能修改錯誤計畫、取消後更換 client、派發前取消界線、背景 IO 計數、Tk after callback 清理、設定驗證先於寫檔等問題。
初次第二環境完整測試曾因 Tk 物件在背景執行緒釋放出現 `main thread is not in main loop`／`Tcl_AsyncDelete`，該次不算通過。改為背景工作 drain 後由主執行緒清理視窗、選項變數及 singleton lock，新增關閉回歸測試；上方證據是修正後的完整重跑結果。

本機可執行不等於公司 production-ready。未實測項目已在 COMPANY-HANDOFF.md 列具體修改位置、內部資訊、正反驗收與執行命令。

## 0.3.1 介面更新

加入 theme.py 集中樣式，不增加套件或變更 schema。重新配置側欄、對話、查詢、計畫、表格、排程、回報、設定；修正小視窗動作列被擠出畫面的問題。0.3.1 發布時的完整測試為各 67 項；目前上述 JSON 已更新為 0.6.0 的三環境完整證據。公司 API／AD／Oracle／Excel 的未實測界線不變。

## 0.4.0 公司接手準備包

- 動態 catalog：六種欄位、精確小數字串、缺欄／未知欄／錯型別／範圍、非日期與不同日期欄位、Plan 未批准零派發、舊 DEMO 日期映射、失效模板停止並保留歷史。
- 串接工具：共用 SDK 契約與合成 fixture、查詢結果斷言、明確啟動與能力審查 gate、缺項 not_tested、hook 載入／失敗／輸出抑制、optimized Python 拒絕。公司 runner 測試使用合成 hook，只證明 runner 行為，**不是公司實測**。
- 診斷：獨立檢查、固定白名單報告、秘密植入不外洩、錯誤設定仍檢查其餘項目；不呼叫公司服務。
- 離線：由核准鎖檔下載完整 20 個 wheel；缺件、損壞、錯目標、lock 不符、路徑穿越與額外檔案拒絕；全新 .venv-offline2 實際從本機 wheelhouse 無 index 安裝，pip check／freeze／95 tests 全通過。
- 新表單已檢視 1280×860 與 1050×700 的自身視窗截圖；六欄位表單於小視窗可捲動、送出保持可見。合成圖見 docs/UI-DESIGN.md。

離線首次嘗試 .venv-offline 雖通過功能測試，直接指定 wheel 路徑造成 pip freeze 記成 file URL，未通過嚴格 lock 檢查，因此**不列為合格交付環境**。setup 已改用同一鎖檔在已驗證 wheelhouse 以 --no-index --no-deps 安裝；新建 .venv-offline2 後重驗，證據為修正後結果。沒有刪除舊環境或使用者資料。

0.4.1 發布時三份完整驗證各為 103 tests、0 skipped。公司 API／AD／Oracle／Excel 仍為 not_tested，docs/COMPANY-ACCEPTANCE.md 提供現場驗收工作單。

## 0.4.1 QA agent 圖示與命名

0.4.1 發布時三份證據為 **各 103 tests、0 skipped**，pip check／freeze lock 一致，runtime 依賴不變。新增 3 項品牌測試、5 項 Windows COM 捷徑測試。

- 本機實測：透明 PNG 角落、ICO 16／24／32／48／64／128／256 尺寸；主視窗與附屬視窗 WM_GETICON；從不同工作目錄載入資源；缺圖片時仍正常建立 App 並顯示提示；對話署名 QA agent。
- 實際圖像檢視：16／32／48px 及 1280×860、1050×700 的 QA agent 視窗，截圖僅限本應用的合成測試資料。
- 真 Windows COM：暫存資料夾建立／重跑、路徑含空白／單引號／中文搬移更新、缺資源保留原捷徑、其他應用同名保留、無效目錄拒絕。
- 使用者桌面：已依核准方案建立 QA agent.lnk（Windows 回報的 OneDrive Desktop），使用專案 pythonw、工作目錄及新 ICO；不改其他桌面項目。
- 啟動器 --check 通過。已更新目前文件與圖示生成提示詞；舊資料、設定與歷史 spec 保持相容。
- 工作列／真實桌面的 OS 最終外觀未人工檢視；不能以自身視窗內容截圖或 COM 屬性檢查冒稱通過。公司 API／AD／Oracle／Excel 仍 not_tested。

曾發現 Tk Windows iconbitmap getter 對載入的 ICO 回傳空字串；改用實際 wrapper HWND 的 WM_GETICON 檢查小／大圖示非空，並對附屬視窗顯式套用。上方最終證據為修正後驗證。

## 0.5.0 深淺工作區與候選圖示

2026-09-27 於三個既有合格 Python 3.10.4 環境各完成 **111 tests、0 skipped**，pip check／freeze lock 一致；本輪沒有新增依賴或重建環境。此段為 0.5.0 歷史；目前三份 JSON 已更新為 0.6.0。

新增 8 項偏好／主題測試：缺失、損壞、未知值、原子保存失敗保留舊檔；App 重開讀取偏好；保存失敗仍套用；草稿、附件、游標、選取、捲動與待批准 Plan 保留；背景工作不中斷不多派發；已開啟／新開選項及檔案預覽同步；下拉清單及捲軸配色；八頁最小尺寸按鈕；不同 Tk interpreter 主題隔離。

首次完整回歸發現品牌測試的舊 SimpleNamespace fixture 缺少新 Appearance，修正測試 fixture 後重跑三環境全部通過；正式品牌載入及缺資源測試仍保留。

實際捕捉 38 個本應用隔離視窗畫面，涵蓋雙主題、八頁、兩尺寸、動態表單與選項。檢視代表畫面後補齊 clam 捲軸的明暗邊線配色，重新截圖與驗證。精選 PNG 見 docs/UI-DESIGN.md；完整本機證據在忽略目錄 artifacts/theme-preview。

四款候選各有高解析透明 PNG、16／32／48 px 預覽及深淺比較圖。原始正式圖示 SHA-256 保持 29cd697887263a1bb195b1e06d6be19a466a40353e678d6a4a74620cd411bf69，沒有更換候選 ICO 或捷徑。啟動器 --check 通過。

以上屬本機真 Tk 程式操作與畫面檢視；公司 API／AD／Oracle／Excel 與 OS 人工全流程維持 not_tested。

## 0.6.0 多助理與新手體驗（歷史）

2026-09-27，三環境各 **139 tests、0 skipped**，doctor／pip check／freeze lock 完全通過。新增 keyring==25.7.0，鎖定共 29 個套件；全新 .venv-verify060 由線上鎖檔建立，全新 .venv-offline060 由 wheelhouse-v060 無 index 安裝建立。舊環境保留，不列為本版基準。

- Windows 認證管理員：真實獨立測試項目保存、讀取、更換、移除，finally 清除；拒絕明文 fallback。失敗案例使用注入 backend；不接觸真實金鑰。
- 助理／Plan：對話上下文隔離、路由固定、修改連線後舊批准拒絕、預覽零派發；升級匯入舊助理識別重開保持固定。工作中切換與私人草稿／附件保存。
- 診斷：助理清單依實際使用者資料目錄讀取；切換 keyring 後不再誤報缺舊環境變數。植入清單秘密及憑證錯誤仍不洩露，診斷不改清單。
- 資料轉交：跨頁列索引與精度、預覽目標／來源、重複確認防重、超限拒絕；失敗保留原查詢。修改其他對話 Plan 時不帶入當前附件。
- SQLite：schema 1 → 2 前真備份及交易遷移；舊對話無 binding 保留閱讀／轉交，未碰公司原始 DB。
- 體驗：真 Tk 控制項完成五步，必須實際批准／查詢／選取／預覽／整理；臨時資料隔離，無公司呼叫，也不讀正式金鑰。歡迎略過、重開、重試與偏好保存通過。
- 手冊：離線文件章節、關於、完整第三方授權可讀；深淺主題截圖及 1050×700 下新導覽／表單／預覽已檢視。曾發現導覽擠掉查詢送出，壓縮底部導覽後重新截圖並驗證按鈕在可見範圍。
- 鍵盤：Enter、Shift+Enter、Ctrl+Enter、空白、長按、重複鍵及注入 IME 狀態通過；Windows IME guard 已整合。**真實中文組字／選字仍 not_tested**，人工步驟見 COMPANY-ACCEPTANCE。
- A 正式圖示七尺寸、主／附屬視窗圖示與 COM 捷徑回歸通過；已更新目前使用者 QA agent 桌面捷徑。OS 工作列／桌面最終外觀未人工檢视。

新公司 assistant ID 映射保持 unconfigured，須公司成功範例確認；公司 API／AD／Oracle／Excel 不以本機通過代替驗收。原始完整輸出見上方三份 JSON，畫面見 docs/UI-DESIGN.md。

## 0.7.0 工作區與固定腳本（歷史）

三份 docs/validation JSON 已更新為本版，各 **150 tests、0 skipped**，doctor、pip check、pip freeze／lock 一致。29 個依賴未變，未重建離線包。0.6.0 段落中的 139 tests 與全新環境是歷史紀錄。

- 真 Tk：1050×700、1280×860、1450×860，深淺主題、訊息、輸入、任務狀態、附屬／側邊詳情、查詢、Plan、結果、設定及五步體驗。
- 新回歸：快捷入口零派發，輸入 3～6 行及寬度改變後重算，跨訊息選取、刷新／主題保留，新增長回覆時保持頂部文字位置；待批准零工作、真實執行／取消／失敗、詳情固定來源、狀態更新保留選取。
- 程式操作與自身視窗截圖發現卡片多餘巢狀邊框及深色預設邊框偏灰白，已統一樣式並重新截圖。查詢／導覽主要按鈕小視窗保持可見。
- HTML／CSS 視覺稿以本機 Chrome headless 渲染深色寬版和淺色小版，檢視離線素材與版面；五種情境由 CSS 控制，只展示合成內容。未宣稱瀏覽器或桌面的 OS 人工全流程。
- 固定脚本：新增 4 項啟動檢查正反案例；原 5 項 Windows COM 捷徑案例全保留，含中文、空白及單引號的搬移路徑。沒有 EncodedCommand、明文密鑰或執行政策繞過。
- **Norton 成效未能確認（not_tested）**：未取得可核對的防毒事件紀錄。測試 exit 0 不代表沒有 Norton 通知，固定腳本也不是完全避免偵測的保證。核對步驟見 docs/NORTON-DEVELOPMENT.md。
- 公司 API／AD／Oracle／Excel、真實中文 IME／OS 滑鼠鍵盤流程與工作列最終外觀仍 not_tested；合成截圖不取代公司驗收。


## 0.7.1 原地操作提示（目前交付）

2026-09-27 三個既有 Python 3.10.4 環境完整回歸各 **155 tests、0 skipped**，doctor／pip check／freeze lock 一致。完整輸出保存在三份 docs/validation JSON。沿用 29 套件及既有離線包；資料庫 schema 和服務 API 未變。

- 移除歡迎視窗、獨立體驗子程序、五步控制器及其入口；原本 6 項導覽／手冊測試改為 11 項原地提示／手冊測試。保留真實本機示範查詢 → 未批准零工作 → 批准 → 選取列 → 預覽零派發 → 整理結果與來源關聯的驗證。正常示範紀錄保存於個人歷史，不再宣称臨時體驗隔離。
- 驗證八頁提示與正確手冊章節、無歡迎／子程序／公司呼叫、每頁收合重開持久化、損壞預設、保存失敗維持當次選擇；舊 onboarding 及未知偏好保留。
- 真 Tk 測試確認收合／主題切換不改草稿、附件、游標、選取、長對話頂部文字位置、待批准 Plan、表格選取或執行中工作。提示不增加對話、訊息、任務或批准。
- 狀態檢查包含當前對話隔離、公司映射未配置、跨頁編輯、真 expires_at 過期、Plan 成功終態、工作失敗／取消、停用與啟用排程、無結果通知及本機回報；提示只讀取狀態。
- 第一輪新增完整回歸發現 UI 測試在清單刷新前選取資料列的時序問題；改為明確刷新後選取，最終依序重跑三環境。未以失敗結果充當通過證據。
- 真 Tk 合成視窗擷取 20 張，檢視深淺、1050×700／1280×860／1450×860 的聊天、查詢、Plan、設定、回報及收合畫面。HTML／CSS 深色版用本機 Chrome headless 渲染後檢視。精選圖见 docs/UI-DESIGN.md；未宣稱 OS 滑鼠／鍵盤人工全流程。
- 啟動器 --check 通過。Norton 成效仍為 **未能確認（not_tested）**；公司 API／AD／Oracle／Excel、真實中文 IME 與工作列外觀仍 not_tested。沒有變更防毒例外或執行政策。

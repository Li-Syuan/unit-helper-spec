# 1.0.0rc5 候選版驗證（2026-10-25）

本版加入每位助理的五項連線診斷、原對話失敗入口、白名單修復工作單及明確分項重測。Python **3.10.4 x64**、主Store8、DialogueStore5及69套件lock不變；無新套件、無新環境、無真實模型請求。

**新增診斷與WebView合成旅程通過；完整回歸仍有一項既有Windows剪貼簿讀取錯誤，不能標為full_passed。仍為候選版，未完成正式1.0、真實達哥或完整Hermes驗收。**

## 操作流程精簡工作單

2026-10-27更新 [SOL 6.1 改版工作單](UX-SIMPLIFICATION.md)，聚焦從需求到成果的同頁操作，並補上 Job 與 Skill 的操作分工、共用能力檢查的提示修正，以及一位助理、零 Skill 的驗收旅程。TO-AGENT 同步指向這份工作單，明示接手者需修改程式，MD 不會自動套用。這次只交付文件，未修改 App、依賴、資料庫或 wheels，產品仍為 rc5。程式閱讀已核對主對話補充、inline 自動預覽、工作卡、能力提示、成果及排程入口；現場跳轉原因仍未重現，也未完成新版 GUI 或人工使用性驗收。

專案 Python 3.10.4 x64 執行 `scripts/test_runner.py --suite targeted --tests tests.test_instruction_docs`，本次選取 6/652 項，6 項通過，0 失敗、錯誤或跳過，exit code 0。更新後的工作單及 TO-AGENT 引用通過既有本機連結檢查。未重跑 quick、full、WebView 或真實 API；下方既有剪貼簿失敗與現場未測狀態不變。原始結果留在忽略的 `artifacts/testing/latest.json`。

## 現行架構圖文件檢查

2026-10-27依程式基準 `aae9836` 新增[系統架構圖](ARCHITECTURE.md)，包含總覽、對話、代理、排程、資料與診斷六張 Mermaid 圖。已核對 WebSession 組裝、CLI 共用 WebBridge、兩種 LangGraph 路徑、資料庫檔案與待接線介面。這是靜態架構核對，不是全功能或現場驗收。

架構圖的本機引用納入既有文件測試，以 Python 3.10.4 執行 `scripts/test_runner.py --suite targeted --tests tests.test_instruction_docs`，6 項通過，exit code 0。這些測試驗證文件契約與連結，不驗證 Mermaid 渲染或產品執行。App、依賴、資料庫及 wheels 未修改，未重跑 full 或呼叫真實服務。

推送後已在 GitHub Preview 逐一檢查六個 Mermaid iframe，全部有圖表 SVG 與對應節點文字，沒有 Parse error、Syntax error 或 Unable to render。瀏覽器截圖擷取不可用，因此未將此項記為完整視覺排版驗收；渲染結果留在本機 `artifacts/architecture-render.json`。

## 開發 Skills 文件檢查

2026-10-25加入三個pstack精簡開發Skills；產品仍為rc5，未修改App、依賴、資料庫或69個wheels。只擴充原有文件案例的metadata／引用檢查，沒有新增測試案例數量。以專案Python3.10.4 x64執行 `scripts/test_runner.py --suite targeted --tests tests.test_instruction_docs`：**6項通過、0失敗／錯誤／跳過**，案例0.103秒，含入口8.15秒。原始結果在忽略的 `artifacts/testing/latest.json`。本輪沒有重跑quick、full或GUI，也未改寫下方既有失敗紀錄。

檢查涵蓋三份Skill的YAML、名稱唯一性、名稱與資料夾一致、手動啟動旗標，以及Skills／角色／prompt／接手文件的本機連結與章節。固定上游提交與授權已核對，完整來源及改編差異見[第三方說明](THIRD-PARTY-NOTICES.md#pstack-開發-skills)。

Codex隨附的 `quick_validate.py` 對三份原檔均回傳exit 1：它的欄位白名單不包含VS Code的 `disable-model-invocation` 與 `user-invocable`。這是驗證器格式差異，未移除手動旗標或修改驗證器來假裝通過；本專案文件檢查依[VS Code格式](https://code.visualstudio.com/docs/agent-customization/agent-skills)驗證這兩欄為真正的布林值。實際Copilot載入仍須現場確認。

以下為維護者對指引及既有程式的**靜態情境走查**，不是Copilot／模型執行測試，也未呼叫達哥：

| 去識別情境 | 核對結果 |
|---|---|
| 助理A目前修訂聊天通過；B有舊修訂通過、目前修訂失敗 | 先按匿名標記／修訂／項目／時間分組，查B目前結果，不複製A或B舊證據。對照diagnostics的revision檢查及狀態讀取；不要求四角色或AD才排錯。 |
| 聊天送出逾時，只有未知POST，沒有已知run | 保留原request與內容，不換ID或透過重測派發；查原收據。對照DialogueService的retry_unsent／recover及diagnostics未結束請求守護，缺帳本不等於未送出。 |
| .venv已存在、doctor報lock缺件，pip check成功 | 列缺件與核准離線包完整性，停止反覆安裝；不覆寫舊環境、不連外降版。對照install-offline的既有環境拒絕及安裝前bundle驗證；新環境／修復另依具體部署方案處理。 |

公司VS Code版本／政策下的發現、手動呼叫及修復成效仍 `not_tested`；不聲稱token節省或正式服務已修復。

## 實際結果

| 範圍 | 結果與界線 |
|---|---|
| 定向驗證 | 診斷、原對話恢復、工作區與安全ZIP的29項通過；後續診斷／文件連結12項通過，含入口2.00秒。 |
| quick | 480項、102.77秒；有1項既有文件連結檢查失敗。原測試把`#章節`當檔名，修正為分別檢查檔案與章節；定向及後續full中的該項通過。沒有重跑整套quick或將原失敗改記成功。 |
| 一次完整回歸 | 652項、346.11秒；**651通過、0 failure、1 error、0 skip**。唯一錯誤為Tk長訊息測試的Windows剪貼簿讀回`OpenClipboard error 5`。 |
| 剪貼簿追查 | 原案例單獨重跑仍error5；唯讀API檢查以無視窗及自己的視窗呼叫均被拒絕，當時未見其他持有者。根因未確認，沒有停用防毒、調整權限或移除／放寬測試。WebView實體剪貼簿仍not_tested。 |
| 環境 | doctor、pip check及lock一致；診斷使用暫存合成設定，沒有修改個人設定、金鑰或原環境。這不證明真實助理憑證可用。 |
| 診斷服務 | `mock_passed`：兩助理隔離、聊天／進階分開、認證／權限／404／限流／網路／逾時／格式／上下文分類、取消、重開未完成、版本失效、保留兩修訂、損壞與寫失敗。摘要不授予能力。 |
| 恢復與隱私 | `mock_passed`：未知送出不經重測再派發；既有已知run恢復保障保留。查看／工作單／安全ZIP零模型請求，植入秘密未出現在分享內容；原訊息與草稿保留。 |
| 真WebView2 | `local_real_passed`僅指實際宿主與合成旅程：兩入口、Plan、八次啟用；兩助理診斷、工作單預覽、模擬剪貼簿拒絕後另存、保存失敗保留預覽、明確指定項目重測及原對話診斷。深淺、1050×700、一般及最大化；必要按鈕可達。原生檔案選擇返回值為fixture，未冒充人工操作。 |
| 離線來源 | 69個wheels全部來源／SHA256／lock核對，暫存materialize後清除，零下載。依賴未變，不重新安裝或重建venv。 |
| 文件／素材 | 現行本機連結檢查無缺件；三支相關JS語法與diff檢查通過。截圖替換現有四張，不新增歷史包。 |
| 未實測 | 真實達哥、搜尋來源品質、公司Copilot、選用AD、真人使用性、實體IME、Excel、WebView實體剪貼簿。Norton成效未能確認。 |

## 證據與處理順序

[完整回歸摘要](validation/development.json)保留`passed=false`及唯一錯誤；[交付摘要](validation/workbench.json)分列定向、quick、full、WebView與未測項目。原始full／quick／沙箱失敗留在忽略的artifacts，公開摘要移除絕對路徑與原始輸出。

首輪沙箱定向測試被檔案原子替換與系統TLS存取拒絕；同一Python在正常Windows測試程序下相關32項通過。這沒有靠關閉TLS或防毒解決，不能將沙箱失敗當產品回歸通過。

現場先用三欄設定與聊天檢查，再分項驗證工作／搜尋。普通聊天不需四角色或AD；選用AD登入的部署另驗收。遇到問題預覽修復工作單交給[TO-AGENT](../TO-AGENT.md)，不要交出金鑰或整份SQLite。Windows剪貼簿讀取仍需在實際桌面釐清；目前可改用已驗證的Markdown另存。

畫面：[深色診斷](images/workspace-dark.png)、[淺色成果](images/workspace-light.png)、[1050×700淺色診斷](images/workspace-small.png)、[計畫確認](images/task-preview.png)。

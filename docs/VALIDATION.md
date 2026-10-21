# 0.23.0 自建 Skill 與單助理 Plan 驗證（2026-10-21）

主schema8、正式69套件lock不變；未新增依賴或環境。使用Python **3.10.4 x64**，隔離空白本機資料進行驗證，沒有真實模型或公司服務請求。[交付摘要](validation/workbench.json)、[完整紀錄](validation/development.json)。

| 範圍 | 結果與界線 |
|---|---|
| 完整回歸 | **未通過：602通過、1錯誤、0跳過**；測試168.49秒，連環境檢查170.59秒。唯一錯誤是既有Tk訊息框剪貼簿讀回：OpenClipboard Windows error 5。環境、pip及lock檢查通過。 |
| 最後審查修正 | 登入過期後Skill取消已生效，但UI後續讀狀態被擋；改回最小取消收據。最後程式定向跑14項：**13項Skill通過、1項既有剪貼簿仍錯誤**，未重跑整套；full載入時在此小修正之前。 |
| WebView | **31項完整合成旅程通過**；手冊入口最後增補後，同一Skills定向旅程再通過。涵蓋空白／範例、四型別條件、Plan修改／取消／批准、成果、排程同意／暫停、複製／刪除、Markdown讀寫及深淺／小窗按鈕可達。 |
| 服務 | 方法修訂固定、未批准零派發、同助理上下文隔離、未知規劃POST阻擋、同ID恢復、晚到回覆、搜尋收據斷言、來源刪除及schema1～7備份／失敗回復均有離線合成案例。 |
| CLI／離線包 | CLI共用服務，非互動管線不能批准；跨目錄入口、退出碼與中文JSON通過。69wheels逐檔hash／來源／lock一致，沒有重建環境。 |
| 真實服務／人工 | **not_tested**：DVC格式與實際搜尋品質、AD、真人使用性及IME。原生檔案選擇以暫存路徑替代，格式讀寫實測；不能宣稱人工選檔已驗收。 |

目前交付為0.23.0實作候選版，**不是完整回歸通過或正式上線核准**。剪貼簿讀回須在實際使用者Windows桌面確認，未跳過測試或調整系統權限。原沙箱原子取代限制曾造成合成profile保存失敗，正常Windows執行通過；未放寬原子保存。WebView首次Skills導航busy狀態曾漏載頁面，已修正；後續測試等待曾誤抓已關閉modal，修正等待條件。原始失敗保留本機artifacts，公開結果去識別。未修改使用者既有助理憑證；本機測試不表示它們可用。

畫面精選已替換為本版，未新增一套歷代截圖。下方是歷史驗證，不能替代當前結果；歷史引用的development.json現為本版，舊詳細證據由Git查閱。

## Code ZIP 離線交付驗證（2026-10-01）

本次改動只補齊 GitHub Code ZIP 的 App 離線來源及安裝診斷隔離；lock、AD、App 功能與舊 Release 不變。實際下載公開遠端 `54767c7a58be4b30870eee04a4352899f2f992d6` archive（20,062,294 bytes），驗來源 MANIFEST、69 個 wheel 二進位及雜湊後，在 MSI 的新目錄執行真正 `install-offline.bat`，不連網補件。原環境未覆蓋。

| 範圍 | 本次結果 |
|---|---|
| 安裝 | **通過**：69 wheels、Python3.10.4 x64／Tk、pip check、doctor、freeze精確符合原lock |
| 完整回歸 | **570通過／571執行，0failure、1error、0skip**；唯一錯誤是長訊息剪貼簿讀回 `OpenClipboard` 被Windows拒絕（error5），單獨重測仍失敗 |
| Code ZIP／installer 定向測試 | **19/19通過**，含損壞、缺檔、LFS指標、不安全路徑、lock不符拒絕，以及暫存診斷／既有資料保留 |
| WebView合成UI | **25/25通過**；MSI真實WebView2，provider與公司SDK為合成 |
| 原生展示登入生命週期 | **3/3通過**，先登入、帶未送出草稿登出、WebView關閉及暫存清除 |
| 一鍵入口 | full模式因回歸錯誤正確停止；另跑`test-company.bat ui`通過，不將它宣稱成full通過 |
| 真實公司DVC／AD／人事使用資格／Oracle | **未執行** |

[去識別證據](validation/code-zip.json)。剪貼簿拒絕尚未解決；唯讀探測在Tk外也出現error5，而input desktop可讀、未見busy window，無法據此判定具體權限／桌面政策原因。未放寬Windows權限、跳過測試或修改公司政策；公司端若同樣失敗，需由核准的互動桌面確認剪貼簿可用性後重跑，不能當公司服務通過。最初安裝因診斷誤讀MSI既有助理設定而停止，已以隔離診斷修正並從另一個遠端ZIP新資料夾安裝通過。最後證據提交只改文件及清單，runtime／wheels與上述已測commit相同，另核對最終遠端ZIP。

以下為先前 Release 登入與待辦版歷史驗證，不能代替本次 Code ZIP 的結果。

# 本次待辦與一鍵交付驗證

2026-09-30，0.21.0登入與待辦版，基於0.20.0/e189eda工作樹；發布依使用者後續明確授權另行執行。主schema6、dialogue schema2、69套件lock未變。

| 範圍 | 本次實際結果 |
|---|---|
| 乾淨離線安裝 | **local_real_passed**；正式69wheels逐檔雜湊及lock通過，Python3.10.4 x64、doctor、pip check、freeze精確相符。[證據](validation/todo-offline-install.json) |
| 正式完整回歸 | **566/566、0failure、0error、0skip**；測試164.488秒，含環境168.92秒。SDK／公司協定為mock_passed；SQLite、Tk及Windows本機為local_real_passed。[證據](validation/development.json) |
| 一鍵入口 | 乾淨環境 `test-company.bat` 實際exit0：語法、566項full、25項WebView通過；之後補登出草稿關閉與原生登入生命週期入口，僅重跑ui與受影響檢查。company_real仍not_tested。版本／打包文字不另重跑full。 |
| WebView2 | **最終25/25合成旅程通過**；深／淺、小視窗與最大化、主對話草稿保留、來源刪除副本、重複保存／空值／取消／搜尋核准均通過。MSI真本機WebView2，provider及公司SDK均合成。[證據](validation/todo-webview.json) |
| DVC | 全文讀取官方Assistant API2719802/v68、插件2720034及DSE2719790，逐項對照實作；[核對紀錄](DVC-REVIEW.md)。文件閱讀不是公司服務通過。 |
| lint／型別／build | 專案無獨立lint／typecheck／編譯build設定；Python AST語法檢查及application_html產生、JS／CSS在真WebView2載入由一鍵與UI驗證涵蓋，未宣稱另跑mypy／ruff。 |
| 真公司Assistant API／搜尋 | **not_tested**；未讀取key，未執行--live；來源、日期、工具副作用、部署相容仍需公司核對。 |

第一次乾淨安裝因開發機舊20wheels與根lock指紋不符而**失敗**，尚未建立環境；沒有繞過驗證。改用既有正式v0.20.0 ZIP的根wheelhouse69wheels後才安裝通過；登入版再次新建驗證環境安裝亦通過，原有.venv及舊wheelhouse保持。初次新增測試fixture與UI等待／基準斷言問題曾失敗；最終新增來源刪除檢查曾因測試直接刪除目前對話且未同步目前ID而失敗，修正測試先移開對話後通過，修正後上述通過；沒有刪測試、skip或放寬安全規則。登入版新增測試曾誤用不存在的方法及只讀catalog作派發斷言，修正後26項受影響測試通過；新增UI測試曾嘗試被封鎖的重新載入，改用既有新增對話流程後通過。完整證據不得引用先前561／563項報告當登入版結果。

公司仍需核准Python3.10.4完整安裝、WebView2、.NET、CA與公司endpoint、各Assistant ID及Windows認證管理員key。多ID權限、搜尋來源品質、AD／Oracle／舊資料、IME／Excel人工操作、跨螢幕DPI均not_tested。使用者的市場日報排程沒有啟用；UI中的排程測試僅存在即用即棄的合成工作區。

交付到新目錄安裝，再用 `test-company.bat`；詳細失敗訊息、報告位置與公司實測入口見 [操作](ONE-CLICK-TEST.md)。不含Python／WebView2／.NET安裝器或憑證。

登入展示：原生登入錯誤／空值／成功／公司禁用由tests.test_authentication驗證；實際原生登入→WebView→有草稿登出→暫存清除另有 [生命週期證據](validation/demo-login-launch.json)。展示不是公司權限，人事App使用資格仍未接線。

最終 `test-company.bat ui` exit0，Python語法、25/25 WebView旅程與3/3實際登入生命週期檢查全部通過；[入口證據](validation/company-test-ui.json)。沒有公司服務呼叫。

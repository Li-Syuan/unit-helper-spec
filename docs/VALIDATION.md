# 0.22.0 交辦工作與 CLI 驗證（2026-10-21）

本版增加共用交辦服務、schema 7、CLI 與 WebView 系統匣；沒有新增依賴或重建環境。使用現有 Python **3.10.4 x64**、69 套件 lock，採獨立空白示範資料目錄完成離線驗證。最新範圍見 [交付證據](validation/workbench.json)及[完整執行紀錄](validation/development.json)。

| 範圍 | 結果與界線 |
|---|---|
| 本機完整回歸 | 590 項，零失敗、錯誤或跳過；包含 SQLite 遷移、真 Tk、批准、防重、取消、身份與工作區互斥。實測耗時見 JSON。 |
| WebView | 29 項真 WebView2 合成操作旅程；包含交辦補問、預覽取消、試跑、示範不建真排程、聊天草稿保留及深淺／小視窗。 |
| 系統匣 | 真 WinForms NotifyIcon 建立、隱藏、還原及清除通過；UI 關閉選項及偏好通過。人工點擊作業系統 X／系統匣菜單的完整退出旅程仍未測。 |
| CLI／離線包 | 從不同工作目錄啟動、中文 JSON、管線不能批准、錯誤退出碼通過；69 個 wheels 逐檔雜湊、lock 及來源一致。未重新安裝正常環境。 |
| 達哥／AD／來源品質 | **not_tested**。規劃 JSON、搜尋工具、日期來源、真實權限與公司多輪對話仍需現場驗收；本輪零付費／公司模型請求。 |
| 人工使用性 | 真人關閉／系統匣、睡眠／關機、IME 等未實測，不以程式操作宣稱通過。 |

原使用者資料目錄的首次 full 預檢因 `credential_store_unavailable_or_empty` 停止，當次測試 **not_run**；套件仍與 lock 一致。改用隔離示範資料目錄是為驗證程式，不表示原助理金鑰已修好，未更改原設定。沙箱檔案原子取代受拒曾使保存測試失敗，正常 Windows 權限執行後通過，未放寬程式檢查。WebView 曾發現「每天08:00」解析缺陷，已修正並保留回歸；獨立審查另找到登入到期擋住取消／退出，修正只允許本機收尾，不允許新派發或讀取成果。原始失敗及修正前紀錄留在本機 artifacts；公開證據去識別。

以下為歷史驗證；舊版引用的 development.json 現已更新為本版，當時詳細證據可由 Git 歷史查閱，不代表本版仍有相同問題或已通過公司服務。

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

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

# 公司 Code ZIP 首次安裝：直接複製給 Copilot

請先開啟 [COPILOT-START-HERE.md](COPILOT-START-HERE.md)，複製完整提示。它包含目前 Code ZIP 的入口、已知 OpenClipboard error5 與正式公司 AD／資格先於 DVC 的順序。

下方保留 v0.21.0-rc.1 Release 的原交接內容及當時測試結果；**目前 Code ZIP 的結果以 [VALIDATION](docs/VALIDATION.md) 為準**，不能把先前566項通過視為本次公司環境通過。根目錄此文件沿用既有附件內容，並修正範例路徑隱藏字元；未更動 Release 附件。

# VS Code Copilot 接手：公司首次離線驗證

用 VS Code 開啟解壓後的整個專案資料夾，使用公司允許的 Copilot Agent 模型與權限；Copilot 是否能連線由公司政策決定，不能宣稱離線可用。

可貼給 Agent：

請先全文讀 AGENTS.md、README.md、docs/ONE-CLICK-TEST.md、docs/COMPANY-IMPLEMENTATION.md、docs/DVC-REVIEW.md、docs/VALIDATION.md、docs/LOGIN-AND-APP-ACCESS.md。檢查既有修改並保留，不覆蓋公司 adapter、設定或環境。

1. 核對公司核准的 Python 恰好3.10.4 x64完整版（含Tk）、WebView2、.NET Framework4.6.2以上。缺軟體就報告，不擅自連網下載安裝、不更動全機環境。
2. 新資料夾乾淨安裝：install-offline.bat "C:\approved\Python3104\python.exe"；69wheels雜湊／lock不符立即停止，不繞過或補件。
3. 執行test-company.bat，區分offline/synthetic/local與company not_tested，不能把mock通過當公司通過。
4. start-demo-login.bat → admin/admin，測登入／待辦來源導航、搜尋、到期、人工完成與登出。這是暫存合成工作區，關閉清除；一般本機／已登入公司工作區是持久資料。展示登入不授予公司權限、不載入正式設定、不允許公司連線。
5. 正式AD／SSO與人事App使用資格閘門接好並核准後，才啟用identity_mode=company，再登入並設定／分別驗DVC metadata、聊天、核准搜尋及已知答案／來源。未接線或未授權拒絕，不退回admin。不得啟用市場日報排程或擅自呼叫有寫入副作用的工具。

公司使用者尚須提供：AD／SSO方式與可信驗證接口；人事資料來源及最小schema（穩定employee_id／在職狀態／資格所需欄位，不索取整份個資）；指定員工白名單或部門等核准使用規則；核准DVC endpoint、Assistant ID、認證保存方式、CA、工具政策及已知答案測例。尚未決定的授權範圍不得自行猜測，不能建立真實admin或持續存取憑證。

桌面登入與本機資料夾只是UX門檻，真正API／查詢須由可信後端驗使用資格。DVC API key／分享不取代AD。舊DVC Task Management頁未完整取得，這不阻塞本機待辦與展示，但遠端任務管理不能宣稱驗收通過。

本版MSI實測：566/566 full，25/25 WebView合成旅程，3/3原生展示登入／有草稿登出／暫存清除檢查。公司AD／人事／DVC／Oracle／真實來源品質尚未驗證。

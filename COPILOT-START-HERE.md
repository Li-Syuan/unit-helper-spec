# 公司 Code ZIP 首次安裝：直接複製給 Copilot

先下載目前 main 的 **Code → Download ZIP**，解壓完整資料夾到新位置，再用 VS Code 開啟包含 `install-offline.bat` 的根目錄。選擇公司允許的 Copilot Agent／模型與權限，將下方整個區塊複製貼上。Copilot 是否可連線由公司政策決定，本文件不宣稱它可離線使用。

```text
請協助我在公司安裝並驗證這個 unit-helper-spec 桌面 App。請實際檢查再操作，不要只給建議，也不要把未執行步驟宣稱通過。

1. 先完整閱讀根目錄 AGENTS.md（若有）、COPILOT-HANDOFF.md、README.md、offline-app/README.md、docs/ONE-CLICK-TEST.md、docs/COMPANY-IMPLEMENTATION.md、docs/DVC-REVIEW.md、docs/VALIDATION.md、docs/LOGIN-AND-APP-ACCESS.md；閱讀 install-offline.bat、scripts/install-offline.py、scripts/code_zip_bundle.py、scripts/offline_bundle.py、test-company.bat、scripts/company-test.py、start-demo-login.bat 的相關實作。檢查並保留公司既有修改、adapter、設定、工作區與虛擬環境。

2. 核對公司核准的 Windows Python 必須恰為 3.10.4 x64 完整安裝版，包含 Tcl/Tk、venv、pip；WebView 主介面需 Microsoft Edge WebView2 Runtime 與 .NET Framework 4.6.2 以上。取得使用者確認的實際核准 Python 路徑，不要猜測。確認解壓資料夾及暫存目錄可寫；缺前置軟體或必要權限就停下回報，不擅自連網下載、升級公司 Python、修改全機環境或權限。

3. 使用完整 Code ZIP 自附的 wheels，在新解壓資料夾根目錄以 CMD 執行：
   install-offline.bat "C:\approved\Python3104\python.exe"
   請把引號內路徑換成公司實際核准的 Python 3.10.4 x64 路徑；此範例不是已知公司路徑。BAT 只接受此 Python 可執行檔作為第一個參數。它會建立專案自己的 .venv，不覆蓋公司 Python 或既有 .venv；已有環境時另用新解壓資料夾，不刪除或覆寫。App 依自己的 requirements.lock 安裝 69 套件，共用 lab 的 48 個 wheels 與 offline-app/packages 的 21 個；不用 lab lock，不改套件版本，不連網補件，不繞過 SHA256／lock／LFS 指標拒絕等完整性檢查。等待安裝診斷、pip check、freeze 比對及退出碼確認成功，不能以 pip 安裝成功代替整個安裝通過。

4. 安裝成功後在根目錄 CMD 執行 test-company.bat。預設已包含完整本機回歸、合成 WebView 操作及原生展示登入生命週期，不必無理由另外重跑 full。明確列出通過、失敗、未執行；本機／合成／mock 不等於公司服務通過。保留 artifacts/installation/latest.json、artifacts/company-test/latest.json、artifacts/testing/latest.json、artifacts/web-smoke/result.json、artifacts/login-launch/result.json 及錯誤摘要，分享前遮密、去識別。
   已知最新 Code ZIP 驗證：安裝通過，完整回歸 570 通過／571 執行、1 error、0 failure、0 skip；Windows OpenClipboard 讀回出現 error 5，單獨重測仍失敗。不要跳過／刪除該測試、放寬權限或將結果改成成功。先診斷並保留證據；可單獨執行 test-company.bat ui 檢查不受影響的 UI，但必須標示它不能代替 full 通過。既有 WebView 25/25、原生登入 3/3 通過是先前 MSI 的結果，不能冒充本公司環境已測。

5. 完成驗證或明確記錄阻礙後，執行 start-demo-login.bat，以 admin / admin 登入離線展示，檢查錯誤／空值、登入、對話、待辦來源導航、搜尋／編輯／取消／重複操作、人工完成，以及帶未送出草稿登出與暫存清除。這組帳密僅是離線 fixture，不是公司帳號或管理員授權；展示工作區暫存且登出清除，一般本機工作區則持久保存。展示模式禁止公司連線設定，不能用它接真實後端。若你沒有實際 UI 操作能力，請我依步驟操作並回報結果，清楚標示哪些仍待人工驗證，不冒充已點擊或已測。

6. 發生錯誤先報告現象、實際命令／退出碼及去識別證據，再診斷；只修正這個專案內可授權的問題並跑受影響測試。不要覆蓋公司既有修改，不新增無關功能；需要公司核准、軟體、權限或真實設定就停止相依步驟並列出最少必要資料。不要自行 commit／push／部署或上傳公司資料。

7. 不讀取、顯示或上傳公司密鑰、AD 密碼、個人資料、內部回應或資料庫內容；不變更 TLS 驗證、CA 信任、代理／防火牆、帳號權限或持續憑證，不繞過公司網路限制。不自行連正式 DVC、AD／SSO 或人事資料來源，不呼叫有寫入副作用的工具，不啟用市場報告排程。

8. 正式接線順序是：公司核准並實作 AD／SSO 驗身分 → 可信伺服器驗人事在職狀態及 App 使用資格 → 驗收登入與拒絕／查詢失敗皆不放行 → 啟用 company 模式登入 → 另外核准 DVC endpoint、Assistant ID、認證保存方式、CA 與工具政策 → 才做真實 metadata／對話／搜尋及已知答案與來源驗收。AD 失敗不可退回 admin/admin。桌面登入只是 UX 門檻，所有 API／查詢都須由可信後端驗資格。請先向我索取 AD／SSO 形式、人事來源與最小 schema、核准使用規則（指定員工或部門尚未決定）及 DVC 設定；不要猜人事 schema、授權範圍或建立真實管理員帳號。DVC 文件閱讀與本機合成測試不等於真實公司 API 已驗證；舊 Task Management 文件未完整取得，不宣稱所有 DVC 規範都已讀完。

最後請交付實際執行順序、修改檔案、通過／失敗／未執行數、報告位置與剩餘公司條件，讓我能判斷是否可使用及下一步要提供什麼。
```

相關內容：[完整交接說明](COPILOT-HANDOFF.md)、[Code ZIP 安裝](offline-app/README.md)、[實測結果](docs/VALIDATION.md)。本文件只提供操作指示，不代表公司環境已驗收。

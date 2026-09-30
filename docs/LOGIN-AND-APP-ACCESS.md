# 登入展示與 App 使用資格

## 為何原本沒有登入頁

既有原生登入頁位於 desktop_app/login_view.py。identity_mode=company 在 Web/Tk 開資料庫及啟動排程前要求 company_auth.py 驗證；預設 demo 直接開本機工作區，--login-preview 僅預覽畫面。公司 hook 目前 is_configured=False，沒有完成 AD 接線；登入會停止，不自動退回本機或 admin。

## 離線展示

執行 `start-demo-login.bat`（等同 `.venv\Scripts\python.exe -m desktop_app --demo-login`），使用 **admin / admin**。這是明示且獨立的合成 fixture，不是管理員權限、AD 帳號或公司預設帳密。帳號欄不預填密碼，密碼不保存／記錄；登入成功後只開新建的空白暫存工作區，不載入原設定、keyring 索引或歷史。關閉清除展示工作區；沒有「記住登入」。Python 記憶體不宣稱安全抹除。

展示禁止公司連線設定、助理／金鑰變更及 metadata probe，沒有真實 API／Oracle。右下「登出並關閉工作區」經確認後撤銷本次記憶體階段、阻止新操作並關閉視窗。一般本機入口仍保留；它不是公司授權入口。--demo-login 不能混用 --config、--groq-trial、--login-preview 或 Tk。

## 公司與人事使用資格

使用者已澄清人事用途是「哪些人能使用 App」，不是员工資料卡的閱讀權限。沿用既有 company_auth.authenticate(employee_id,password) 回應契約，不新增人事資料庫、LDAP 套件、帳密、白名單或部門規則。

待公司實作的可信流程：AD 驗身分 → 從驗證結果取得穩定 subject／employee_id → 查人事在職狀態 → 檢查核准 App 使用资格（指定員工或部門，尚待決定）→ 回傳 authenticated、allowed、身分與有限 expires_at。未知工號、停用、未核准、資料缺失及查詢失敗均拒絕；AD 成功但資格未通過顯示「尚未開通使用權限」。錯誤不得露出人事內容、密碼或服務回應。

目前桌面 hook 和本機 subject 資料夾只是 UX 門檻與避免混用資料，使用者可改本機程式／設定，**不能充當可信安全邊界**。真正公司後端必須驗證可信登入憑證與 App 使用資格，所有 API／查詢再檢查；不能接受桌面任意送入的 employee_id／allowed。期限與撤權由服務端控制，不能以本機八小時期限宣稱即時 AD 撤權。

接線前先核准驗證服務契約、來源／timeout／CA、授權政策與稽核，再由公司維護者修改 company_auth.py；不得以 AD 失敗回退 admin/admin。現有契約和範例見 COMPANY-HANDOFF.md「AD 登入與作者資訊」。本次未連 AD／人事，不接受或配置公司安全設定，不建立持續存取。

## DVC 邊界

本次沿用已全文核對的 Assistant API 第68版、插件與 DSE；DVC API key／助理分享不是 AD 或 App 使用资格。官方頁與要求對照見 DVC-REVIEW.md。舊 Task Management 頁未完整取得，不宣稱全部 DVC 文件已讀；本次無遠端任務／循環排程，因此這不阻塞展示登入與本機待辦驗收。

正式UI顺序：離線安裝／test-company → 接AD與App使用資格 → company登入 → 核准DVC設定與metadata／聊天／搜尋實測。既有check-assistants.py --live只供另經核准的診斷，會產生遠端請求，不是正式登入或授權的替代；本次未執行。

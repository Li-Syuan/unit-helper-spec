# 本機實作驗證紀錄 — 0.3.0

本次完成 Windows x64／CPython **3.10.4**／Tk **8.6.12** 的兩個獨立 venv 驗證。每個環境 **65 項測試通過，0 skipped**；pip check 成功，pip freeze --all 與 requirements.lock 完全一致。

## 可核對證據

- [開發環境原始輸出](docs/validation/development.json)
- [第二乾淨環境原始輸出](docs/validation/clean-rebuild.json)
- 證據含 UTC 執行時間、實際直譯器完整路徑、版本、架構、Tk、全部套件、逐項測試及 exit code。
- 開發直譯器：`github-unit-helper-spec/.venv/Scripts/python.exe`。
- 重建直譯器：`github-unit-helper-spec/.venv-verify/Scripts/python.exe`。
- 兩者各自 site-packages，`include-system-site-packages=false`，由同一官方 CPython 3.10.4 建立；沒借用 Conda 或其他專案環境。
- `scripts/setup.ps1 -PythonExe .runtime/python3104/python.exe -Environment .venv-verify -CaBundle .runtime/windows-ca.pem` 實際成功；公司使用自身核准的直譯器／CA。

重跑並保存證據：

```powershell
.\.venv\Scripts\python.exe scripts/verify.py development
.\.venv-verify\Scripts\python.exe scripts/verify.py clean-rebuild
```

verify 會拒絕 0 tests、任何 skip、非零 exit code 或套件與 lock 不符。程式不需要真實 API 金鑰即可通過基準。

## 各項驗證邊界

| 項目 | 本次結果 |
|---|---|
| 環境／依賴 | local_real_passed：兩環境確切版本、64 位元、真 Tk root、pip check、鎖檔一致 |
| SDK | mock_passed：真 OpenAI SDK + httpx.MockTransport；request／headers／assistant ref、session 資料隔離、401、timeout、空白／異常格式／工具回覆、TLS／CA、禁重導與 retry |
| Plan／任務 | local_real_passed：未批准零 dispatch、修訂／過期／取消、並行重複批准、防重、真 future drain、摘要部分失敗保表格 |
| typed 選項 | local_real_passed：owner、是非／多選、數量／未知值、過期、取消、持久化及 idempotency |
| TXT／CSV／輸出 | local_real_passed：大小／UTF-8 BOM／錯編碼／欄數、精確字串、公式防護、CSV quoting、全部／選取／跨頁、snapshot 不變 |
| 排程／通知 | local_real_passed：可控制時鐘測每日／每週、前一日解析、漏跑、重啟、防重、停用、非空改變／門檻、失敗通知，不等待隔天 |
| Tkinter 桌面 | local_real_passed（程式操作）：真 Tk widgets，對話→Plan 修改批准→查詢→分頁→Windows 剪貼簿、回報草稿、排程與通知、選項對話框、可見八頁、關閉等待／重開保存 |
| 人工滑鼠／鍵盤 GUI 與外觀 | not_tested：Computer Use helper 啟動失敗 `apply deny-read ACLs`，未完成 OS 層操作與截圖人工檢視；不能以程式控制項測試冒充人工驗收 |
| 公司 chatbot | not_tested：沒有公司端點／成功樣本／金鑰；示範文字不是 AI 生成 |
| AD／員工名單 | not_tested：只验证 demo 明示及正式未配置拒絕；非真 AD 登入 |
| Oracle | not_tested：三個合成查詢／參數驗證通過，未執行公司 SQL |
| Excel 真實貼上 | not_tested：Windows clipboard/TSV 通過，未在 Excel 驗證資料自動轉型 |
| 舊公司資料移轉、打包、中央更新 | out_of_scope：沒有執行 |

## 發現與修正

整合檢查修正跨功能修改錯誤計畫、取消後更換 client、派發前取消界線、背景 IO 計數、Tk after callback 清理、設定驗證先於寫檔等問題。
初次第二環境完整測試曾因 Tk 物件在背景執行緒釋放出現 `main thread is not in main loop`／`Tcl_AsyncDelete`，該次不算通過。改為背景工作 drain 後由主執行緒清理視窗、選項變數及 singleton lock，新增關閉回歸測試；上方兩份證據是修正後的完整重跑結果。

本機可執行不等於公司 production-ready。未實測項目已在 COMPANY-HANDOFF.md 列具體修改位置、內部資訊、正反驗收與執行命令。

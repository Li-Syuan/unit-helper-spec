# 離線試驗包驗證

本輪是可選實驗交付，QA agent 保持 0.15.0；未修改 App 程式、根目錄 requirements 或正式資料。證據見 [validation.json](validation.json)。

| 檢查 | 結果 |
|---|---|
| 全新 Python 3.10.4 x64 試驗環境，離線安裝 | local_real_passed |
| 複製到含中文／空白／單引號路徑，第二次全新離線安裝 | local_real_passed |
| 52 個鎖定版本、wheels SHA-256、pip check | 兩個環境均通過 |
| 每個環境 10 項測試 | 各 10 通過，0 失敗／錯誤／跳過 |
| 等待批准、拒絕、批准後分工、覆核不符停止 | mock_passed，使用真框架與合成節點 |
| SQLite 關閉再開、thread 隔離、不可信文字保持內容 | 通過 |
| 缺 wheel、內容變更、lock 變更 | 正確拒絕驗證 |
| 測試程序網路攔截 | 兩個環境均 0 次網路嘗試 |
| 三個獨立程序執行 demo | 未批准離開 → 重開批准 → 重開只讀成果，通過 |
| 正式 App doctor | local_real_passed，原 41 個鎖定套件未變 |
| 公司 API／多 assistant ID／真實 AI 回覆 | not_tested |
| 正式 App 的 LangGraph 整合 | not_implemented |
| 真人使用性、防毒成效 | not_tested |

安裝使用 `--no-index --no-cache-dir --require-hashes`；bootstrap pip 亦來自先驗雜湊的本機 wheel。沒有改動系統 Python、PATH、TLS、防毒或執行政策。兩個驗證環境在記錄證據、確認無程序使用及無連結跳轉後清除，只保留原日常 `.venv`。

這次未修改 App 的執行程式，因此沒有重跑整套 409 項桌面回歸。原本 0.15.0 的剪貼簿讀回未通過紀錄仍保留於根專案驗證文件，不能以本試驗通過取代。

SQLite 接續只驗證這個無外部副作用的合成範例。公司真實工具的授權、request ID、防重與失敗恢復需要接線後另外驗證。

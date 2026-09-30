# QA agent 0.20.0 驗證紀錄

本版為達哥接口修正候選版，完成未送出重試、明確的新連線轉交、個別金鑰、聊天搜尋核准及安全錯誤分類。正式69套件lock、主schema6、dialogue schema2、Assistants ledger schema1不變。

## 目前結果

| 範圍 | 實測結果 |
|---|---|
| 正式完整回歸 | **local_real_passed / mock_passed**，561/561、0失敗、0錯誤、0skip；測試157.94秒，連環境共160.34秒。[完整證據](validation/development.json) |
| Python與依賴 | 恰好3.10.4 x64、doctor、Tk8.6.12、WebView2/.NET、pip check與根lock精確一致。 |
| WebView2 | **local_real_passed**，22組合成旅程；深淺、1050×700、一般／最大化、未送出重試、搜尋往返、新連線轉交。[UI證據](validation/webview.json) |
| Assistants協定 | 真SDK＋MockTransport；兩個不同assistant ID各十輪、同thread追問、GET失敗恢復、未知POST零重送、舊批准與晚到取消隔離。**mock_passed**。 |
| 個別金鑰 | MemoryVault合成保存／更換／移除／共用回切，受影響revision撤銷、失敗保留原來源、残留清理警示、bridge無索引外洩與inflight guard。真Windows認證管理員的既有測試另包含於full，真實組織key未使用。 |
| 搜尋授權 | 普通聊天需獨立opt-in；舊policy不擴權，草稿／規劃停用，批次驗證／大小／取消／未知提交保護仍通過。來源與事實未驗收。 |
| 離線包 | 根lock及69個既有wheels不變；打包重新核對完整性。未重建環境，先前乾淨安裝證據見[離線安裝](validation/offline-install.json)，不可冒充本版新建環境。 |
| 真實達哥／多ID權限／搜尋 | **not_tested**。`check-assistants.py --live`為明確現場驗收入口，這裡只測合成傳輸。 |

完整檢查曾發現登入到期例外分類被包裝及一處舊按鈕測試定位；已修正後重新完整驗證。獨立檢查另發現inspect隱藏retry、修正key後fork沿舊版本，已補實際操作測試。初次失敗紀錄留本機artifacts，不將失敗改成通過；公開檔案只保留目前完整證據。

先前Windows剪貼簿error5案例本輪完整檢查通過，沒有刪除／skip／放寬斷言；這不等於已完成所有Excel或IME人工驗收。GUI均串行，沒有付費模型或組織網路請求。

## 交付界線

lock SHA256：`cb89c89a7d9176eab8bb533a42534370225427aac2d51d1a275ede55c7f75c4b`。常駐只有.venv，保留其基礎.runtime/python3104；沒有新增依賴或環境。離線ZIP由已提交來源產生，含69正式wheels；不含Python/WebView2/.NET安裝器、金鑰、publisher.json或使用者資料。雜湊是完整性檢查，不是數位簽章。

正式服務TLS／權限／工具副作用、四角色品質、AD／Oracle／舊資料、人工使用性、IME、Excel、跨螢幕DPI與PyInstaller均 **not_tested**。Norton成效 **未能確認**，未調整防毒、TLS或執行政策。App關閉不執行本機排程，取消不保證遠端立即停止。

儲存庫及候選Release公開；證據僅遮蔽本機絕對路徑，不改狀態、數量或耗時。介面圖片全為合成資料。不能將本機測試通過解讀為正式上線完成。

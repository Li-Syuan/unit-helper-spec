# 組織串接測試工具包

## 三種證據分開

- `tests/`：沒有真實正式服務；SDK 契約為 mock_passed，本機 SQLite／Tk 為 local_real_passed。
- `company_local/`：組織建立的本地測試與設定，預設忽略，不把內部資料推到 Git。
- 組織實測報告：只有明確執行組織測試 hook 且檢查成功，該項才為 company_real_passed。runner 本身不能證明 hook 寫得正確，需組織審查其斷言與人工比對證據。

## 離線契約

`test_support/assistant_contract.py` 抽出既有 SDK 測試，`tests/test_gateways.py` 仍繼承執行它們。可替換 adapter_class；不同協定須覆寫 request/response 斷言及 transport factory，不能把組織回覆硬塞成 OpenAI 格式來假通過。固定 wire 範例是純合成資料，位於 `test_support/fixtures/`。

`test_support/query_contract.py` 提供 QueryContractMixin 與 assert_query_result：檢查純 validate、未知／錯誤參數、結果欄列、UTC 時間、精度字串與截斷資訊。組織須覆寫 validation_guard，攔截真正 DB／HTTP 入口；只攔 run 不足以證明任意第三方 adapter 沒有 IO。空結果、row cap 與邊界樣本由組織依核准 SQL 補齊。

複製 `company_templates/test_company_offline.py.example` 到 `company_local/test_company_offline.py`，接入合成 transport 後執行：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gateways tests.test_contract_tools -v
.\.venv\Scripts\python.exe -m unittest discover -s company_local -p test_company_offline.py -v
```

範本未完成會明確失敗；不加入基準 discovery，不用 skip 充當完成。

## 真實組織驗證

複製 `company_templates/company_hooks.py.example` 到 `company_local/company_hooks.py`。每項 None 維持 not_tested；用有 timeout 的真實測試函式取代。函式須先完成檢查／assert，再回傳 True；不能只回傳 True，不能註冊 DemoQueries 或 mock transport。

```powershell
# 不載入 hooks，也不呼叫任何服務；預期 exit 2、not_tested
.\.venv\Scripts\python.exe scripts/company_check.py
# 先完成組織測試助理副作用能力審查，僅使用核准測試環境
.\.venv\Scripts\python.exe scripts/company_check.py --hooks company_local/company_hooks.py --execute --capabilities-reviewed --output artifacts/company-check.json
```

`--capabilities-reviewed` 是操作者確認已完成組織審查，不會替助理關閉工具。hook 是可信任可執行 Python，不是 sandbox；只載入組織審查過的本地程式。不得自動下載／執行模型產生的 hook。診斷 doctor 不會啟動這個流程。

runner 拒絕 Python -O／-OO，避免 assert 被移除而誤報通過。Python 層的 hook 標準輸出／錯誤輸出會抑制；組織 hook 不得自行寫秘密 log 或啟動會洩漏資料的外部程序。

exit 0：全部註冊必需項通過；exit 1：失敗；exit 2：尚未全部測試。報告只列固定 case ID、狀態與安全代碼，不附回覆或錯誤本文。真實 GUI／Excel、人工 SQL 比對與授權派發 gate 的詳細證據仍需填入組織驗收文件；runner 通過不是全產品上線許可。

AD 骨架涵蓋允許、拒絕、停用、逾期，正式 adapter 與服務授權尚未實作。拒絕測試必須比對組織錯誤代碼，不能把連線逾時也當授權拒絕通過。

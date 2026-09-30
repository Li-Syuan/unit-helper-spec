# 本次 DVC 契約核對

2026-09-30：DVC 指的是 **DaVinci Ai platform／達哥**。依本機 AGENTS.md、接線文件的引用找到官方文件，沒有當成 Data Version Control。

## 實際完整讀取

- [Assistant API 介紹：2719802，第 68 版](https://dvcaiplatform.atlassian.net/wiki/spaces/DW/pages/2719802)：匿名公開 Confluence v2 API 取得原文，包含分享／權限、Gradio、客製參數、curl、Python及 streaming 程式碼區塊。程式碼以 CDATA 保留後閱讀，沒有只看摘要。
- [插件對話：2720034](https://dvcaiplatform.atlassian.net/wiki/spaces/DW/pages/2720034)：插件用途、選擇、安裝、上架和自動選擇說明。
- [DSE：2719790](https://dvcaiplatform.atlassian.net/wiki/spaces/DW/pages/2719790)：知識庫與臨時文件差異、命名、描述、文件限制、安裝與更新。
- [官方資源入口](https://dvcbot.net/docs)：對話、助理、插件、文件及知識庫的產品區分。
- 本機對照：`AGENTS.md`、`README.md`、`COMPANY-HANDOFF.md`、`docs/ASSISTANT-INTEGRATION.md`、`docs/COMPANY-IMPLEMENTATION.md`、`docs/ADAPTER-TEST-KIT.md`、`docs/DEVELOPMENT.md`、`docs/PROJECT.md`、`docs/VALIDATION.md`。

舊站 Task Management 223084553 的完整內容目前無法重新取得（匿名 REST 404，新站同名查詢無結果）；不宣稱本輪已讀完該頁，也不依它接遠端任務或推論循環排程。這不阻塞本次本機待辦；目前相關 API／插件／DSE 已讀完。

## 要求 → 本次證據

| 要求／辨識 | 實作與驗證 |
|---|---|
| 自行部署使用公司網址；ID放 runs 的 assistant_id | 沿用 Profiles／AssistantsGateway；未改目的地、不讀 key；`test_assistants_gateway`、`test_assistants_profiles` 完整回歸通過 |
| thread → message → run；pluginapi 的 tid／aid／pid與同run的 tool_call_id 配對 | 沿用 Gateway／search_tools；未知工具和参数拒絕，批次收據防重；完整回歸及 WebView 核准搜尋合成往返通過 |
| API認證與共享不等於 AD／工具授權 | 不變更帳號／能力／verified；普通聊天搜尋仍需獨立核准；公司 AD／權限仍 not_tested |
| 插件可能執行程式或生圖，不能全部當唯讀搜尋 | 本次待辦僅讀本機狀態並導回原流程，沒有新工具或自動派發；UI導航及人工完成檢查零新增 task |
| DSE是文件知識庫，與Internet Search用途不同 | 沒有把DSE當市場新聞，也未新增文件上傳或遠端任務；來源核對仍由人完成 |
| 中斷不代表未送出／遠端取消 | 回原對話只讀原request；沿用inspect/recover及有證據的retry_unsent；未知結果拒絕重送、取消晚到隔離測試通過 |
| 本機待辦完成由人確認 | todos獨立保存；切狀態不改AI工作成功、不建立排程；新回歸與真WebView2合成操作通過 |
| 公司測試不可用mock冒充 | `test-company.bat` 明示local與synthetic；報告 company_real=not_tested；live保持獨立且本次未執行 |

## 衝突與補正

官方示範仍包含停用TLS驗證、短timeout、截斷工具回覆、第一筆訊息及每次刪thread。本機依使用者範圍及AGENTS保留TLS驗證、可設定期限、超限拒絕、按run取回與thread隔離；範例不是正式安全要求，沒有照抄。新版API Gradio已使用60秒，但Python例子仍有2秒；不以任一範例硬套公司工作期限。

新版DSE頁與舊SE頁的上傳限制不同（例如ZIP與CSV上限）；本次没有DSE上傳功能，不能把桌面TXT／CSV限制冒稱DSE規格。舊文件連結補上目前官方頁與本次核對紀錄。CUSTOMIZED_PARAMS示範亦有差異；本次不使用客製參數，不猜映射。

離線驗證第一次從本機舊20套件wheelhouse拿到錯誤lock指紋，安裝正確停止。改用現有正式v0.20.0 ZIP內根wheelhouse的69套件，完整雜湊、lock、乾淨安裝與563項回歸通過。現有使用者環境和舊wheelhouse不覆寫；公司應使用本次可攜包的正式wheelhouse。

真實公司Assistant API／搜尋來源與副作用／AD／Oracle／多ID權限仍 not_tested。文件核對和合成測試不代表正式服務驗收。

登入版補充：DVC助理／API key認證不取代AD與人事App使用资格；demo_login.py僅臨時合成fixture，company模式未接線就拒絕，無失敗回退。正式UI先AD／資格，後DVC；見LOGIN-AND-APP-ACCESS.md。

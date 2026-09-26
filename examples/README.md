# 契約與設定範例

本目錄只含合成／停用範例，不含公司端點、密碼或正式簽章。JSON 是自有產品格式，不是達哥 API。

| 檔案 | 用法 |
|---|---|
| [app.example.json](app.example.json) | Mock 預設、限制、既有登入引用與停用真實連線 |
| [guided-query.example.json](guided-query.example.json) | 合成引導請求、snapshot、精度／公式防護 TSV 期望值與未送出的 issue 草稿 |
| [query-catalog.example.json](query-catalog.example.json) | 三項待公司填寫的 query slots，全部 disabled；SQL 是 null |
| [assistant-decision.schema.json](assistant-decision.schema.json) | 助理輸出的外層契約；query 參數仍需對照已授權模板驗證 |
| [question-form.schema.json](question-form.schema.json) | 後端產生的題目 DTO，另需跨欄位、owner、期限與修訂檢查 |
| [plan-and-choices.example.json](plan-and-choices.example.json) | 未批准的合成計畫與排程選項；選是只取得 disabled 草稿 |
| [schedule.example.json](schedule.example.json) | 草稿與相對日期綁定，不能直接啟用未核准 query |
| [issue.example.json](issue.example.json) | 明確無附加對話／數據的回報樣例 |
| [release-manifest.example.json](release-manifest.example.json) | 未簽章、example_only 的 release 範例，正式 updater 必須拒絕 |

Query slots 的參數只是填表格式示範；公司端必須把主表、欄位語意、join、單位與三項人工標準答案補齊。不要把任意公司表都授權給它，也不要用假 SQL 使範例變 enabled。

建議填入清單：問題名稱、同仁常見問法、輸入條件、輸出欄位／型態、查詢時間口徑、單位範圍、資料 owner、核准 View、SQL 模板、參數 schema、timeout/上限及至少三組驗證案例。

plan_draft 是第七種 AssistantDecision，僅為未信任候選；可完全不用模型 JSON，以固定表單建立計畫。執行組合、step/source 對應、參數、權限與批准皆由後端再驗。QuestionForm 的 JSON Schema 不取代服務端跨欄位規則。

v2.2 query catalog 的 display 是待公司確認的展示資料，不使查詢變 enabled。guided-query 範例的輸出欄位只供合成 fixture；正式 output_columns 仍由公司補齊，不將假欄位當真實 schema。日期示例固定基準日供 fake clock 使用。

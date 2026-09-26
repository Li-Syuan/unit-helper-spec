# Plan 與選項確認（v2.1）

snapshot 的執行步驟只接受下列固定組合；「最多 3 步」是上限，不授權任意三步串接。

本文件定義 UH-11「先規劃」與 UH-12「選項確認」。這是桌面及既有後端新增的工作流程，不依賴達哥原生 Plan、Goal、function calling 或結構化輸出。首版不做持續自主 Goal、任意工具迴圈或多 agent。

## 1. 使用者流程與範圍

對話輸入區新增「一般／先規劃」切換，預設一般，送出時把模式保存到該次 request；切換只影響下一次需求，不把現有計畫視為已同意。

- **一般**：沿用目前流程；條件完整即可執行已授權唯讀查詢。不為每個查詢加一次多餘確認。
- **先規劃**：先整理目標、待補條件、使用的查詢／文字來源、步驟及預期產物；使用者確認整份計畫才執行。使用者可修改、取消或稍後回來。
- **選項確認**：兩種模式共用。用是／否、單選、多選及必要的文字欄位收集条件；按「提交」才生效。選定或預選不等於已送出。

範例：輸入「查昨天的資料並整理重點」→ 詢問資料類別 → 使用者選項提交 → 顯示「指定模板與日期→取得表格→整理重點」→ 確認執行 → 顯示結果。成功後可問「要設成每天查詢嗎？」；選「是」只打開排程草稿，仍須補齊時間、通知條件及未來三次預覽，再按排程的「確認啟用」。選「否」保留已有結果，不建立或啟用排程。

首版計畫最多 3 個順序步驟，只允許以下組合：

| 組合 | 執行內容 | 產物 |
|---|---|---|
| query | 一個已核准、版本固定的查詢 | 同一份表格 snapshot |
| query → summarize | 查詢後整理該 snapshot | 表格＋摘要；摘要失敗仍保留表格 |
| summarize | 對已選文字／單一 TXT/CSV 整理 | 可核對的摘要 |
| rewrite | 對已選文字／TXT 改寫 | 保留原文的候選內容 |

不支援的組合顯示原因並讓使用者調整；不自行拆成無上限任務。匯出、複製、另存、排程啟用、issue 送出、軟體更新沿用各自現有操作，不是計畫自動步驟。核准查詢可用固定日期或在确认時解析的「昨天」等語意；確認畫面必須顯示解析後的絕對日期，跨日重新預覽才能確認。

## 2. 桌面畫面

計畫卡顯示：目標、狀態、修訂編號、資料來源及範圍、缺少條件、步驟、預期產物、有效期限。按鈕為「修改計畫」「取消計畫」「確認執行」。條件缺漏、來源過期或後端判定不可用時，確認按鈕停用並顯示理由。

題目卡顯示完整問題與選項文字，yes_no 用兩個 RadioButton，single_choice 用 RadioButton，multi_choice 用 Checkbutton；boolean 選項穩定 ID 為 yes/no，提交值由 server 映射為 true/false。前端不能以顯示文字當命令。Tab／方向鍵可操作，必填與錯誤提示不能只靠顏色。

每張表單最多 3 題，每題 2～6 個選項；單選／是非題必須剛好一項，多選依 min/max 明確限制。可提供「補充說明」文字欄位（最多 2,000 字），但文字不取代必填選項或正式確認。一般條件可推薦／預選；執行、啟用等正式確認不能預選同意、不能倒數自動送出。Enter 在文字輸入時不觸發正式確認。

提交中鎖按鈕；網路錯誤保留答案和 request ID，重新讀取後端狀態再重送。多視窗、舊題目、已取消、已過期的卡片显示「已失效，請重新整理」。重新開啟桌面可讀回自己的計畫與待答題，後端才是權威。

## 3. 後端強制界線

Plan 允許保存自己的草稿／問答／稽核、讀取已授權模板說明及已明確提供的資料，並呼叫**已驗證無工具副作用的文字規劃介面**。確認前不執行 Oracle 業務查詢、不派發 legacy 搜尋／排程、不啟用排程、不發信、不覆寫檔案。此限制由服務端 action allowlist／dispatch gate 強制執行，不能只在 prompt 寫「請勿執行」。

如果公司助理可能自行查資料、排程或寫入，且無法證實能停用這些原生工具，Plan 不呼叫該介面。改用固定查詢精靈和程式產生的計畫，畫面標示「表單規劃」；一般模式也不得繞過既有授權界線。

模型只提出文字及結構候選。後端產生 ID、版本、expires_at、按鈕用途及核准範圍，驗證模板、參數與來源擁有者。不接受模型提供的 approved=true、權限、URL、SQL、命令、任意工具名稱或可執行 UI。計畫摘要必須由已驗證的步驟／參數產生或核對，不能顯示 A 卻執行 B。

公司 API 只回文字時，固定表單收集模板參數、程式組合上述固定流程；原生無 JSON 也能用。選擇啟用模型候選時，以新增的 plan_draft schema 驗證，失敗最多修正一次，再回固定表單，不能猜工具指令或無限重試。既有每次需求最多 6 次助理呼叫上限包含規劃、修正及執行解讀；用完後表單仍可填，摘要標示未完成。

## 4. 狀態、版本與確認

PlanState：draft → ready → executing → succeeded / failed / cancelled；draft/ready 也可 cancelled/expired。缺條件為 draft 並關聯 waiting_input task；ready 代表資料完整且可預覽。草稿／ready 計畫有效期預設自建立起 24 小時，若來源更早過期則取較早時間。等待使用者不持有 worker lease、DB transaction 或連線；沒有回覆不等於同意。

plan_revision 是執行內容的修訂；row_version 是每次狀態變更的樂觀鎖。修改來源、參數、目標或步驟會增加修訂、使舊確認失效，重新驗證後才回 ready；executing 不可原地修改。使用者按確認時送 plan_revision、expected_version、preview_hash、client_request_id。hash 是後端對 canonical 執行快照（模板版本、參數、來源 ID/hash、步驟、到期時間）的 SHA-256，不是授權憑證。

後端在同一短交易內驗證 owner／名單／期限／ready／版本與 hash，重新驗證模板授權及來源可用性，記 approved_by/at/revision/hash、建立唯一 execution_task_id 並將計畫改 executing。模板被停用、来源改變或日期已跨日時拒絕，要求新預覽，不靜默換模板／參數。立即查詢端點不能接受 plan_id 來繞過這個 gate。

雙擊或兩個視窗同時確認只能建立一個執行 task：唯一(plan_id, plan_revision)，相同 request key 回原資源；不同 key 再確認同一份則回既有 task 或 409，不建立第二份。queued 任務真正派發前仍驗權；worker 使用既有 lease/fencing。唯讀查詢可依原重試規則重試，但不承諾資料庫永遠只讀一次；只採用一份完成結果，不重複建立排程。

執行使用現有 task 流程，首版不建通用 DAG 引擎。execution deadline 預設確認後 5 分鐘，各工具仍用既有較短 timeout。表格已成功而摘要失敗時 task／plan 為 succeeded，result 標 summary_status=failed 並提示「表格已完成，摘要未完成」；不能聲稱全部完成。查詢本身失敗則 failed。取消禁止後續步驟與晚到結果改狀態，已完成結果保留；遠端 API 未支援 cancel 時明確顯示可能仍在處理。重新執行需建立新草稿並確認，不恢復舊批准。

## 5. 選項與輸入契約

自有 QuestionForm：id、task_id、plan_id?、plan_revision?、form_version、purpose(collect_parameters/offer_schedule)、state(open/submitted/expired/cancelled)、expires_at、questions[]。server 綁定 owner，client 不可指定。每題 id、type(yes_no/single_choice/multi_choice)、prompt、required、options[{id,label}]、min_selections、max_selections、allow_note。必填題至少選一項；yes_no 的 ID 必須剛好 yes/no；ID 不重複。選項對應的 typed value 由後端保存，不信任 client 自填值。

InputSubmission：form_id、form_version、plan_revision?、expected_version（GET task 的 version，即 task row_version）、answers[{question_id,selected_option_ids,note?}]、client_request_id。拒絕未知題目／選項、重複題目／選項、數量違規、過期、跨 owner 及舊版本；重送同一 key 同一內容回原結果，成功後表單標為 submitted（已消耗），不重複套用。答案入庫、task 恢復及 plan 修訂更新在同一交易。答案只可補參數／開草稿，不可被解讀成任意動作授權。

計畫「確認執行」使用獨立確認端點，不用 QuestionForm 中一句「是」或聊天文字猜測批准。一般模式補完條件可依原唯讀請求繼續；Plan 補完條件只轉 ready，等待正式確認。offer_schedule 綁定已成功且有權的 query task；yes 建立或回傳該表單唯一的 disabled 排程草稿並導向設定，no 關閉提問。不複製尚未執行的計畫來啟用排程。

純文字條件輸入仍可用原 missing_fields typed values；與 form 回覆是互斥的 input payload，兩者都需 expected_version 及 client_request_id。後端不把未匹配到欄位的自由文字直接當有效條件。

## 6. 自有 API 補充

路徑沿用 /unit-helper/v1，所有資源須逐筆驗 owner。既有 POST 的去重規則也適用於此。

| Method／path | 契約 |
|---|---|
| POST /conversations/{id}/requests | 保留 mode(auto/rewrite/summarize/query) 作工作種類，新增 interaction_mode(normal/plan)，缺省 normal；202 task_id，Plan 規劃 task 建立或連結 plan_id |
| GET /tasks/{id} | 原欄位外新增 plan_id?、question_form?；規劃 task 完成後回 plan_id，不表示計畫已執行 |
| POST /tasks/{id}/input | typed values 或 InputSubmission 二擇一；補條件回 202 task_id；offer_schedule 回 200 form_id、result_ref（草稿 ID 或 null），重送回同一結果 |
| GET /plans?conversation_id=…；GET /plans/{id} | 私有分頁清單／計畫快照、revision、row_version、preview_hash、有效期、approval 與 execution_task_id |
| PATCH /plans/{id} | goal/source_refs/parameters/允許步驟的修改候選＋expected_version；只限 draft/ready，回新修訂；原規劃 task 若已終結則建立新 task，用量累計仍屬同一需求 |
| POST /plans/{id}/confirm | plan_revision、expected_version、preview_hash、client_request_id；202 execution_task_id；409 stale/conflict、410 expired、403 forbidden、422 invalid |
| POST /plans/{id}/cancel | expected_version、client_request_id；draft/ready 取消，executing 轉交 task cancel 並協調狀態，終結狀態不被重寫 |
| POST /tasks/{id}/schedule-offer | 成功 query 的「設成排程」可取得後端固定 yes_no 表單，回 form_id；提供這個快捷問題而不啟用排程 |

執行 task cancel 和 plan cancel 共用一個服務，不能讓兩邊終結狀態不同。QuestionForm 用既有 task input 端點回答，offer_schedule 可掛於 succeeded query task，但回答只更新 form／建立 disabled 草稿，不把已終結 query task 改回 running。

## 7. 資料與維護

沿用 Oracle schema 新增 UH_PLANS、UH_QUESTION_FORMS，欄位見 database/ORACLE.md。計畫與問答跟對話保存 90 天、原檔仍最多暫存 24 小時；計畫 ready 不延長附件保留。來源已刪／過期必須重新提供，不在確認後找不到來源才假裝成功。新增欄位與資料表採相容 migration；舊 client 未送 interaction_mode 預設 normal。

桌面關閉不取消已確認的後端工作；等待回答則保持待答直到到期。預設不每隔幾秒催覆或自動批准；到期由讀取／確認及後端清理共同判斷。Plan 與選項狀態記錄可供問題追查，原文、選項答案及來源副本仍需使用者選取後才附到 issue。

正式開放前使用 AT-16～AT-21 驗證。這一版只增加「先想清楚再執行」與方便回答的介面，不承諾自主追逐目標直到成功。

## 8. v2.2 引導入口相容

常用工作入口依 [GUIDED-QUERIES.md](GUIDED-QUERIES.md) 產生固定表單。已選 query_ref/parameters 的 Plan 可以由程式建立計畫，不需模型猜測。一般模式在表單摘要旁按查詢即執行；Plan 按產生計畫只取得計畫卡，仍需原 confirm gate。複製結果及快速回報不是計畫自動步驟，不能藉此自動提交 issue。

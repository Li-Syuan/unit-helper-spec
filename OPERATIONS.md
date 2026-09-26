# 排程、通知與問題回報

## 1. 從成功查詢建立排程

只讓已成功、未撤銷且使用者仍有權的 query task 出現「設成排程」。複製 query_id/version、參數與欄位定義，不複製一段待 agent 再解釋的自然語言作 executable。

草稿必填：名稱、固定模板版本、參數綁定、頻率、時區、通知條件。預覽顯示未來三次時間、日期條件將如何變動及執行位置；確認才 enabled。首版 daily/weekly，Asia/Taipei 為預設；選定時間由後端轉 UTC 保存，不依桌面時鐘。

參數分 `literal` 和 `relative_date`。日期支援 today、previous_day、last_n_days(1..90)，以該次 scheduled_for 對應的當地日期計算 `[start_inclusive,end_exclusive)`；不得用 retry 當下時間改變同一 occurrence 的範圍。草稿要顯示「每天查昨天」與「每天重查同一日期」的差別。非日期參數預設固定。

rule/params/notify 修改需 expected_version，保存新版本，已執行紀錄不變；停用不取消正在跑的 task，可另選取消。run-now 是有獨立去重 key 的手動工作，不消耗下次固定 occurrence。

## 2. 可靠性與舊排程切換

一個中央 worker 每 30 秒掃描到期排程，使用 DB 交易 claim。`(schedule_id,scheduled_for_utc)` 唯一，建立 occurrence、對應 task 與更新 next_fire 在同一交易內。worker lease 60 秒、每 20 秒續租；失去 lease 的 worker 不可提交結果，寫入必須檢查 lease token。

預設 overlap=skip：上次還沒結束則新 occurrence 記 skipped_overlap。停機漏跑採 24 小時內 coalesce_latest：只補最新一次，較早的記 missed；24 小時以前不補跑。空結果屬成功，不當錯誤。公司改時區時遇 DST 不存在時間跳過、重複時間取第一個 occurrence，需測時間轉換。

query 純讀失敗最多 2 次重試（總共 3 attempts），每次遵守原 deadline；重新讀到新 snapshot 可接受，只有持有 lease 的最終成功結果被採用。查詢成功之後的助理解讀失敗不讓 Oracle 查詢重跑；保留表格與「說明未完成」。助理若可能帶原生副作用，timeout 不自動重送，保留待查核 request ID。

同一 occurrence 最多產一個 task；retries 是同 task 的 attempt。通知與 result commit 同交易，唯一 notification_key（task:<task_id>:<kind>）防止 worker 重啟重複提醒；issue 通知使用 issue:<event_id>:<recipient_subject>，避免 NULL task 欄位造成去重歧義。不宣稱對所有外部操作 exactly-once。

舊排程每筆盤點來源、下次時間、時區、是否有副作用。中央匯入先 disabled → 停用舊 runner 的那筆工作 → 保存最後 occurrence watermark／migration map → 啟用中央版本。新舊 runner 不得同時執行同一工作。沒有映射的舊排程先留舊系統運作並標記管理位置，不自動全刪。

本機桌面關閉不影響中央排程；若中央服務尚未上線，畫面必須說明舊本機排程仍依賴原 runner，不能宣稱已背景常駐。

## 3. 通知規則

第一版提供兩種結果規則：

- `nonempty_on_change`（預設）：本次非空且結果 hash 與上次成功不同才通知；第一次成功非空也通知。模板需固定排序與 result key；忽略 fetched_at 等執行 metadata，避免每天無意義提醒。
- `threshold_crossing`：在管理者允許的單值數值指標上設定比較符號與 threshold；由 false/unknown 轉 true 才通知，持續 true 不重複。不可在截斷的明細上計算全量門檻。

查詢最終失敗每 occurrence 產一筆通知，重試中的失敗只記進度。首次成功空結果不提醒，歷史保留成功／0 列。首版不加 Email／Teams；桌面登入時補抓未讀通知，開啟期間每 60 秒查新通知（另提供重新整理），點擊回到可授權的 task。

每次執行前檢查 owner 在職、單位及名單、模板與資料權限。撤權時停用排程，不用管理員身分代跑；站內只回無敏感資料的停用原因。AD 密碼不存於排程。

## 4. 同仁回報

入口 A：回答／查詢結果旁「這個結果有問題」；入口 B：固定「回報問題／提建議」。表單：type(answer/query/app/schedule/update/feature)、title、description、expected_result；title ≤ 120 字、description ≤ 5,000 字。提交後有穩定 issue 編號，網路中斷可用同一 request ID 重送，不建重複 issue。

自動帶入 app_version、功能、時間、error_code、trace_id；不自動附上 SQL、密碼、檔案、對話原文或完整數據。附上內容必須先預覽，由使用者勾選具體訊息／結果／附件，server 驗證其 owner，再保存 issue 專用 snapshot。未附的原對話不得因 maintainer 點擊 trace_id 而變可讀。預設 issue 內容包括本人說明，無跨人公開。

離線回報保留本機草稿，顯示「尚未送出」；重新連線由使用者重送。首版不做不可見的背景資料上傳。

## 5. Issue 管理

在既有全端平台加一張列表與详情頁，無須導入外部 issue 平台。欄位含分類、priority(P1/P2/P3)、狀態、reporter、建立時間、app_version、assigned_to（預設維護者）、target_version、resolution、duplicate_of。

狀態：new 待確認 → planned 預計處理 → in_progress 處理中 → verifying 待驗證 → resolved 已完成；new/planned 可 not_planned 不採納且必填原因。resolved 可由本人要求重開、maintainer 確認後回 new。合併重複標 duplicate 並指向主 issue，不刪原回報。

使用者能看自己的 issue 的狀態與回覆；主 issue 屬別人時僅顯示「已併入相同問題」及處理狀態，不暴露其描述。maintainer 可看 issue 附件與管理紀錄，不等於有權看來源所有內容。狀態變更皆有 event、操作者與時間，樂觀鎖避免互相覆蓋。

resolved 必填解法；若需要軟體修正，填入已發布 release_id，否則用 `configuration / data / explanation` resolution_type。發布版本列修正 issue IDs，對不同收件人只產其可看的通知。工作台更新不是自動修改程式；issue 是你的開發待辦。

## 6. 後端資源上限

初始同時最多 2 個 Oracle query、2 個助理呼叫（每 user 各最多 1 個），其餘排隊，limits 可由管理者設定。所有 task 有 deadline；長時間 idle connection 不占用 DB query pool。執行帳號、企業 proxy／CA 與 existing platform 配額在公司核對，不擅自安裝額外 scheduler／消息平台。

## 7. Plan 與排程的銜接

計畫本身不會定時執行，也不能以尚未執行的計畫建立已啟用排程。僅成功 query task 可透過固定 yes/no 題打開 disabled 排程草稿；原有未來三次時間、日期綁定與通知條件預覽仍必須完成。選「是」不等於啟用，詳見 [PLAN-AND-CHOICES.md](PLAN-AND-CHOICES.md)。計畫／題目也能回報問題，但 issue 附加仍須使用者明確選取。

## 8. v2.2 快速回報

結果旁「沒有解決我的問題」只開原 issue 表單，預填 type、版本、功能及 trace ID；使用者補描述並提交才建立 issue。對話／結果／附件仍預設不勾選，不因入口位置自動帶入。首版不另外記錄滿意度或建立評分儀表板。

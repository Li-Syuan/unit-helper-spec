# 給接手 Agent：把 QA agent 接到現場服務

將下方指令貼給 GPT 6 sol／SOL 6.1，並讓它讀取本檔。版本為 **1.0.0rc1 候選版**；不要把本機合成測試通過寫成真實服務已驗收。

> 請先讀 AGENTS.md、TO-AGENT.md、docs/VALIDATION.md 及 COMPANY-HANDOFF.md，檢查目前分支和未提交修改。保留現場既有接線及設定，不重寫整套 UI 或 agent 引擎。先驗環境，再使用我提供的 endpoint、Assistant ID 和 API key 接通一位達哥助理，完成兩輪啟用、十輪續談及單助理 Skill／Plan／搜尋日報旅程。金鑰只從本機遮蔽設定取得，不要要求我貼進對話或文件。遇到問題先依錯誤編號定位，做最小修正，完成受影響測試。不要循環重裝套件、猜 API 格式、改用示範答案或重送結果未知的請求。實測前說明會呼叫哪個助理及可能耗用的請求；缺少資訊時集中提出具體問題。交付時分列已完成、未驗證、修改檔案和可重現結果。SMTP 為下一階段，依本檔規格實作前先取得必要資訊；本版沒有寄信命令，不要直接寄信。

## 先取得的資訊（不要把秘密填進本檔）

- **聊天**：正式 HTTPS endpoint、一位有效 Assistant ID、該使用者的 API key。API key 在 App 遮蔽輸入並存 Windows 認證管理員。
- **契約**：目前已成功的 Threads／Messages／Runs 呼叫範例；若有差異，提供去識別的欄位結構、狀態碼及安全錯誤代碼。Assistant ID 不是 `model` 部署名稱。
- **搜尋**：人工核對的唯讀 function 名稱、參數 schema、用途，以及有權使用的助理。工具宣告不是驗收，也不是任意工具授權。
- **登入（若啟用）**：可信的 `authenticate(employee_id, password)` 實作、穩定 subject、允許名單與到期規則；不可只回傳 `True`。
- **TLS**：先使用系統信任，不要求使用者另填 CA。僅在真實憑證錯誤時請部署者確認根憑證；不可使用 `verify=False`。

## 1. 環境只處理一次

保留現場修改及資料。Code ZIP 需完整解壓；正式 69 個 wheels 由 `offline-app/bundle-manifest.json` 固定來源與 SHA256，部分重用 lab 目錄。不要單獨複製 lab lock，也不要從網路補件。

已有 `.venv` 先診斷；符合 lock 就不重裝：

```bat
.venv\Scripts\python.exe scripts\doctor.py
```

沒有環境才在新目錄使用核准的 **Windows x64 Python 3.10.4 完整版**（包含 Tk；下面路徑需換成現場路徑）：

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
```

安裝不覆寫既有環境、不連外補件。WebView2／.NET 是 Windows 元件，不含在 wheels 內。操作細節見[開發指南](docs/DEVELOPMENT.md)及[離線來源](offline-app/README.md)。不要在使用中的環境直接升降套件。

## 2. 依序接通，不一次更動所有功能

| 階段 | 修改或操作入口 | 完成條件 |
|---|---|---|
| 三欄設定 | `activation.py`、`profiles.py`；UI「設定助理」 | endpoint／ID／key 保存，keyring 失敗不降成明文；端點變更需確認並撤銷舊綁定 |
| 一般聊天 | `assistants_gateway.py`、`dialogue_provider.py`、`dialogue_service.py` | 明確同意兩輪合成測試，同 thread 第二輪能辨識第一輪標記；metadata 失敗不直接判聊天失效 |
| 穩定續談 | 主側欄最近對話；`continuity.py` | 兩段對話各十輪、中間切換與關閉重開，內容不串線；草稿、標題、資料夾可恢復 |
| 中斷處理 | `assistant_errors.py`、請求帳本、原對話「檢查／取回」 | 已知 run 讀回；未知 POST 不重送；取消晚到不變成功，原文仍在 |
| 記憶 | 「我的記憶」、`continuity.py` | 預覽確認保存、同助理隔離、新對話固定快照；停用不再選入，舊快照不宣稱已撤回 |
| 單助理 Skill | `skills.py`、`profiles.py`、「測試 Skill 相容性」 | 規劃／整理格式實測；不因填 ID 或收到任意文字就把能力標為通過 |
| 核准搜尋 | `search_tools.py`、`assistants_gateway.py` | 僅允許核准 function；規劃階段無工具；確認後實際完成工具往返並核對來源 |
| 每日工作 | 既有 `workflows.py`、`graph_runner.py`、排程服務 | Skill → 補問 → 修改 Plan → 確認試跑 → 人工核對 → 另同意每天08:00；立即試跑、暫停、重開防重 |
| AD（選用） | `company_auth.py`、`authentication.py` | 允許／拒絕／停用／到期實測；密碼不留存、不同 subject 資料隔離 |

保持 App 開啟或留在系統匣才有排程。CLI 不啟動排程器，CLI 和桌面不能同時開同一資料目錄。日常工作不必設四位角色；多助理留作後續能力驗收。

資料庫：主 Store schema8、DialogueStore schema4。既有對話庫1／2／3先 SQLite backup，再交易升級；勿直接降低版本或搬移組織舊資料庫。對話資料夾只改本機分類，不改遠端 thread／助理／記憶快照。

## 3. 測試與問題回報

修改連線或續談後先跑相關範圍：

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_continuity tests.test_dialogue_recovery tests.test_assistants_gateway
```

先核對模組存在；其他修改依 `tests/suites.json` 選受影響案例。日常使用 quick；交付或核心整合只跑以下一次，不先 full 再重複 verify：

```bat
.venv\Scripts\python.exe scripts\verify.py development
```

真實服務測試必須另外明確啟動。UI 兩輪與 Skill 檢查會耗用 API；`scripts/check-assistants.py` 預設零請求，`--help` 可查 `--live`、現有設定路徑及本機 profile ID 用法。十輪腳本通過仍須人工驗證對話內容與搜尋來源，不能只看 HTTP 成功。

回報提供版本、操作順序、預期／實際結果、問題編號及 App 匯出的安全支援 ZIP。不要附 key、內網網址、原始 HTTP body、整個 SQLite 或未審查的終端紀錄。保存首次失敗證據，修正後再列結果；不把 skip、demo 或 metadata 成功當成驗收。

## 4. 下一階段：核准 SMTP 自動寄信（尚未實作）

使用者已選 **核准 SMTP 郵件伺服器**。不需要另請組織製作 CLI；可在現有共用服務上增加 SMTP adapter，再讓桌面及 CLI 共用。Python3.10 的 [`smtplib`](https://docs.python.org/3.10/library/smtplib.html) 與 [`EmailMessage`](https://docs.python.org/3.10/library/email.message.html) 已提供傳送及信件組裝能力，通常不需新增套件。若現場只接受 OAuth，仍需確認取得／更新 token 的核准方式，不能假設密碼登入一定可用。

### 實作前需由管理者提供

- 主機、port、TLS 方式（STARTTLS 或直接 TLS），是否需要登入或使用核准 IP relay。
- 認證方式、可用寄件者／代理寄件規則；密碼或 token 只放 keyring／核准秘密來源。
- 允許的收件者／網域、信件大小與寄送頻率限制、測試收件人。
- 哪個已完成的工作成果可以寄出、寄送時間與使用者可授權的範圍。第一版無附件、不自動抄送或擴張收件名單。

### 建議 CLI 契約（以下名稱是待開發規格，現在不能執行）

| 擬新增操作 | 行為 |
|---|---|
| `mail status` | 只檢查設定是否完整，不讀出金鑰，不連線 |
| `mail check --live` | 明確啟動連線／TLS／認證檢查，不寄信 |
| `mail draft` → `mail preview` | 從指定成果建立可編輯草稿，顯示寄件者、所有收件者、主旨與完整正文 |
| `mail send` | 只接受當前有效預覽及使用者明確確認；模型文字不能當確認 |
| `mail schedule-preview` → `mail schedule-enable` | 另外授權固定工作、收件範圍及時間的持續寄送，沿用現有排程器 |
| `mail status <attempt>`／`mail pause` | 查看真實傳送狀態或停止後續寄送，不暗中重送 |

新增 `mail_service` 與 `smtp_adapter` 應分層，先定資料契約與遷移，再實作。每次保存固定 request ID、收件者／內容快照及傳送嘗試；狀態區分草稿、傳送中、伺服器已接受、部分拒收、失敗與結果未知。**SMTP 已接受不代表已送達收件匣；Message-ID 也不是防重保證。** 傳出 DATA 後斷線可能已寄出，須保留未知狀態供人工／郵件管理員查核，不自動 retry。部分收件者成功時不得整批再寄。

排程只寄出核准工作的新成果；失敗／未完成不冒充成功寄報告。收件者、端點、認證或內容範圍變更後舊授權失效。使用標準 TLS 驗證，拒絕換行注入信件標頭；不開任意 shell、模型指定 SMTP 主機或任意檔案讀取。

先用本機 SMTP 替身測試預覽零寄送、取消、過期、防重、部分拒收、逾時與未知結果。取得使用者明確同意後，僅向指定測試收件人寄一封合成信並核對收件；再做一次核准的排程試跑。正式實作與這兩項現場驗收前，不在 UI 宣稱已有自動寄信能力。

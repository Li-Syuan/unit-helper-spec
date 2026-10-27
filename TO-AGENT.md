# 給接手 Agent：把 QA agent 接到現場服務

將下方指令貼給 GPT 6 sol／SOL 6.1，並讓它讀取本檔。版本為 **1.0.0rc5 候選版**；不要把本機合成測試通過寫成真實服務已驗收。

若 App 已可運作，這次要改善「交辦 Job 卻被帶向 Skill」及縮短完成工作的操作，直接使用[操作流程精簡工作單](docs/UX-SIMPLIFICATION.md)及其中的 SOL 6.1 指令。以一位助理、零 Skill 完成試跑與另行啟用排程為主旅程。這份 MD 不會自動套用到 App，接手者須修改程式並驗證，不能只更新文件。沿用已成功的接線與環境，不重新執行下方完整安裝、啟用和 API 試跑流程。

本版驗證結果以[驗證紀錄](docs/VALIDATION.md)為準；剪貼簿應依本次實際Windows結果判讀，不能靠重裝69個套件解決。版本仍為候選版。

先讀[工作代理契約](docs/AGENT-WORK.md)。rc4日常直接在對話輸入，Skill選用；側欄只留對話／我的工作。設定三欄保存後，如需搜尋先核准工具，再一次明確啟動最多8次基本檢查（2聊天兼辨識、3工作格式、3自主決策），最後另做單次搜尋測試。各項結果分開，不假裝全部啟用；聊天成功但工作未過時仍可聊天，手動入口在更多工具。

新契約位於`dialogue_routing.py`：嚴格欄位version/kind/text/goal/search；kind=chat/clarify/work。同一次回覆辨識，不額外分類；工作建議不是授權。`workspace_turns.py`以原thread/request固定識別連AgentJobs，已知工作不重建；原始wire與畫面文字分開，舊thread不改契約。若平台只回純文字，先保留聊天，對照去識別失敗樣本修mapping，不放寬JSON或手改證據。

自主模式以達哥JSON建議驅動本機固定工具目錄；當前不需要自訂本機function calling。每輪的角色、目的助理、輸入來源與預算須由程式檢查；規劃與決策停工具。固定12請求／6動作／600秒，未知POST不重送。收據／checkpoint及原request ID是恢復依據，不能為測試方便改成新請求。新格式請依錯誤及合成測試修改最小範圍，不改整套UI／runner／資料庫。

維持Python3.10.4與現有核心；完整Hermes仍有[移植缺口](docs/HERMES-COMPATIBILITY.md)，SMTP未實作。

要擴充 Hermes 類能力時，先讀 [Hermes 開發參考包](doc/hermes/README.md)，選定一項 WORK-ITEMS 後再修改程式。包內有固定版本的離線官方文件、來源與 MIT 授權；它們不是 App Skill 或安裝指令。保留本檔與共用指引的批准及達哥接線規則，不因參考文件提到工具就直接開放。

> 請先讀 AGENTS.md、TO-AGENT.md、docs/VALIDATION.md 及 COMPANY-HANDOFF.md，檢查目前分支和未提交修改。保留現場既有接線及設定，不重寫整套 UI 或 agent 引擎。先驗環境，再使用我提供的 endpoint、Assistant ID 和 API key 接通一位達哥助理，完成八次基本檢查、十輪續談及單助理 Skill／Plan／搜尋日報旅程。金鑰只從本機遮蔽設定取得，不要要求我貼進對話或文件。遇到問題先依錯誤編號定位，做最小修正，完成受影響測試。不要循環重裝套件、猜 API 格式、改用示範答案或重送結果未知的請求。實測前說明會呼叫哪個助理及可能耗用的請求；缺少資訊時集中提出具體問題。交付時分列已完成、未驗證、修改檔案和可重現結果。SMTP 為下一階段，依本檔規格實作前先取得必要資訊；本版沒有寄信命令，不要直接寄信。

## 在 VS Code Copilot 接手

以VS Code開啟專案根目錄，使用公司允許的Copilot帳號、模型與工具。這些檔案是開發指引，不會替App增加Hermes能力，也不保證模型一定完成；請核對實際修改與證據。

- [共用指引](.github/copilot-instructions.md) 保存當前規則，四個既有 [開發角色](.github/agents/coordinator.agent.md) 各自只保留職責，避免重複長指示。日常選 `UnitHelper-Coordinator`；不指定模型，沿用你在Copilot選的模型。Backend／Desktop供已授權的分工，QA唯讀審查。
- 支援prompt files的VS Code Chat可手動使用下表。依目前官方說明，prompt files限Local harness；若版本／管理政策／session不支援，直接附上對應Markdown，要求照內容操作即可，不要修改公司政策或擴大工具權限。
- 先確認Copilot已載入專案指引；可從Chat的Customizations／使用的參考內容檢查。沒有顯示角色時，使用一般Agent模式並明確附上本檔和共用指引。工具名稱與子代理支援依session而異；角色檔沿用Local內建工具別名，若所選Copilot執行環境未提供必要工具，改用已有工具的一般Agent依序處理，不假稱分工已執行。

| 手動入口 | 用途 |
|---|---|
| [/qa-takeover](.github/prompts/qa-takeover.prompt.md) | 先查環境，再依序接通單助理；不自動呼叫真實API |
| [/qa-diagnose](.github/prompts/qa-diagnose.prompt.md) | 帶錯誤編號與去識別步驟，定位並做最小修正 |
| [/qa-hermes-plan](.github/prompts/qa-hermes-plan.prompt.md) | 只規劃一項Hermes類功能，列修改入口、必要資訊及驗收；不安裝／執行 |

### 精簡開發 Skills

另提供三個pstack改編Skills，位於 `.github/skills/`。它們是給Copilot使用的開發方法，不會出現在QA agent的「我的Skills」，也不為App新增工具。預設手動啟動（`disable-model-invocation: true`），沿用目前選定的模型；沒有插件安裝、hooks、模型切換或自動分工。來源提交、改編差異及MIT全文見[第三方說明](docs/THIRD-PARTY-NOTICES.md#pstack-開發-skills)。

| 入口 | 直接可用的交辦範例 |
|---|---|
| [/qa-map](.github/skills/qa-map/SKILL.md) | `/qa-map 請說明對話送出到達哥回覆的程式路徑，列出恢復入口及相關測試；先不要修改或呼叫API。` |
| [/qa-fix](.github/skills/qa-fix/SKILL.md) | `/qa-fix 請依這份修復工作單處理續談失敗。先確認原因並重現，再做最小修正；保留原請求與歷史，只跑受影響測試。` |
| [/qa-review](.github/skills/qa-review/SKILL.md) | `/qa-review 請唯讀審查這次修改與測試證據，優先檢查未知送出、防重及兩位助理隔離；列具體問題，不自動修正。` |

先在VS Code的Customizations／Skills確認這三個名稱可見，再從 `/` 選單明確選用。現有qa-takeover／qa-diagnose prompt分別引用定位及修復方法，QA角色引用同一份審查表；按任務讀取，不把三份同時塞入每次對話。單模型檢查不是獨立多模型審查，也不保證節省固定token數。

不同VS Code版本、harness或管理政策可能影響載入；若找不到Skill，明確附上對應 `SKILL.md` 與共用指引即可，不修改管理政策或安裝完整pstack。prompt files仍依前述Local限制；Skills支援方式以[VS Code官方說明](https://code.visualstudio.com/docs/agent-customization/agent-skills)及現場版本為準。公司Copilot實際載入與修復成效仍 `not_tested`。

第一次可直接貼：「請依 TO-AGENT.md 與 qa-takeover.prompt.md 接手。先完成離線環境盤點，不重建已正常的環境；接著讓我在App設定助理，真實呼叫前說明測試範圍。一次跑通聊天→Plan→搜尋成果，再處理排程。」

GitHub Code ZIP也含 `.github` 與開發Skills；它不要求GitHub Actions或再部署API server。未實測公司VS Code版本／政策的自動載入；上述手動附檔方式是備用入口。

格式依2026-10-25官方文件核對：[共用指引](https://code.visualstudio.com/docs/agent-customization/custom-instructions)、[自訂角色](https://code.visualstudio.com/docs/agent-customization/custom-agents)、[prompt files](https://code.visualstudio.com/docs/agent-customization/prompt-files)。

## 先取得的資訊（不要把秘密填進本檔）

- **聊天**：正式 HTTPS endpoint、一位有效 Assistant ID、該使用者的 API key。API key 在 App 遮蔽輸入並存 Windows 認證管理員。
- **契約**：目前已成功的 Threads／Messages／Runs 呼叫範例；若有差異，提供去識別的欄位結構、狀態碼及安全錯誤代碼。Assistant ID 不是 `model` 部署名稱。
- **搜尋**：人工核對的唯讀 function 名稱、參數 schema、用途，以及有權使用的助理。工具宣告不是驗收，也不是任意工具授權。
- **登入（若啟用）**：可信的 `authenticate(employee_id, password)` 實作、穩定 subject、允許名單與到期規則；不可只回傳 `True`。
- **TLS**：先使用系統信任，不要求使用者另填 CA。僅在真實憑證錯誤時請部署者確認根憑證；不可使用 `verify=False`。

## 1. 環境只處理一次

保留現場修改及資料。Code ZIP 需完整解壓；正式69個wheels全部在 `offline-app/packages`，由 `offline-app/bundle-manifest.json` 固定來源與SHA256。不要使用舊lab lock或從網路補件。

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

資料庫：主 Store schema8、DialogueStore schema5。既有對話庫1／2／3／4先 SQLite backup，再交易升級；勿直接降低版本或搬移組織舊資料庫。對話資料夾只改本機分類，不改遠端 thread／助理／記憶快照。

## 3. 測試與問題回報

rc5 優先收取 App「設定助理 → 連線診斷 → 預覽修復工作單」產生的 Markdown。它列出匿名助理、修訂、檢查時間、安全代碼／階段、錯誤編號、程式位置與最小命令。先核對哪位助理、哪個修訂、哪個項目失敗；工作格式失敗不阻擋已通過的聊天，不需先接 AD 或四角色。

若缺資訊，只問足以定位的去識別操作步驟。不要索取 `connection-diagnostics.json` 原檔、整個使用者目錄或 HTTP body。安全 ZIP 是選用附件。`connection_diagnostics.py` 不授予能力，不能修改摘要解鎖功能；缺細節保留「沒有可用紀錄」。

修改診斷或安全匯出，先跑：

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_connection_diagnostics tests.test_support
```

按實際修改再選相關模組。UI 指定重測須明確同意：聊天／辨識2次、工作3次、自主3次；搜尋一次測試最多4次模型請求（含工具續答）。未知請求仍先沿原 ID 檢查／恢復，不透過新測試或 request ID 繞過。

修改連線或續談後先跑相關範圍：

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_workspace_turns tests.test_continuity tests.test_dialogue_recovery tests.test_assistants_gateway
```

先核對模組存在；其他修改依 `tests/suites.json` 選受影響案例。日常使用 quick；交付或核心整合只跑以下一次，不先 full 再重複 verify：

```bat
.venv\Scripts\python.exe scripts\verify.py development
```

真實服務測試必須另外明確啟動。UI 基本檢查最多8次，搜尋另測，會耗用 API；`scripts/check-assistants.py` 預設零請求，`--help` 可查 `--live`、現有設定路徑及本機 profile ID 用法。十輪腳本通過仍須人工驗證對話內容與搜尋來源，不能只看 HTTP 成功。

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

## 固定資料晨報試跑

多助理屬進階入口，不是單助理啟用前提。先以以下虛構資料驗收既有分析／覆核／彙整角色；助理 Instruction 及故意矛盾案例見[建立指南](docs/assistant-instructions/README.md)。

```text
請規劃一次合成晨報，不搜尋、不排程：
A：台股觀察指標本期100、前期99，只提供兩期。
B：美股觀察指標本期200，沒有前期。
C：政策聲明預計明日公布，目前沒有結果。
分析助理區分已知、未知；覆核同時取得原始A/B/C與分析；
彙整列結論、注意事項及待確認決策。不編造原因、趨勢或來源網址。
先給我計畫，等我確認才執行。
```

預期：確認前零執行；A只能比較這兩期，B不能判斷漲跌，C不能當作已公布。覆核輸入需包含原始資料，不只前一步摘要；矛盾則停止，不為取得成功狀態而放行。全部標示合成資料，真實搜尋另測。

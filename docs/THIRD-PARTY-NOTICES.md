# 0.16.0 新增框架依賴

正式 App 使用 LangGraph、langgraph-checkpoint-sqlite 及其鎖定的 langchain-core、LangSmith client 等間接依賴；安裝不代表啟用 LangSmith 雲端 tracing。版本以 requirements.lock 為準，新增完整授權文字位於 docs/licenses。LangSmith 與 sqlite-vec 的上游授權來源沿用獨立試驗包 licenses/sources.json；原 wheel 不另附授權的項目已保留上游文字。

# 第三方套件授權

QA agent 使用 Python、Tcl/Tk、OpenAI SDK、keyring 與鎖定檔列出的間接依賴。這些元件的著作權與授權分別屬於原權利人；QA agent 不表示受到這些專案的背書。

完整版本以專案 requirements.lock 為準。隨附授權文字存於 docs/licenses；請保留套件附帶的 LICENSE／NOTICE。第三方元件更新時，由維護者同步更新授權清單及文字。

本頁是索引，不重新授權第三方程式。組織再散布或打包時應依隨附原始授權及組織流程確認義務，不以本頁取代授權全文。

## pstack 開發 Skills

`.github/skills/` 的三份開發指引改編自 [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude)，固定提交 **356c6e0f978df729eb16f227d795f34d221c5aad**（2026-10-25核對）。採用部分的著作權為 Copyright (c) 2026 Lauren Tan、Copyright (c) 2026 Michael Denyer，MIT全文隨附於 [pstack-claude.txt](licenses/pstack-claude.txt)。來源鏈見該提交的 [NOTICE-skills](https://github.com/michael-denyer/pstack-claude/blob/356c6e0f978df729eb16f227d795f34d221c5aad/NOTICE-skills.md)；本次沒有採用 cursor-team-kit 或 thermos 的內容。

| 本機改編 | 固定上游檔案 | 採用與調整 |
|---|---|---|
| [qa-map](../.github/skills/qa-map/SKILL.md) | [how/SKILL.md](https://github.com/michael-denyer/pstack-claude/blob/356c6e0f978df729eb16f227d795f34d221c5aad/plugins/pstack/skills/how/SKILL.md) | 保留按問題建立程式地圖；改為單一agent唯讀追蹤QA現有呼叫路徑，不複製explorer／explainer子代理與模型配置。 |
| [qa-fix](../.github/skills/qa-fix/SKILL.md) | [tdd/SKILL.md](https://github.com/michael-denyer/pstack-claude/blob/356c6e0f978df729eb16f227d795f34d221c5aad/plugins/pstack/skills/tdd/SKILL.md) | 保留最小重現、修正前後證據及避免脆弱測試；加入既有安全工作單、請求恢復與選測入口。 |
| [qa-review](../.github/skills/qa-review/SKILL.md) | [interrogate/SKILL.md](https://github.com/michael-denyer/pstack-claude/blob/356c6e0f978df729eb16f227d795f34d221c5aad/plugins/pstack/skills/interrogate/SKILL.md) | 保留按意圖審查、查證疑點、歸納可行問題；改成目前模型的唯讀審查，不複製多模型派發、fallback或自動PR操作。 |

這是繁體中文專案改編，不是完整pstack插件或其官方適配。不複製上游執行腳本、hooks、模型表或其他Skill依賴；三份指引可分別閱讀，只引用本專案共用規則。不新增App執行期依賴或改變產品權限；授權與來源需隨Code ZIP保留。


新版增加 pywebview（BSD）、pythonnet（MIT）、clr-loader（MIT）、cffi（MIT）、pycparser（BSD）、proxy_tools（BSD）、bottle（MIT）、python-dotenv（BSD）、markdown-it-py／mdurl（MIT）、bleach（Apache-2.0）及webencodings（BSD）。完整文字在docs/licenses，確切版本以lock為準。WebView2與.NET Runtime由組織依Microsoft授權提供，不包含於Python離線wheel包。

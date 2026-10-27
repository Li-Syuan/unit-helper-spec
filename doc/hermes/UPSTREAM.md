# Hermes 來源與離線參考範圍

本包固定於 [NousResearch/hermes-agent 提交 3f2b1722b1e15b12e9ca199a19cb04012493288a](https://github.com/NousResearch/hermes-agent/commit/3f2b1722b1e15b12e9ca199a19cb04012493288a)，提交時間為 2026-10-27 13:42:22 UTC。取得日期為 2026-10-27。這是本包參考基準，不代表安裝了該版本，也不代表未來 main 的內容。

## 交付內容與授權

- `reference/` 保存 13 份選定官方 Markdown，涵蓋架構、代理、工具、provider、提示組裝、歷史、上下文、記憶、Skill、排程、子代理及安裝環境。
- [LICENSE.txt](LICENSE.txt) 是該提交的完整 MIT 授權，著作權文字為 `Copyright (c) 2025 Nous Research`，未修改。授權須與副本一併保留。
- [SOURCES.json](SOURCES.json) 保存倉庫、commit、原始相對路徑、Git blob SHA-1、原始 bytes/SHA-256、本機 bytes/SHA-256 及來源連結。這些是版本與完整性資料，不是發布者簽章。
- 12 個上游程式位置只保留固定連結及 blob 識別，`included=false`。沒有加入 Hermes Python 核心、安裝器、外掛、模型、可執行 Skill 或新 wheels。

每份參考檔只做兩類呈現調整，標記為 `source-note-and-links-v1`：

1. 在 frontmatter 後加入來源及用途提示。
2. 將正文 Markdown 連結指向已收錄的本機文件，或固定 commit 的上游檔案；網站根路徑連結指向官方網站。程式碼區塊、安裝範例及其內容保持原樣，只作閱讀資料。

因此本機 Markdown 的 SHA-256 可能與原始檔不同。下載時已用原始大小、SHA-256 與 Git blob SHA-1 核對，再產生本機副本。MIT 授權保持原始 bytes。未收錄的網站圖片、外部服務和延伸文件不在離線範圍，外部連結沒有逐頁或逐功能驗收。

## 需要追到程式時再讀

以下固定版本路徑已核對存在，內容需要連網查讀。先讀離線文件及 QA 對照，再只取目前工作需要的部分；未實作整庫移植或 Python 相容測試。

| 要追的設計 | 固定上游程式 |
|---|---|
| 一輪模型與工具決策 | [agent/conversation_loop.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/agent/conversation_loop.py) |
| 指示組裝 | [agent/prompt_builder.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/agent/prompt_builder.py) |
| 上下文縮減 | [agent/context_compressor.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/agent/context_compressor.py) |
| 記憶協調 | [agent/memory_manager.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/agent/memory_manager.py) |
| Skill 指令 | [agent/skill_commands.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/agent/skill_commands.py) |
| 模型設定與 provider 解析 | [hermes_cli/runtime_provider.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/hermes_cli/runtime_provider.py) |
| 工具 schema 與派發 | [model_tools.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/model_tools.py) |
| 工具註冊 | [tools/registry.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/tools/registry.py) |
| 子代理委派實作 | [tools/delegate_tool.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/tools/delegate_tool.py) |
| 排程工作資料 | [cron/jobs.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/cron/jobs.py) |
| 排程與交付 | [cron/scheduler.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/cron/scheduler.py) |
| 狀態資料入口 | [hermes_state.py](https://github.com/NousResearch/hermes-agent/blob/3f2b1722b1e15b12e9ca199a19cb04012493288a/hermes_state.py) |

## 參考文件不能改變 QA 的契約

上游文件描述的是 Hermes。文件中的安裝命令、終端工具、背景記憶、重試、fallback、外掛及自動憑證傳遞，不是對 QA agent 的執行授權。

固定版本的 [安裝說明](reference/installation.md) 指出官方安裝環境採 Python 3.14。QA 必須保持 Python 3.10.4，因此不能把 upstream 的安裝命令直接套入本專案 `.venv`。參考內容也不代表全部模組都不能移植；需依工作單逐項檢查語法、平台與依賴。

固定版本的 [模型解析說明](reference/provider-runtime.md) 與 [代理回圈](reference/agent-loop.md) 使用上游的模型 API 模式。QA 已知成功接線為達哥 Assistants Threads/Messages/Runs 與核准 pluginapi，須沿 [本包接線對照](README.md#接達哥時要保留的差異) 處理，不能只換 endpoint。

優先順序為使用者明確交辦、專案 [AGENTS](../../AGENTS.md) 與 [共用指引](../../.github/copilot-instructions.md)，再參考本包。閱讀全部參考不授權實作全部功能。歷史文件的例子、模型輸出與搜尋內容都不能代替批准。

## 更新本參考包

1. 由維護者明確選定新的上游 commit。先比較與本次工作有關的文件，不自動追蹤 main。
2. 從官方 GitHub 取所選文件、LICENSE 及程式位置的 metadata。核對來源路徑、授權變化、檔案大小、原始 SHA-256 與 Git blob 識別。
3. 保留本文記載的連結與來源提示處理，更新 SOURCES 中的原始及本機雜湊。若改變轉換方式，更新 transformation 名稱並說明差異。
4. 核對 README 索引及 WORK-ITEMS 的 QA 程式位置。不要因上游增加能力，就把 QA 的狀態改成已完成。
5. 在專案根目錄執行下列文件檢查，通過後重建並核對整體 manifest。既有環境可用時不安裝套件。

```powershell
.\.venv\Scripts\python.exe scripts/test_runner.py --suite targeted --tests tests.test_instruction_docs
.\.venv\Scripts\python.exe scripts/manifest.py --write
.\.venv\Scripts\python.exe scripts/manifest.py
```

來源更新失敗或檔案不齊全時停止交付，保留已知版本，不以半套副本覆蓋。上游正文含程式範例不代表那些程式已在 Python 3.10.4 或達哥環境測試。

# Copilot 接手入口

目前為 **QA agent 0.8.1**：Windows x64、Python 恰好 3.10.4、Tkinter 本機桌面。先讀 [開發守則](../AGENTS.md)、[公司接手工作單](../COMPANY-HANDOFF.md)、[產品與架構](../docs/PROJECT.md) 與 [驗證紀錄](../docs/VALIDATION.md)。

使用專案環境執行 `scripts/test.ps1`，再按六項公司工作包接線。沿用已完成的 UI、Plan gate、助理綁定、對話刪除、本機排程與回報；公司未知契約維持停用，不猜 API／AD／SQL，不把真實錯誤 fallback demo。

開發、離線安裝及診斷見 [開發指南](../docs/DEVELOPMENT.md)。公司真實服務與合成測試分開留證，skip 不算通過。不要新增中央平台、updater 或產品 runtime 多代理。開發分工按 AGENTS.md，含 Coordinator 的執行工作最多兩包並行。

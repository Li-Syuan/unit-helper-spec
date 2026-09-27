# Copilot 接手入口

以根目錄 AGENTS.md、LOCAL-SPEC.md、COMPANY-HANDOFF.md 為當前範圍。這是 Python 3.10.4 / Windows x64 / Tkinter 本機程式 0.3.0，不是要重新建立中央平台。
先執行 scripts/test.ps1，按六項公司接線工作包推進。已完成的 UI、Plan gate、選項、本機排程與回報不重做。
旧 v2.2 的 BACKEND／UPDATES／M0～M4 是後續完整路線，不能宣稱已完成。真實模式失敗不 demo fallback；沒有內部資料就保留 fail-closed adapter，不猜公司 URL、SQL 或 AD。
開發分工至多兩個互斥工作包；產品 runtime 維持單助理。詳見 AGENTS.md。

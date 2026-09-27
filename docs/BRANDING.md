# QA agent 正式品牌 — 0.6.0

使用者選定 A：Q 形對話夥伴，石墨底、米白 Q 與眼點、青藍確認勾。正式 PNG 是候選 A 的原圖複本；1254×1254，透明外角，SHA-256：7eaafa870bb85f4e685c8a7398c09ae0746c898c055e7086e88ceba17032e3e1。

![正式圖示](../desktop_app/assets/qa-agent-256.png)

完整生成提示詞保留於 assets/GENERATION-PROMPT.txt 及 candidates/prompts.json。B～D 與比較圖保留設計歷史，不再等待選定。scripts/export-icon.ps1 輸出16／24／32／48／64／128／256 PNG 與 ICO，不新增圖片 runtime 依賴。

視窗／附屬視窗與側欄沿用 branding.py，Windows AppUserModelID 不變。資源缺失與不同工作目錄測試保留。桌面捷徑仍用固定 qa-agent.ico 路徑，create-shortcut.bat 可更新自己的捷徑，不覆蓋其他程式。

已檢視應用內圖示及小尺寸資源；Windows 工作列／桌面的系統圖示快取呈現仍未人工驗收，不能以 ICO 檔或 COM 屬性測試代替。

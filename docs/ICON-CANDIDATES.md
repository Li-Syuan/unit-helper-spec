# QA agent 候選圖示 — 0.5.0

0.6.0 使用者已選定 A，正式 PNG／ICO 已套用。以下保留當時四款候選的比較與生成歷史。

![深淺背景與原尺寸預覽](images/icon-candidates.png)

| 編號 | 方向 | 原圖 |
|---|---|---|
| A | Q 對話夥伴：眼點與確認勾 | [PNG](../desktop_app/assets/candidates/A.png) |
| B | QA 字母融合：企業工具字標 | [PNG](../desktop_app/assets/candidates/B.png) |
| C | 雙對話框：協作與交接 | [PNG](../desktop_app/assets/candidates/C.png) |
| D | 極簡面罩：專注的 AI Agent | [PNG](../desktop_app/assets/candidates/D.png) |

2026-09-27 使用 Codex 內建 imagegen 分別生成四款；皆為 1254×1254 RGBA PNG，四角透明。完整生成提示詞與 C 的背景修整提示詞保存在 [prompts.json](../desktop_app/assets/candidates/prompts.json)。C 初稿有背景斑點，經同一 imagegen 編輯移除；其餘保留生成原圖。未使用公司金鑰、未採用外部品牌圖示。

scripts/export-icon-candidates.ps1 只用 Windows System.Drawing 縮放及編排比較，不創作／改畫符號，也不增加 runtime 套件。輸出各款 16／32／48／224 px PNG；比較圖上下分別為深／淺背景，小圖按照原像素尺寸顯示。檢視後四款輪廓可辨；16px 的眼點／確認勾細節自然較小，32／48px 更清楚。

A 已輸出正式七尺寸 ICO。B／C／D 保留為候選原圖，沒有套用。

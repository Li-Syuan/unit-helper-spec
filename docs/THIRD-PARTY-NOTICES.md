# 0.16.0 新增框架依賴

正式 App 使用 LangGraph、langgraph-checkpoint-sqlite 及其鎖定的 langchain-core、LangSmith client 等間接依賴；安裝不代表啟用 LangSmith 雲端 tracing。版本以 requirements.lock 為準，新增完整授權文字位於 docs/licenses。LangSmith 與 sqlite-vec 的上游授權來源沿用獨立試驗包 licenses/sources.json；原 wheel 不另附授權的項目已保留上游文字。

# 第三方套件授權

QA agent 使用 Python、Tcl/Tk、OpenAI SDK、keyring 與鎖定檔列出的間接依賴。這些元件的著作權與授權分別屬於原權利人；QA agent 不表示受到這些專案的背書。

完整版本以專案 requirements.lock 為準。隨附授權文字存於 docs/licenses；請保留套件附帶的 LICENSE／NOTICE。第三方元件更新時，由維護者同步更新授權清單及文字。

本頁是索引，不重新授權第三方程式。組織再散布或打包時應依隨附原始授權及組織流程確認義務，不以本頁取代授權全文。


新版增加 pywebview（BSD）、pythonnet（MIT）、clr-loader（MIT）、cffi（MIT）、pycparser（BSD）、proxy_tools（BSD）、bottle（MIT）、python-dotenv（BSD）、markdown-it-py／mdurl（MIT）、bleach（Apache-2.0）及webencodings（BSD）。完整文字在docs/licenses，確切版本以lock為準。WebView2與.NET Runtime由組織依Microsoft授權提供，不包含於Python離線wheel包。

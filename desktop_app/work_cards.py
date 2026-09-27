"""Company-editable text starters. Content only: no tools, routing or execution."""
CARDS = (
    {'id': 'summarize', 'title': '整理重點與待辦', 'description': '把零散文字整理成重點、待辦與待確認事項。',
     'purpose': '整理重點', 'prompt': '請依下列內容分列重點、可執行的待辦及待確認資訊。不要編造負責人、期限或未提供的事實。\n\n原始內容：\n'},
    {'id': 'rewrite', 'title': '改寫信件與說明', 'description': '保留原意，讓信件或說明更清楚。',
     'purpose': '改寫文字', 'prompt': '請保留原意，以{tone}語氣改寫下列文字，不補入未提供的事實。\n\n原始內容：\n'},
    {'id': 'report', 'title': '整理工作報告', 'description': '整理已完成、進行中、問題與需要協助的事項。',
     'purpose': '整理重點', 'prompt': '請將下列工作內容整理為已完成、進行中、問題及需要協助的事項；無法確認的內容請標記待確認，不要自行推斷完成狀態。\n\n原始內容：\n'},
)

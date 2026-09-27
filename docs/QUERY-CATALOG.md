# 動態查詢目錄契約

`QueryGateway.catalog()` 回傳 `list[dict]`。目錄由可信的 adapter 程式定義，不能把模型回答直接當成模板。每個模板有唯一非空 `id`、`name`、`parameters`；可提供 `description`、既有 `columns`，以及選用的 `date_range`。不存在、重複或不支援的模板不執行。

```python
{
    "id": "Q01", "name": "核准查詢", "description": "查詢說明",
    "parameters": {
        "begin": {"label": "起日（含）", "type": "date", "required": True},
        "until": {"label": "迄日（不含）", "type": "date", "required": True},
        "limit": {"label": "筆數", "type": "integer", "default": 100, "min": 1, "max": 1000},
        "amount": {"label": "金額", "type": "decimal", "default": "0.00", "min": "0"},
        "group": {"label": "分類", "type": "single_choice", "options": ["A", "B"], "default": "A"},
        "active": {"label": "啟用", "type": "boolean", "default": False},
        "note": {"label": "備註", "type": "text", "required": False, "max_length": 200}
    },
    "date_range": {"start": "begin", "end": "until"}
}
```

## 參數規則

| type | 服務層值 | 表單 |
|---|---|---|
| `text` | 字串 | 單行文字 |
| `date` | 真實且完整的 YYYY-MM-DD 字串 | 日期文字 |
| `integer` | Python int，拒絕 bool | 輸入後轉為 int |
| `decimal` | 一般十進位字串；不用 float，拒絕 NaN／Infinity／科學記號 | 保留輸入精度與尾零 |
| `single_choice` | `options` 中的字串 | 唯讀下拉 |
| `boolean` | Python bool | 是／否下拉，必填時不預選 |

- `label`、`type` 必填；`required` 預設 `True`，只能是 bool。
- `default` 是原型別值，必須符合該欄位規則；只用於新表單初值。服务層不偷偷補上缺少的參數。
- 選填空值不傳送；必填缺少、空字串或純空白文字會拒絕。已保存的 Plan 修改使用原參數，不重新套用 default。
- `min`／`max` 為含界線的限制，只適用整數、小数與日期，型別與欄位相同。
- `min_length`／`max_length` 是字串長度限制，預設 0／50,000；可用於字串型別，不能用於 integer／boolean。
- 參數名稱不能以 `_` 開頭。未知參數、未知欄位設定、未知型別會拒絕；選項需為非空、不重複的字串清單。
- 表單與服務共用 `desktop_app/query_schema.py`。通用檢查後仍呼叫 adapter 的 `validate()`；跨欄位關係、資料權限、日期期間及查詢上限由 adapter 驗證。`validate()` 必須為純驗證，不能執行查詢。

## 排程與介面

`Engine(..., query_validator=gateway.validate, query_catalog=gateway.catalog)` 供應目錄。使用 bound `gateway.run` 時也會自動找到 `catalog`；公司接線仍應明確注入兩者。舊有直接注入純函式的 Engine 測試介面保留，但不能拿它當公司模式省略目錄與驗證的理由。

- `date_range` 的 start／end 必須指向不同的 date 欄位。前一日模式依台北的排定日，產生起日含、迄日不含的昨天範圍。其他參數保持原值。
- 新設定只在明確宣告日期映射時提供「每次前一日」；服務層也限制。沒有映射仍可使用「固定原參數」。
- 舊版已保存的 DEMO01／DEMO02／DEMO03 前一日排程，允許明確的 from_date／to_date 相容映射；不推測其他查詢欄位。此相容不授權新建未宣告的日期模式。
- 模板或參數失效時，排程不呼叫資料來源；保留失敗紀錄與通知，畫面仍可查看歷史及停用。
- Plan 預覽／修改、查詢條件與排程預覽依同一目錄標籤呈現。歷史結果的模板失效時保留原快照，明示使用已保存的欄位名稱。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_query_schema tests.test_ui tests.test_core -v
```

測試包含非日期模板、改名日期、六種欄位、精度、Plan 批准前不執行、失效模板、舊 DEMO 排程及最小視窗。這些為合成資料及本機 Tk 驗證，不代表公司 Oracle 或 Excel 已驗收。

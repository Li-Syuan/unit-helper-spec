"""Pure catalog validation and parameter conversion, shared by UI and services."""
import re
from datetime import date
from decimal import Decimal

TYPES = {'text', 'date', 'integer', 'decimal', 'single_choice', 'boolean'}
LEGACY_DATE_RANGES = {key: {'start': 'from_date', 'end': 'to_date'} for key in ('DEMO01', 'DEMO02', 'DEMO03')}


def _value(field, value, from_ui=False):
    label, kind = field['label'], field['type']
    if kind in {'text', 'date', 'decimal', 'single_choice'} and not isinstance(value, str):
        raise ValueError(label + ' 必須是文字。')
    if kind == 'date':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError(label + ' 需使用 YYYY-MM-DD。')
        try: date.fromisoformat(value)
        except ValueError: raise ValueError(label + ' 日期不存在。') from None
    if kind == 'integer':
        if from_ui and isinstance(value, str) and re.fullmatch(r'[+-]?\d+', value): value = int(value)
        if type(value) is not int: raise ValueError(label + ' 必須是整數。')
    if kind == 'decimal':
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', value):
            raise ValueError(label + ' 必須是精確小數文字。')
    if kind == 'boolean':
        if from_ui and value in ('是', '否'): value = value == '是'
        if type(value) is not bool: raise ValueError(label + ' 請選擇是或否。')
    if kind == 'single_choice' and value not in field['options']:
        raise ValueError(label + ' 請選擇提供的選項。')
    comparable = Decimal(value) if kind == 'decimal' else value
    for key, predicate in [('min', lambda a,b:a < b), ('max', lambda a,b:a > b)]:
        if key in field:
            boundary = Decimal(field[key]) if kind == 'decimal' else field[key]
            if predicate(comparable, boundary): raise ValueError(label + ' 超過允許範圍。')
    if isinstance(value, str):
        if len(value) < field.get('min_length', 0) or len(value) > field.get('max_length', 50000):
            raise ValueError(label + ' 字數超過允許範圍。')
    return value


def validate_template(template):
    if not isinstance(template, dict) or not isinstance(template.get('id'), str) or not template['id'] or not isinstance(template.get('name'), str):
        raise ValueError('查詢模板定義無效。')
    fields = template.get('parameters')
    if not isinstance(fields, dict): raise ValueError('查詢模板缺少參數定義。')
    for key, field in fields.items():
        if not isinstance(key, str) or not key or key.startswith('_') or not isinstance(field, dict):
            raise ValueError('查詢欄位定義無效。')
        if set(field) - {'label','type','required','default','options','min','max','min_length','max_length'}:
            raise ValueError('查詢欄位含未支援的設定。')
        if not isinstance(field.get('type'),str) or field.get('type') not in TYPES or not isinstance(field.get('label'), str) or not field['label']:
            raise ValueError('查詢欄位類型或標籤不支援。')
        kind = field['type']
        if type(field.get('required', True)) is not bool: raise ValueError('required 必須為是非值。')
        if kind == 'single_choice':
            options = field.get('options')
            if not isinstance(options, list) or not options or any(not isinstance(v,str) or not v for v in options) or len(set(options)) != len(options):
                raise ValueError('查詢選項定義無效。')
        elif 'options' in field: raise ValueError('只有單選欄位可設定 options。')
        for limit in ('min_length','max_length'):
            if limit in field and (kind not in {'text','decimal','single_choice','date'} or type(field[limit]) is not int or field[limit] < 0):
                raise ValueError('字數限制定義無效。')
        if field.get('min_length',0) > field.get('max_length',50000): raise ValueError('字數上下限顛倒。')
        for limit in ('min','max'):
            if limit in field:
                if kind not in {'integer','decimal','date'}: raise ValueError('此欄位不支援數值或日期範圍。')
                _value({'label':field['label'],'type':kind},field[limit])
        if 'min' in field and 'max' in field:
            low, high = (Decimal(field['min']),Decimal(field['max'])) if kind == 'decimal' else (field['min'],field['max'])
            if low > high: raise ValueError('欄位上下限顛倒。')
        if 'default' in field: _value(field,field['default'])
    mapping = template.get('date_range')
    if mapping is not None:
        if not isinstance(mapping,dict) or set(mapping) != {'start','end'} or mapping['start'] == mapping['end']:
            raise ValueError('日期區間映射無效。')
        if any(not isinstance(v,str) or v not in fields or fields[v]['type'] != 'date' for v in mapping.values()):
            raise ValueError('日期映射必須指向兩個日期欄位。')
    return template


def find_template(catalog, query_id):
    if not isinstance(catalog,list): raise ValueError('查詢目錄格式錯誤。')
    matches = [item for item in catalog if isinstance(item,dict) and item.get('id') == query_id]
    if len(matches) != 1: raise ValueError('查詢模板不存在或重複，請重新選擇。')
    return validate_template(matches[0])


def parameters(template, values, from_ui=False):
    fields = validate_template(template)['parameters']
    if not isinstance(values,dict) or set(values)-set(fields): raise ValueError('查詢包含未核准的欄位。')
    result = {}
    for key,field in fields.items():
        if key not in values or values[key] == '' or (field['type']=='text' and isinstance(values[key],str) and not values[key].strip()):
            if field.get('required',True): raise ValueError(field['label']+' 為必填。')
            continue
        result[key] = _value(field,values[key],from_ui)
    return result


def initial_values(template):
    return {key: field.get('default','') for key,field in validate_template(template)['parameters'].items()}


def date_mapping(template, legacy=False):
    validate_template(template)
    mapping = template.get('date_range')
    if mapping is None and legacy: mapping = LEGACY_DATE_RANGES.get(template['id'])
    if mapping is not None and any(key not in template['parameters'] or template['parameters'][key]['type'] != 'date' for key in mapping.values()):
        raise ValueError('舊排程日期欄位已失效。')
    return mapping


def describe(template, values):
    fields = validate_template(template)['parameters']
    return ['{}：{}'.format(fields.get(key,{}).get('label',key), '是' if value is True else '否' if value is False else str(value))
            for key,value in values.items() if not key.startswith('_')]

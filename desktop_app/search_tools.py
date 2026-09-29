"""Bounded, explicitly approved function tools. No model-selected destinations."""
import copy
import hashlib
import json
import math
import re
from .gateways import GatewayError

NAME = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
STOPPED = ('failed', 'cancelled', 'cancel_requested', 'tools_blocked',
           'tool_outcome_unknown', 'tool_submit_unknown')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def schema(value, depth=0):
    """Supported JSON Schema subset; unsupported constraints fail closed."""
    if not isinstance(value, dict) or depth > 6:
        raise GatewayError('搜尋參數結構過深或不是物件。')
    kind = value.get('type')
    fields = {'type', 'description', 'title'}
    fields |= {'object': {'properties', 'required', 'additionalProperties'},
               'string': {'enum', 'minLength', 'maxLength'},
               'integer': {'enum', 'minimum', 'maximum'},
               'number': {'enum', 'minimum', 'maximum'},
               'boolean': {'enum'}, 'array': {'items', 'minItems', 'maxItems'}}.get(kind, set()) if isinstance(kind, str) else set()
    if kind not in ('object', 'string', 'integer', 'number', 'boolean', 'array') or set(value) - fields:
        raise GatewayError('此搜尋參數使用尚未支援的 schema 條件。')
    out = {'type': kind}
    for field in ('description','title'):
        if field in value:
            if not isinstance(value[field],str) or len(value[field])>4000:
                raise GatewayError('搜尋工具說明超過長度限制或格式不符。')
            out[field]=value[field]
    if kind == 'object':
        props, required = value.get('properties', {}), value.get('required', [])
        if (not isinstance(props, dict) or len(props) > 32 or
                not all(isinstance(k, str) and NAME.fullmatch(k) for k in props) or
                not isinstance(required, list) or not all(isinstance(k, str) and k in props for k in required) or
                len(required) != len(set(required)) or value.get('additionalProperties', False) is not False):
            raise GatewayError('搜尋物件欄位或必要參數不受支援。')
        out.update(properties={k: schema(v, depth+1) for k, v in props.items()},
                   required=required, additionalProperties=False)
    elif kind == 'array':
        out['items'] = schema(value.get('items'), depth+1)
    pairs = [('minLength', 'maxLength', 4000)] if kind == 'string' else [('minItems', 'maxItems', 64)] if kind == 'array' else []
    for low, high, limit in pairs:
        a, b = value.get(low, 0), value.get(high, limit)
        if type(a) is not int or type(b) is not int or not 0 <= a <= b <= limit:
            raise GatewayError('搜尋參數大小限制不受支援。')
        out.update({low: a, high: b})
    for key in ('minimum', 'maximum'):
        if key in value:
            v = value[key]
            if type(v) not in (int, float) or not math.isfinite(v):
                raise GatewayError('搜尋數值限制無效。')
            out[key] = v
    if out.get('minimum', -math.inf) > out.get('maximum', math.inf):
        raise GatewayError('搜尋數值範圍無效。')
    if 'enum' in value:
        enum = value['enum']
        if not isinstance(enum, list) or not 1 <= len(enum) <= 64:
            raise GatewayError('搜尋選項格式無效。')
        for v in enum: validate(v, out)
        out['enum'] = copy.deepcopy(enum)
    return out


def validate(value, definition):
    kind = definition['type']
    valid = {'object': isinstance(value, dict), 'array': isinstance(value, list),
             'string': isinstance(value, str), 'integer': type(value) is int,
             'number': type(value) in (int, float), 'boolean': type(value) is bool}[kind]
    if not valid: raise GatewayError('搜尋工具參數型別不符合核准定義。')
    if kind == 'object':
        props = definition['properties']
        if set(value) - set(props) or set(definition['required']) - set(value):
            raise GatewayError('搜尋工具含未知欄位或缺少必要參數。')
        for k, v in value.items(): validate(v, props[k])
    elif kind in ('array', 'string'):
        low, high = ('minItems', 'maxItems') if kind == 'array' else ('minLength', 'maxLength')
        if not definition[low] <= len(value) <= definition[high]:
            raise GatewayError('搜尋工具參數超出大小限制。')
        if kind == 'array':
            for v in value: validate(v, definition['items'])
    elif kind in ('integer', 'number'):
        if not math.isfinite(value) or not definition.get('minimum', -math.inf) <= value <= definition.get('maximum', math.inf):
            raise GatewayError('搜尋工具數值超出範圍。')
    if 'enum' in definition and not any(type(value) is type(v) and value == v for v in definition['enum']):
        raise GatewayError('搜尋工具選項不在核准範圍。')


def policy(value):
    if value is None: return {'tools': []}
    if not isinstance(value, dict) or set(value) != {'tools'} or not isinstance(value['tools'], list) or len(value['tools']) > 16:
        raise GatewayError('搜尋核准清單格式無效。')
    tools, seen = [], set()
    for tool in value['tools']:
        if not isinstance(tool, dict) or not {'name','parameters'}<=set(tool) or set(tool)-{'name','parameters','description'}:
            raise GatewayError('搜尋工具定義無效。')
        name = tool['name']
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen:
            raise GatewayError('搜尋工具名稱無效或重複。')
        definition = schema(tool['parameters'])
        if definition['type'] != 'object': raise GatewayError('搜尋參數必須是物件。')
        entry={'name':name,'parameters':definition}
        if 'description' in tool:
            if not isinstance(tool['description'],str) or len(tool['description'])>4000:
                raise GatewayError('搜尋工具說明超過長度限制或格式不符。')
            entry['description']=tool['description']
        tools.append(entry); seen.add(name)
    result = {'tools': sorted(tools, key=lambda t: t['name'])}
    if len(json.dumps(result).encode()) > 65536: raise GatewayError('搜尋工具定義超出大小限制。')
    return result


def arguments(raw, definition):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate')
            result[key] = value
        return result
    try:
        if not isinstance(raw, str) or len(raw.encode('utf-8')) > 32768: raise ValueError()
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        validate(value, definition)
        return value
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise GatewayError('搜尋工具參數不符合核准定義；本批未執行。') from None

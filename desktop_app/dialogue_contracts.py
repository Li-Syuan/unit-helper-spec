"""Validated task suggestions, with no tool or scheduler capabilities."""
import copy
import re
from datetime import date

ASSISTANTS=[{'id':'demo-general','name':'示範通用助理'}, {'id':'demo-data','name':'示範資料助理'}]
TASK_TYPES=['資料追蹤','摘要整理','異常檢查']
FIELDS={'target','source','task_type','schedule'}


def assistant(value):
    if value not in {p['id'] for p in ASSISTANTS}:raise ValueError('助理未配置或尚未驗證；目前只允許示範助理。')
    return value


def answers(value):
    if not isinstance(value,dict) or set(value)-FIELDS:raise ValueError('草稿包含不支援欄位，未建立任務。')
    result=copy.deepcopy(value)
    for key in ('target','source'):
        if key in result and (not isinstance(result[key],str) or not 1<=len(result[key].strip())<=500):raise ValueError('追蹤對象與來源各需1～500字。')
    if 'task_type' in result and result['task_type'] not in TASK_TYPES:raise ValueError('任務類型不支援。')
    if 'schedule' in result:
        schedule=result['schedule']
        if not isinstance(schedule,dict) or set(schedule)!={'frequency','time_hhmm','weekday','date'}:raise ValueError('執行時間格式無效。')
        if not isinstance(schedule['time_hhmm'],str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',schedule['time_hhmm']):raise ValueError('請使用台北時間HH:MM。')
        frequency=schedule['frequency']
        if frequency not in {'daily','weekly','once'}:raise ValueError('只支援每日、每週或指定日期。')
        if frequency=='weekly':
            if type(schedule['weekday']) is not int or schedule['weekday'] not in range(7):raise ValueError('請選擇星期一至星期日。')
        elif schedule['weekday'] is not None:raise ValueError('此頻率不能指定星期。')
        if frequency=='once':
            try:
                if date.fromisoformat(schedule['date']).isoformat()!=schedule['date']:raise ValueError()
            except (TypeError,ValueError):raise ValueError('請提供有效YYYY-MM-DD日期。') from None
        elif schedule['date'] is not None:raise ValueError('重複排程不能附帶指定日期。')
    return result


def draft(value,assistant_id):
    assistant(assistant_id)
    result=answers(value)
    if set(result)!=FIELDS:raise ValueError('請補齊追蹤對象、資訊來源、任務類型與執行時間。')
    return result

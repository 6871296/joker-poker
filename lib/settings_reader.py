import json
import os

_SETTINGS = None
_DEFAULT_SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'settings.json'
)


def load_settings(path=None):
    """加载 settings.json，返回字典"""
    global _SETTINGS
    if path is None:
        path = _DEFAULT_SETTINGS_PATH
    try:
        with open(path, 'r', encoding='utf-8') as f:
            _SETTINGS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _SETTINGS = {}
    return _SETTINGS


def get(key, default=None):
    """
    读取配置项，支持嵌套键（用点号分隔）。
    例如 get('uno.superposing.P2P2', True)
    """
    if _SETTINGS is None:
        load_settings()
    keys = key.split('.')
    value = _SETTINGS
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


def get_all():
    """返回所有配置的副本"""
    if _SETTINGS is None:
        load_settings()
    return _SETTINGS.copy()

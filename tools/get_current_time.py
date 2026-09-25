from __future__ import annotations
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from tzlocal import get_localzone_name


def _safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception:  # noqa: BLE001
        return "<unprintable>"


def _local_timezone() -> str:
    """Возвращает IANA-имя локальной таймзоны компьютера.

    При любой проблеме (tzlocal недоступен, зона не определяется) —
    фолбэк на 'UTC'.
    """
    try:
        tzname = get_localzone_name()
    except Exception:  # noqa: BLE001
        return "UTC"
    if not tzname or not isinstance(tzname, str):
        return "UTC"
    return tzname


def _ok(result: str) -> dict[str, Any]:
    return {"success": True, "error": None, "result": result}


def _err(message: str) -> dict[str, Any]:
    return {"success": False, "error": message, "result": None}


def get_current_time(timezone: str | None = None) -> dict[str, Any]:
    """Возвращает текущее время в указанной таймзоне (IANA).

    Args:
        timezone: Имя таймзоны, например 'Europe/Moscow', 'UTC'.
            Если None или пусто — используется локальная таймзона компьютера.

    Returns:
        {"success": bool, "error": str | None, "result": str | None}
    """
    if timezone is None or not timezone:
        timezone = _local_timezone()

    if not isinstance(timezone, str):
        return _err(f"Некорректная таймзона: {_safe_repr(timezone)}")

    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return _err(f"Неизвестная таймзона: {_safe_repr(timezone)}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Неожиданная ошибка: {_safe_repr(e)}")

    return _ok(datetime.now(tz).strftime(f"%Y-%m-%d %H:%M:%S ({timezone})"))


get_current_time.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.get_current_time.get_current_time",
        "description": (
            "Возвращает текущие дату и время в указанной таймзоне.\n"
            "Используй, когда пользователь спрашивает «сколько сейчас времени», "
            "«какое сегодня число», «который час в <городе>» и т.п.\n"
            "Ответ: {success: bool, error: str | null, result: str | null}.\n"
            "- success=False означает, что таймзону распознать не удалось; "
            "error содержит текст ошибки, result=null.\n"
            "- success=True: result — строка вида 'YYYY-MM-DD HH:MM:SS (<timezone>)'.\n"
            "\n"
            "Таймзона задаётся в формате IANA (например 'Europe/Moscow', "
            "'America/New_York', 'UTC'). Если пользователь называет город — "
            "сам преобразуй его в подходящую IANA-таймзону.\n"
            "Если пользователь не указал таймзону — не передавай параметр: "
            "функция сама подставит локальную таймзону компьютера. "
            "Явно указывай 'UTC' только если пользователь просит именно UTC."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "Имя таймзоны в формате IANA, например "
                        "'Europe/Moscow', 'Europe/Berlin', 'America/New_York', 'UTC'. "
                        "Регистр важен. Если не указать — используется "
                        "локальная таймзона компьютера."
                    )
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
}

from __future__ import annotations
from typing import Dict, Any, Optional
from loguru import logger
import requests

proxies = {
    "http": "http://127.0.0.1:10808",
    "https": "http://127.0.0.1:10808"
}

@logger.catch
def get_weather(timeout: int = 10, proxies: Dict = proxies) -> Dict[str, Any]:
    """
    Возвращает погоду относительно IP-адреса клиента.

    Args:
        timeout: int    Сколько секунд ждать ответа от сервера. По умолчанию - 10 секунд.

    Returns:
        Словарь с полями:
            - success (bool):       True, если поиск выполнен без критических ошибок.
            - Error (str):          Содержит текст ошибки, если success False
            - temperature (str):    Температура по Цельсию.
            - humidity (str):       Относительная влажность воздуха.
    """
    logger.debug(" -> In function get_weather.get_weather()")
    wttr_url = "https://wttr.in/?format=j1"

    try:
        r = requests.get(wttr_url, timeout=timeout, proxies=proxies)
        r.raise_for_status()
        d = r.json()
        c = d.get("current_condition", [{}])[0]
    except Exception as e:
        return {
            "success": False,
            "error": f"{e}",
            "temperature": None,
            "humidity": None
        }

    logger.debug(" <- Out function get_weather.get_weather()")
    return {
        "success": True,
        "error": "",
        "temperature": c.get("FeelsLikeC"),
        "humidity": c.get("humidity")
    }


get_weather.tool_description = {
    "type": "function",
    "function": {
        "name": "get_weather.get_weather",
        "description": "Возвращает погоду относительно местоположения клиента (геолокация вычисляется по IP-адресу клиента). Возвращает структурированный словарь с полями: success (bool), error (str), tenperature (str), humidity (str). Если запрос завершается с ошибкой, success=false и error содержит описание проблемы.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False
        }
    }
}


if __name__ == '__main__':
    pass
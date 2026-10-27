from __future__ import annotations
from config import settings
from typing import Dict, Any, Literal, Optional, List, get_args
from tavily import TavilyClient, TavilyKeylessLimitError
from tavily.errors import (
    BadRequestError,
    ForbiddenError,
    InvalidAPIKeyError,
    UsageLimitExceededError,
    TimeoutError as TavilyTimeoutError,
)
from urllib.parse import urlparse
from requests.exceptions import Timeout as RequestsTimeoutError

SearchDepth = Literal["basic", "advanced", "fast", "ultra-fast"]
_ALLOWED_SEARCH_DEPTHS = frozenset(get_args(SearchDepth))

SearchAnswers = Literal["basic", "advanced"]
_ALLOWED_ANSWERS = frozenset(get_args(SearchAnswers))

_TAVILY_QUERY_LIMIT = 400
_TAVILY_MAX_RESULTS_LIMIT = 20
_TAVILY_TIMEOUT = 30

_SNIPPET_HARD_MIN = 50
_SNIPPET_HARD_MAX = 2000
_SNIPPET_BALANCED = _SNIPPET_HARD_MIN + (_SNIPPET_HARD_MAX - _SNIPPET_HARD_MIN) // 5
_SNIPPETS_TOTAL_BUDGET = 4000

_ALLOWED_PROXY_KEYS = frozenset({"http", "https"})
_ALLOWED_PROXY_SCHEMES = frozenset({"http", "https"})


def _cfg(key: str, default: Any) -> Any:
    """Читает настройку из settings с fallback."""
    return settings.get(key, default)


def websearch_tavily(
    query: str,
    search_depth: SearchDepth = "basic",
    max_results: int = 5,
    include_answer: bool | SearchAnswers = "advanced",
    result_length: Optional[int] = None,
    api_key: Optional[str] = None,
    proxies: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Ищет в интернете через Tavily и возвращает результат, готовый для LLM:
    краткий ответ (если доступен) и нумерованные источники.

    Невалидные аргументы не приводят к исключению — они откатываются
    к дефолтам или зажимаются в допустимый диапазон. Ошибки (сеть, API,
    валидация) возвращаются в поле ``error``.

    Args:
        query: Поисковый запрос. Обрезается по краям, лимит — 400 символов.
        search_depth: ``"basic"`` (быстро) или ``"advanced"`` (глубже и дороже).
            Также принимаются ``"fast"`` / ``"ultra-fast"`` при поддержке SDK.
        max_results: Количество источников, зажимается в ``[1, 20]``.
        include_answer: ``True`` / ``False`` или ``"basic"`` / ``"advanced"``.
            Управляет кратким ответом от поисковика.
        result_length: Длина фрагмента на источник в символах, зажимается
            в ``[50, 2000]``. ``None`` → сбалансированный дефолт (~400).
        api_key: Ключ ``tvly-...`` (≥20 символов). ``None`` → keyless-режим
            с жёсткими rate-лимитами.
        proxies: ``{"http": "...", "https": "..."}`` для ``requests``.
            ``None`` → берётся из ``settings["http_proxies"]``.

    Returns:
        ``{"success": bool, "content": str | None, "error": str | None}``.
        При успехе ``content`` заполнен, ``error`` — ``None``; при ошибке
        наоборот.
    """
    result = {
        "success": False,
        "content": None,
        "error": None,
    }

    # Проверяем полученный запрос query
    if not isinstance(query, str):
        result["error"] = "Поисковый запрос должен быть строкой."
        return result

    query = query.strip()
    if not query:
        result["error"] = "Поисковый запрос пустой."
        return result

    if len(query) > _TAVILY_QUERY_LIMIT:
        query = query[:_TAVILY_QUERY_LIMIT].rstrip()

    # Проверяем search_depth
    if not isinstance(search_depth, str) or search_depth not in _ALLOWED_SEARCH_DEPTHS:
        search_depth = "basic"

    # Проверяем max_results
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        max_results = 5
    else:
        max_results = max(1, min(max_results, _TAVILY_MAX_RESULTS_LIMIT))

    # Проверяем include_answer
    if isinstance(include_answer, bool):
        pass  # True/False валидны
    elif not isinstance(include_answer, str) or include_answer not in _ALLOWED_ANSWERS:
        include_answer = "advanced"

    # Проверяем result_length
    if (
        result_length is None
        or isinstance(result_length, bool)
        or not isinstance(result_length, int)
    ):
        result_length = _SNIPPET_BALANCED
    else:
        result_length = max(_SNIPPET_HARD_MIN, min(result_length, _SNIPPET_HARD_MAX))

    # Проверяем api_key
    if api_key is not None:
        if not isinstance(api_key, str):
            result["error"] = "api_key должен быть строкой или None (keyless mode)."
            return result
        api_key = api_key.strip()
        if not api_key.startswith("tvly-") or len(api_key) < 20:
            result["error"] = (
                "Неверный формат API-ключа Tavily: "
                "ожидается 'tvly-...' длиной не менее 20 символов."
            )
            return result

    # Проверяем proxies
    if proxies is None:
        proxies = _cfg("http_proxies", None) or {}
    else:
        if not isinstance(proxies, dict):
            result["error"] = (
                "proxies должен быть словарём {'http': '...', 'https': '...'} или None."
            )
            return result

        for key, value in proxies.items():
            if key not in _ALLOWED_PROXY_KEYS:
                result["error"] = (
                    f"Недопустимый ключ proxies: {key!r}. "
                    "Ожидается 'http' или 'https'."
                )
                return result
            if not isinstance(value, str) or not value.strip():
                result["error"] = (
                    f"Значение proxies[{key!r}] должно быть непустой строкой."
                )
                return result

            parsed = urlparse(value.strip())
            if parsed.scheme not in _ALLOWED_PROXY_SCHEMES or not parsed.netloc:
                result["error"] = (
                    f"Некорректный URL прокси для {key!r}: {value!r}. "
                    f"Ожидается схема {sorted(_ALLOWED_PROXY_SCHEMES)} и хост."
                )
                return result

    try:
        t_client = TavilyClient(
            api_key=api_key,
            proxies=proxies,
        )
        resp = t_client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=include_answer,
            timeout=_TAVILY_TIMEOUT,
        )
    except TavilyKeylessLimitError:
        result["error"] = "Закончились бесплатные запросы к поисковой машине."
        return result
    except InvalidAPIKeyError:
        result["error"] = "Неверный или отозванный API-ключ."
        return result
    except UsageLimitExceededError:
        result["error"] = "Превышен лимит запросов к поисковой машине."
        return result
    except ForbiddenError as e:
        result["error"] = (
            f"Доступ к поисковой машине запрещён (403). "
            f"Возможно, гео-блок или ограничение аккаунта: {e}"
        )
        return result
    except BadRequestError as e:
        result["error"] = f"Некорректный запрос к поисковой машине: {e}"
        return result
    except TavilyTimeoutError as e:
        result["error"] = (
            f"Поиск не уложился в таймаут ({_TAVILY_TIMEOUT} с). "
            f"Попробуйте позже или проверьте прокси/сеть: {e}"
        )
        return result
    except RequestsTimeoutError as e:
        result["error"] = (
            f"Сетевой таймаут при запросе к поисковой машине "
            f"(прокси или соединение): {e}"
        )
        return result
    except Exception as e:  # noqa: BLE001
        result["error"] = f"Неожиданная ошибка поиска: {type(e).__name__}: {e}"
        return result

    resp_parts: List[str] = []
    if search_answer := (resp.get("answer") or "").strip():
        resp_parts.append(f"Краткий ответ: {search_answer}")

    search_results = resp.get("results") or []
    if not search_results:
        resp_parts.append("Ничего не найдено.")
    else:
        resp_parts.append("Источники:")
        used_budget = 0
        for num, search_result in enumerate(search_results, 1):
            title = (search_result.get("title") or "").strip() or "(без заголовка)"
            url = (search_result.get("url") or "").strip()
            content = (search_result.get("content") or "").strip()

            cut = min(result_length, (_SNIPPETS_TOTAL_BUDGET - used_budget))
            if cut <= 0:
                snippet = ""
            elif len(content) > cut:
                snippet = content[:cut].rstrip() + "…"
            else:
                snippet = content
            used_budget += len(snippet)

            block = f"{num}. {title}\n    {url}"
            if snippet:
                block += f"\n    {snippet}"
            resp_parts.append(block)

    result["success"] = True
    result["content"] = "\n\n".join(resp_parts)
    return result


websearch_tavily.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.websearch_tavily.websearch_tavily",
        "description": (
            "Поиск актуальной информации в интернете. "
            "Вызывай только для свежих данных: новости, курсы, цены, события "
            "после обучения модели. Не используй для общих знаний, математики и кода. "
            "Возвращает краткий ответ и нумерованные источники со ссылками."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Поисковый запрос: имена, даты, названия. До 400 символов."
                    ),
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "default": "basic",
                    "description": ("basic — быстро; advanced — глубже и дороже."),
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Количество источников, 1–10.",
                },
                "include_answer": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "default": "advanced",
                    "description": "Уровень краткого ответа от поисковика.",
                },
                "result_length": {
                    "type": "integer",
                    "default": 400,
                    "description": "Длина фрагмента на источник в символах.",
                },
            },
            "required": ["query"],
        },
    },
}

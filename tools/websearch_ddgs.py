from __future__ import annotations

from typing import Dict, Optional, List, Tuple, Any

from ddgs import DDGS
from ddgs.exceptions import DDGSException, TimeoutException

from config import settings

_QUERY_MAX_CHARS = 400

_MAX_RESULTS_MIN = 1
_MAX_RESULTS_MAX = 20
_MAX_RESULTS_DEFAULT = 5

_SNIPPET_HARD_MIN = 50
_SNIPPET_HARD_MAX = 2000
_SNIPPET_BALANCED = _SNIPPET_HARD_MIN + (_SNIPPET_HARD_MAX - _SNIPPET_HARD_MIN) // 5
_SNIPPETS_TOTAL_BUDGET = 4000

_TIMEOUT_MIN = 3
_TIMEOUT_MAX = 60
_TIMEOUT_DEFAULT = 10

_ALLOWED_BACKENDS = frozenset(
    {
        "auto",
        "google",
        "brave",
        "bing",
        "duckduckgo",
        "mojeek",
        "yandex",
        "yahoo",
        "wikipedia",
    }
)

_ALLOWED_SAFESEARCH = frozenset({"on", "moderate", "off"})
_ALLOWED_TIMELIMIT = frozenset({"d", "w", "m", "y"})

_PROXY_SCHEMES = ("http://", "https://")


def _clamp_int(value: int, lo: int, hi: int, default: int) -> int:
    """Возвращает value в [lo, hi] или default, если value — не int."""
    # type(value) is not int отсекает и bool (bool ⊂ int в Python).
    if type(value) is not int:  # type: ignore[unreachable]
        return default
    return max(lo, min(value, hi))


def _prepare_query(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Возвращает (нормализованный query, None) или (None, текст ошибки)."""
    if not isinstance(query, str):  # type: ignore[unreachable]
        return None, "Поисковый запрос должен быть строкой."
    query = query.strip()
    if not query:
        return None, "Поисковый запрос пустой."
    if len(query) > _QUERY_MAX_CHARS:
        query = query[:_QUERY_MAX_CHARS].rstrip()
    return query, None


def _prepare_snippet_length(value: Optional[int]) -> int:
    if value is None or type(value) is not int:  # type: ignore[unreachable]
        return _SNIPPET_BALANCED
    return max(_SNIPPET_HARD_MIN, min(value, _SNIPPET_HARD_MAX))


def _validate_proxy_url(value: str) -> Optional[str]:
    """None — валидный URL прокси, иначе — текст ошибки."""
    if not isinstance(value, str) or not value.strip():  # type: ignore[unreachable]
        return "URL прокси должен быть непустой строкой."
    if not value.strip().startswith(_PROXY_SCHEMES):
        return (
            f"Некорректный URL прокси: {value!r}. "
            f"Поддерживаются только схемы http:// и https://."
        )
    return None


def _resolve_proxy(
    proxy: Optional[str | Dict[str, str]],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Приводит proxy (str | dict | None) к строке URL для ddgs.
    Возвращает (url, None) или (None, текст ошибки).
    """
    if proxy is None:
        return None, None

    if isinstance(proxy, str):
        value = proxy.strip()
        if not value:
            return None, None
        err = _validate_proxy_url(value)
        return (None, err) if err else (value, None)

    if isinstance(proxy, dict):
        if not proxy:
            return None, None
        for key in ("https", "http"):
            value = proxy.get(key)
            if not isinstance(value, str):
                continue
            value = value.strip()
            if _validate_proxy_url(value) is None:
                return value, None
        return None, "dict с прокси не содержит валидных прокси"

    return None, "proxy должен быть строкой, dict или None."


def _format_sources(sources: List[Dict], result_length: int) -> str:
    """
    Форматирует нормализованные источники [{"title", "url", "content"}, ...]
    в нумерованный блок с общим бюджетом символов.
    """
    if not sources:
        return "Ничего не найдено."

    parts = ["Источники:"]
    used = 0
    for num, src in enumerate(sources, 1):
        title = (src.get("title") or "").strip() or "(без заголовка)"
        url = (src.get("url") or "").strip() or "(без URL)"
        content = (src.get("content") or "").strip() or "(без контента)"

        cut = min(result_length, _SNIPPETS_TOTAL_BUDGET - used)
        if cut <= 0:
            snippet = ""
        elif len(content) > cut:
            snippet = content[:cut].rstrip() + "…"
        else:
            snippet = content
        used += len(snippet)

        block = f"{num}. {title}\n    {url}"
        if snippet:
            block += f"\n    {snippet}"
        parts.append(block)

    return "\n\n".join(parts)


def websearch_ddgs(
    query: str,
    backend: str = "auto",
    max_results: int = _MAX_RESULTS_DEFAULT,
    result_length: Optional[int] = None,
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    timeout: int = _TIMEOUT_DEFAULT,
    proxy: Optional[str | dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Ищет в интернете через ddgs (DuckDuckGo и др.) и возвращает нумерованные
    источники с заголовками, ссылками и фрагментами — готово для LLM.

    Невалидные аргументы не приводят к исключению: они откатываются к дефолтам
    или зажимаются в допустимый диапазон. Ошибки (сеть, движок, таймаут,
    некорректный прокси) возвращаются в поле ``error``.

    Args:
        query: Поисковый запрос. Обрезается по краям, лимит — 400 символов.
        backend: Движок: ``"auto"`` (ddgs выбирает сам), ``"google"``,
            ``"brave"``, ``"bing"``, ``"duckduckgo"`` и др.
        max_results: Количество источников, зажимается в ``[1, 20]``.
        result_length: Длина фрагмента на источник в символах,
            зажимается в ``[50, 2000]``. ``None`` → сбалансированный дефолт (~440).
        region: Регион, например ``"ru-ru"``, ``"us-en"``. ``"wt-wt"`` — без региона.
        safesearch: ``"on"`` / ``"moderate"`` / ``"off"``.
        timelimit: ``"d"`` (день), ``"w"`` (неделя), ``"m"`` (месяц), ``"y"`` (год).
        timeout: Таймаут HTTP-запроса в секундах, зажимается в ``[3, 60]``.
        proxy: URL прокси (строка) или dict ``{"http": "...", "https": "..."}``.
            Из dict пробуются ``https``, затем ``http``; берётся первый валидный.
            Поддерживаются только схемы ``http://`` и ``https://``;
            SOCKS не поддерживается.

    Returns:
        ``{"success": bool, "content": str | None, "error": str | None}``.
        При успехе ``content`` содержит нумерованные источники; при ошибке —
        ``None``, а ``error`` — человекочитаемое сообщение.
    """
    result: Dict[str, Any] = {
        "success": False,
        "content": None,
        "error": None,
    }

    prepared_query, err = _prepare_query(query)
    if prepared_query is None or err is not None:
        result["error"] = err or "Не удалось подготовить запрос."
        return result

    if not isinstance(backend, str) or backend not in _ALLOWED_BACKENDS:
        backend = "auto"

    max_results = _clamp_int(
        max_results, _MAX_RESULTS_MIN, _MAX_RESULTS_MAX, _MAX_RESULTS_DEFAULT
    )
    result_length = _prepare_snippet_length(result_length)
    timeout = _clamp_int(timeout, _TIMEOUT_MIN, _TIMEOUT_MAX, _TIMEOUT_DEFAULT)

    if not isinstance(region, str) or not region.strip():
        region = "wt-wt"
    if safesearch not in _ALLOWED_SAFESEARCH:
        safesearch = "moderate"
    if timelimit not in _ALLOWED_TIMELIMIT and timelimit is not None:
        timelimit = None

    if proxy is None:
        proxy = settings.get("http_proxies") or {}
    proxy_str, proxy_err = _resolve_proxy(proxy)
    if proxy_err:
        result["error"] = proxy_err
        return result

    try:
        ddgs = DDGS(proxy=proxy_str, timeout=timeout)
        hits = ddgs.text(
            prepared_query,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            backend=backend,
            max_results=max_results,
        )
    except TimeoutException as e:
        result["error"] = f"Таймаут поиска ({timeout} с): {type(e).__name__}: {e}"
        return result
    except DDGSException as e:
        result["error"] = f"Ошибка поискового движка: {type(e).__name__}: {e}"
        return result
    except Exception as e:  # noqa: BLE001
        result["error"] = f"Неожиданная ошибка поиска: {type(e).__name__}: {e}"
        return result

    try:
        hits_iter = iter(hits or [])
    except TypeError:
        hits_iter = iter([])

    sources = [
        {
            "title": h.get("title") or "",
            "url": h.get("href") or h.get("url") or "",
            "content": h.get("body") or h.get("snippet") or "",
        }
        for h in hits_iter
        if isinstance(h, dict)
    ]

    result["success"] = True
    result["content"] = _format_sources(sources, result_length)
    return result


websearch_ddgs.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.websearch_ddgs.websearch_ddgs",
        "description": (
            "Поиск актуальной информации в интернете (DuckDuckGo и др.). "
            "Вызывай только для свежих данных: новости, курсы, цены, события "
            "после обучения модели. Не используй для общих знаний, математики и кода. "
            "Возвращает нумерованные источники со ссылками и фрагментами."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос (до 400 символов).",
                },
                "backend": {
                    "type": "string",
                    "enum": ["auto", "google", "brave", "bing", "duckduckgo"],
                    "default": "auto",
                    "description": "Поисковый движок. 'auto' — ddgs выбирает сам.",
                },
                "max_results": {
                    "type": "integer",
                    "default": _MAX_RESULTS_DEFAULT,
                    "description": "Количество источников, 1–20.",
                },
                "result_length": {
                    "type": "integer",
                    "default": _SNIPPET_BALANCED,
                    "description": "Длина фрагмента на источник в символах.",
                },
                "region": {
                    "type": "string",
                    "default": "wt-wt",
                    "description": "Регион, например 'ru-ru' или 'us-en'.",
                },
                "safesearch": {
                    "type": "string",
                    "enum": ["on", "moderate", "off"],
                    "default": "moderate",
                    "description": "Фильтр безопасного поиска.",
                },
                "timelimit": {
                    "type": "string",
                    "enum": ["d", "w", "m", "y"],
                    "description": "Свежесть: d — день, w — неделя, m — месяц, y — год.",
                },
            },
            "required": ["query"],
        },
    },
}

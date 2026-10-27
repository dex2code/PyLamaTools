from __future__ import annotations
from config import settings
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import requests
import trafilatura
import re

_CONNECT_TIMEOUT_MIN = 0.5
_CONNECT_TIMEOUT_MAX = 60.0
_READ_TIMEOUT_MIN = 1.0
_READ_TIMEOUT_MAX = 300.0
_MAX_BYTES_MIN = 1024
_MAX_BYTES_MAX = 50 * 1024 * 1024
_MAX_CHARS_MIN = 100
_MAX_CHARS_MAX = 1_000_000

_DEFAULT_CONNECT_TIMEOUT = 5.0
_DEFAULT_READ_TIMEOUT = 15.0
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024
_DEFAULT_MAX_CHARS = 20_000
_DEFAULT_USER_AGENT = "PyLamaTools/1.0 (tool: fetch_url)"
_DEFAULT_ALLOWED_CONTENT: tuple[str, ...] = (
    "text/html",
    "text/plain",
    "application/json",
    "application/xml",
    "text/xml",
    "application/xhtml+xml",
)

_ALLOWED_PROXY_KEYS = frozenset({"http", "https"})
_ALLOWED_PROXY_SCHEMES = frozenset({"http", "https"})


def _clamp_float(value: Any, lo: float, hi: float, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(lo, min(float(value), hi))


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(lo, min(value, hi))


def _validate_proxies(proxies: Any) -> Optional[str]:
    """None — валидны, строка — описание ошибки."""
    if not isinstance(proxies, dict):
        return "proxies должен быть словарём {'http': '...', 'https': '...'}."
    for key, value in proxies.items():
        if key not in _ALLOWED_PROXY_KEYS:
            return f"Недопустимый ключ proxies: {key!r}. Ожидается 'http' или 'https'."
        if not isinstance(value, str) or not value.strip():
            return f"Значение proxies[{key!r}] должно быть непустой строкой."
        parsed = urlparse(value.strip())
        if parsed.scheme not in _ALLOWED_PROXY_SCHEMES or not parsed.netloc:
            return (
                f"Некорректный URL прокси для {key!r}: {value!r}. "
                f"Ожидается схема {sorted(_ALLOWED_PROXY_SCHEMES)} и хост."
            )
    return None


def fetch_url(
    url: str,
    connect_timeout: Optional[float] = None,
    read_timeout: Optional[float] = None,
    max_bytes: Optional[int] = None,
    max_chars: Optional[int] = None,
    user_agent: Optional[str] = None,
    allowed_content: Optional[tuple[str, ...]] = None,
    allow_redirects: Optional[bool] = None,
    proxies: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Скачивает URL и извлекает из него текстовое содержимое.

    Функция выполняет HTTP(S)-запрос, ограничивает размер ответа
    (в байтах и символах), извлекает основной текст через
    :mod:`trafilatura` и возвращает его в структурированном виде.
    Если извлечение не удалось (например, для JSON или XML), содержимое
    декодируется как текст с учётом ``charset`` из заголовка
    ``Content-Type`` (fallback — UTF-8 с ``errors="replace"``).

    Никакие исключения наружу не пробрасываются: все ошибки
    (сетевые, HTTP, таймауты, ошибки извлечения) упаковываются
    в поле ``result["error"]``. Вызывающая сторона должна проверять
    ``result["success"]``.

    Args:
        url: Адрес страницы. Поддерживаются только схемы ``http``
            и ``https``; адрес должен содержать домен.
        connect_timeout: Таймаут установки TCP-соединения, секунды.
        read_timeout: Таймаут ожидания каждого следующего чанка при
            чтении тела, секунды. **Не** ограничивает общее время
            запроса: медленный сервер, присылающий данные реже
            ``read_timeout``, может удерживать соединение долго.
        max_bytes: Максимальный размер тела ответа в байтах.
            Проверяется дважды: предварительно по ``Content-Length``
            (если сервер его прислал) и фактически при чтении через
            ``iter_content``. При превышении чтение прекращается,
            а в ``result["truncated"]`` выставляется ``True``.
        max_chars: Максимальное количество символов в извлекаемом
            тексте. Если текст длиннее — он обрезается, к нему
            добавляется пометка, а ``result["truncated"]`` становится
            ``True``.
        user_agent: Значение заголовка ``User-Agent``.
        allowed_content: Кортеж допустимых медиатипов (без параметров,
            например ``"text/html"``). Сравнение идёт по части
            ``Content-Type`` до первой ``;``. Если сервер не прислал
            ``Content-Type``, проверка пропускается и ответ скачивается.
        allow_redirects: Следовать ли HTTP-редиректам. Учтите, что при
            ``True`` валидация конечного адреса (например, на предмет
            приватных IP) не выполняется — это ответственность
            вызывающей стороны, если она работает в недоверенном
            окружении.
        proxies: Словарь прокси в формате :mod:`requests`
            (``{"http": "...", "https": "..."}``). ``None`` — без прокси.

    Returns:
        Словарь со следующими ключами:

        - ``success`` (``bool``): ``True``, если текст успешно получен.
        - ``content`` (``str | None``): извлечённый текст; ``None`` при
          ошибке. Может быть короче исходного, если сработал лимит
          ``max_chars`` — см. ``truncated``.
        - ``size_chars`` (``int``): длина ``content`` в символах
          **после** применения ``max_chars``. При ошибке — ``0``.
        - ``truncated`` (``bool``): ``True``, если ответ был обрезан
          по ``max_bytes`` или по ``max_chars``. Позволяет отличить
          полный текст от неполного; сам ``content`` при этом
          остаётся валидной строкой.
        - ``error`` (``str | None``): человекочитаемое описание ошибки
          или ``None`` при успехе.
    """

    result = {
        "success": False,
        "content": None,
        "size_chars": 0,
        "truncated": False,
        "error": None,
    }

    # --- проверяем proxies: из аргумента или из settings, с валидацией. ---
    if proxies is None:
        proxies = settings.get("http_proxies", None) or {}
    proxy_err = _validate_proxies(proxies)
    if proxy_err:
        result["error"] = proxy_err
        return result

    # --- проверяем url ---
    if not isinstance(url, str):
        result["error"] = "URL должен быть строкой."
        return result
    url = url.strip()
    if not url:
        result["error"] = "URL пустой."
        return result

    try:
        url_parsed = urlparse(url)
    except Exception as e:  # noqa: BLE001
        result["error"] = f"Невалидный URL: {type(e).__name__}: {e}"
        return result

    if url_parsed.scheme not in ("http", "https"):
        result["error"] = (
            f"Поддерживаются только http/https. Получено: {url_parsed.scheme!r}"
        )
        return result
    if not url_parsed.netloc:
        result["error"] = "В URL отсутствует домен."
        return result

    # --- числовые параметры: clamp, а не падение ---
    connect_timeout = _clamp_float(
        connect_timeout,
        _CONNECT_TIMEOUT_MIN,
        _CONNECT_TIMEOUT_MAX,
        _DEFAULT_CONNECT_TIMEOUT,
    )
    read_timeout = _clamp_float(
        read_timeout,
        _READ_TIMEOUT_MIN,
        _READ_TIMEOUT_MAX,
        _DEFAULT_READ_TIMEOUT,
    )
    max_bytes = _clamp_int(
        max_bytes, _MAX_BYTES_MIN, _MAX_BYTES_MAX, _DEFAULT_MAX_BYTES
    )
    max_chars = _clamp_int(
        max_chars, _MAX_CHARS_MIN, _MAX_CHARS_MAX, _DEFAULT_MAX_CHARS
    )

    # --- user_agent: непустая строка без переводов строки (header injection) ---
    if (
        not isinstance(user_agent, str)
        or not user_agent.strip()
        or "\r" in user_agent
        or "\n" in user_agent
    ):
        user_agent = _DEFAULT_USER_AGENT
    else:
        user_agent = user_agent.strip()

    # --- allowed_content: к нижнему регистру, без параметров ---
    if isinstance(allowed_content, (tuple, list)):
        normalized = tuple(
            str(mt).split(";", 1)[0].strip().lower()
            for mt in allowed_content
            if isinstance(mt, str) and mt.strip()
        )
        allowed_content = normalized or _DEFAULT_ALLOWED_CONTENT
    else:
        allowed_content = _DEFAULT_ALLOWED_CONTENT

    # --- allow_redirects ---
    if not isinstance(allow_redirects, bool):
        allow_redirects = True

    try:
        with requests.get(
            url=url_parsed.geturl(),
            headers={"User-Agent": user_agent},
            timeout=(connect_timeout, read_timeout),
            allow_redirects=allow_redirects,
            proxies=proxies,
            stream=True,
        ) as response:
            response.raise_for_status()

            raw_length = response.headers.get("Content-Length")
            if raw_length:
                try:
                    if int(raw_length) > max_bytes:
                        result["error"] = (
                            f"Ответ слишком большой: {raw_length} байт. "
                            f"Лимит: {max_bytes} байт."
                        )
                        return result
                except Exception:
                    pass

            raw_content_type = response.headers.get("Content-Type", "").lower()
            media_type = raw_content_type.split(";", 1)[0].strip().lower()
            if media_type and media_type not in allowed_content:
                result["error"] = (
                    f"Неподдерживаемый Content-Type: {raw_content_type}. "
                    f"Инструмент умеет только: {allowed_content}"
                )
                return result

            chunks: list[bytes] = []
            total_bytes = 0
            try:
                for chunk in response.iter_content(chunk_size=2048):
                    if not chunk:
                        continue
                    needed = max_bytes - total_bytes
                    if len(chunk) > needed:
                        chunks.append(chunk[:needed])
                        total_bytes = max_bytes
                        result["truncated"] = True
                        break
                    chunks.append(chunk)
                    total_bytes += len(chunk)
            except Exception as e:  # noqa: BLE001
                result["error"] = (
                    f"Ошибка при чтении тела ответа: {type(e).__name__}: {e}"
                )
                return result

            content_bytes = b"".join(chunks)
            if not content_bytes:
                result["error"] = f"Пустой ответ от {url}"
                return result

    except requests.exceptions.Timeout:
        result["error"] = f"Таймаут при запросе к {url}"
        return result
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL-ошибка при запросе к {url}: {e}"
        return result
    except requests.exceptions.TooManyRedirects:
        result["error"] = f"Слишком много редиректов при запросе к {url}"
        return result
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Ошибка соединения с {url}: {type(e).__name__}: {e}"
        return result
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP-ошибка {url}: {e}"
        return result
    except requests.exceptions.RequestException as e:
        result["error"] = f"Ошибка запроса к {url}: {type(e).__name__}: {e}"
        return result
    except Exception as e:  # noqa: BLE001
        result["error"] = (
            f"Непредвиденная ошибка при запросе к {url}: {type(e).__name__}: {e}"
        )
        return result

    content_text = ""
    extraction_error: str | None = None
    try:
        content_text = (
            trafilatura.extract(
                filecontent=content_bytes,
                include_comments=False,
                favor_precision=True,
            )
            or ""
        )
    except Exception as e:  # noqa: BLE001
        extraction_error = f"{type(e).__name__}: {e}"

    if not content_text:
        charset = None
        m = re.search(r"charset\s*=\s*([^\s;]+)", raw_content_type)
        if m:
            charset = m.group(1).strip("\"'").lower()
        enc = charset or "utf-8"
        try:
            content_text = content_bytes.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            content_text = content_bytes.decode("utf-8", errors="replace")

    if len(content_text) > max_chars:
        original_len = len(content_text)
        content_text = content_text[:max_chars] + (
            f"\n\n[...Текст обрезан: было {original_len} символов, "
            f"лимит {max_chars}.]"
        )
        result["truncated"] = True

    if not content_text.strip():
        reason = extraction_error or "пустой текст после извлечения"
        result["error"] = f"Не удалось извлечь текст из {url}: {reason}"
        return result

    result["success"] = True
    result["content"] = content_text
    result["size_chars"] = len(content_text)
    return result


fetch_url.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.fetch_url.fetch_url",
        "description": (
            "Скачивает URL по HTTP(S) и извлекает основной текст. "
            "Только http/https и текстовые форматы (html, text, json, xml, xhtml). "
            "Размер ограничивается; при превышении текст обрезается и truncated=True. "
            "Не бросает исключений — ошибки в поле error."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "Полный URL страницы (http/https, с доменом), "
                        "например 'https://example.com/article'."
                    ),
                },
                "max_chars": {
                    "type": "integer",
                    "default": 20000,
                    "description": "Максимум символов в извлечённом тексте.",
                },
                "max_bytes": {
                    "type": "integer",
                    "default": 2097152,
                    "description": "Максимум байт ответа (по умолчанию 2 МиБ).",
                },
                "allow_redirects": {
                    "type": "boolean",
                    "default": True,
                    "description": "Следовать ли HTTP-редиректам.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
}

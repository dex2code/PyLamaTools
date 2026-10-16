from __future__ import annotations

import errno
import shutil
from pathlib import Path
from typing import Any, TypedDict


class _DeleteDirResult(TypedDict):
    success: bool
    error: str | None


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return "<unprintable>"


def _ok() -> _DeleteDirResult:
    return {"success": True, "error": None}


def _fail(message: str) -> _DeleteDirResult:
    return {"success": False, "error": message}


def delete_dir(dir_path: str, recursive: bool = False) -> _DeleteDirResult:
    """
    Удаляет каталог по указанному пути. Операция необратима.

    Args:
        dir_path: путь к каталогу (абсолютный или относительный).
        recursive: если True — удаляет каталог со всем содержимым.
                   если False — удаляет только пустой каталог;
                   при наличии содержимого вернёт ошибку.

    Returns:
        {"success": True, "error": None} при успехе,
        {"success": False, "error": "<описание>"} при ошибке.
    """
    if not isinstance(dir_path, str) or not dir_path.strip():
        return _fail("Пустой или некорректный путь")

    if not isinstance(recursive, bool):
        return _fail("recursive должен быть bool")

    try:
        # Симлинк (в т.ч. на каталог) удаляем как ссылку, не трогая цель.
        # Ни shutil.rmtree, ни Path.rmdir не работают с симлинками:
        # rmtree отказывается по документации, rmdir получает ENOTDIR от ядра.
        path = Path(dir_path)
        if path.is_symlink():
            path.unlink()
            return _ok()
        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
        return _ok()
    except FileNotFoundError:
        return _fail(f"Каталог не найден: {dir_path}")
    except NotADirectoryError:
        return _fail(f"Путь не является каталогом: {dir_path}")
    except PermissionError:
        return _fail(f"Нет прав на удаление: {dir_path}")
    except OSError as e:
        if not recursive and e.errno in (errno.ENOTEMPTY, errno.EEXIST):
            return _fail(
                f"Каталог не пуст: {dir_path}. "
                "Передай recursive=True, чтобы удалить его со всем содержимым."
            )
        return _fail(f"Ошибка при удалении: {_safe_str(e)}")
    except Exception as e:  # noqa: BLE001
        return _fail(f"Неожиданная ошибка: {_safe_str(e)}")


# Определение тула для LLM (формат function calling)
delete_dir.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.delete_dir.delete_dir",
        "description": (
            "Удаляет каталог по указанному пути. Операция необратима. "
            "Если recursive=False (по умолчанию), удалит только пустой каталог; "
            "если в каталоге есть содержимое — вернёт ошибку. "
            "Если recursive=True — удалит каталог вместе со всем содержимым. "
            "Симлинк удаляется как ссылка, цель не затрагивается, "
            "независимо от значения recursive. "
            "Используй только когда пользователь явно просит удалить каталог."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": (
                        "Полный или относительный путь к каталогу, который нужно удалить"
                    ),
                },
                "recursive": {
                    "type": "boolean",
                    "description": (
                        "Если True — удалить каталог со всем содержимым. "
                        "Если False (по умолчанию) — удалить только пустой каталог."
                    ),
                    "default": False,
                },
            },
            "required": ["dir_path"],
        },
    },
}

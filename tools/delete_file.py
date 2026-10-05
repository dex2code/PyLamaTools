from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class _DeleteResult(TypedDict):
    success: bool
    error: str | None


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return "<unprintable>"


def _ok() -> _DeleteResult:
    return {"success": True, "error": None}


def _fail(message: str) -> _DeleteResult:
    return {"success": False, "error": message}


def delete_file(file_path: str) -> _DeleteResult:
    """
    Удаляет файл по указанному пути. Операция необратима.

    Returns:
        {"success": True, "error": None} при успехе,
        {"success": False, "error": "<описание>"} при ошибке.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return _fail("Пустой или некорректный путь")

    try:
        Path(file_path).unlink()
        return _ok()
    except FileNotFoundError:
        return _fail(f"Файл не найден: {file_path}")
    except IsADirectoryError:
        return _fail(f"Путь является директорией: {file_path}")
    except PermissionError:
        return _fail(f"Нет прав на удаление: {file_path}")
    except OSError as e:
        return _fail(f"Ошибка при удалении: {_safe_str(e)}")
    except Exception as e:
        return _fail(f"Неожиданная ошибка: {_safe_str(e)}")


# Определение тула для LLM (формат function calling)
delete_file.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.delete_file.delete_file",
        "description": (
            "Удаляет файл по указанному пути. Операция необратима. "
            "Используй только когда пользователь явно просит удалить файл."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Полный или относительный путь к файлу, который нужно удалить"
                    ),
                }
            },
            "required": ["file_path"],
        },
    },
}

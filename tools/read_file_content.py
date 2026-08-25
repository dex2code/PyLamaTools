from __future__ import annotations
from loguru import logger
from typing import Dict, Optional, Any
from pathlib import Path


@logger.catch
def read_file_content(
        file_path: str,
        encoding: str = 'utf-8',
        max_bytes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Читает содержимое текстового файла с возможностью ограничения размера.

    Args:
        file_path:  Путь к файлу (абсолютный или относительный).
        encoding:   Кодировка файла (по умолчанию 'utf-8').
        max_bytes:  Максимальное количество байт для чтения (если None – читается весь файл).

    Returns:
        Словарь с полями:
            - success (bool): True, если файл успешно прочитан.
            - content (Optional[str]): Содержимое файла (при success=True).
            - size_bytes (int): Размер прочитанного содержимого в байтах.
            - error (Optional[str]): Описание ошибки (при success=False).
    """
    path_obj = Path(file_path).resolve()

    if not path_obj.exists():
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Файл '{file_path}' не существует."
        }
    if not path_obj.is_file():
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Путь '{file_path}' не является файлом."
        }

    try:
        with open(path_obj, 'r', encoding=encoding) as f:
            content = f.read(max_bytes if max_bytes is not None else -1)
    except FileNotFoundError:
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Файл '{path_obj}' не найден (возможно, он был удален или перемещен)."
        }
    except PermissionError:
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Нет прав доступа для чтения файла '{path_obj}'."
        }
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Ошибка декодирования файла '{path_obj}' (возможно, неверная кодировка или бинарный файл): {str(e)}"
        }
    except OSError as e:
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Ошибка при чтении файла '{path_obj}': {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "size_bytes": 0,
            "error": f"Неизвестная ошибка при чтении файла '{path_obj}': {str(e)}"
        }

    return {
        "success": True,
        "content": content,
        "size_bytes": len(content.encode(encoding)),
        "error": None
    }

read_file_content.tool_description = {
    "type": "function",
    "function": {
        "name": "read_file_content.read_file_content",
        "description": "Читает содержимое текстового файла. Возвращает словарь с полями: success (bool), content (строка или None), size_bytes (int), error (строка или None). Поддерживает указание кодировки (по умолчанию utf-8) и ограничение на объём чтения (max_bytes).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Путь к файлу (абсолютный или относительный)."
                },
                "encoding": {
                    "type": "string",
                    "description": "Кодировка файла. По умолчанию 'utf-8'.",
                    "default": "utf-8"
                },
                "max_bytes": {
                    "type": "integer",
                    "description": "Максимальное количество байт для чтения. Если не указано – читается весь файл.",
                    "minimum": 1
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    pass
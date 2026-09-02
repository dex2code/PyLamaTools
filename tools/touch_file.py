from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


@logger.catch(reraise=False)
def touch_file(
    directory: str,
    filename: str
) -> Dict[str, Any]:
    """
    Создает пустой файл с именем filename в каталоге directory.

    Args:
        directory:  Путь к каталогу (абсолютный или относительный).
        filename:   Имя файла.

    Returns:
        Словарь с полями:
            - success (bool): True, если файл успешно создан.
            - error (Optional[str]): Описание ошибки (при success=False).
    """
    result: dict[str, Any] = {
        "success": False,
        "error": None
    }

    file_path = Path(directory) / filename

    try:
        with open(file_path, 'x') as f:
            pass

    except FileExistsError:
        result["error"] = f"Файл '{filename}' уже существует в '{directory}'"

    except FileNotFoundError:
        result["error"] = f"Директория '{directory}' не найдена"

    except PermissionError:
        result["error"] = f"Нет прав для записи в '{directory}'"

    except IsADirectoryError:
        result["error"] = f"'{file_path}' является директорией, а не файлом"

    except OSError as e:
        result["error"] = f"Ошибка ОС: {e}"

    except Exception as e:
        result["error"] = f"Неожиданная ошибка: {e}"

    else:
        result["success"] = True

    return result

touch_file.tool_description = {
    "type": "function",
    "function": {
        "name": "touch_file.touch_file",
        "description": "Создаёт пустой файл в указанной директории. Возвращает словарь с полями: success (bool), error (строка или None)",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Путь к директории, где нужно создать файл (например, '/tmp' или './data')"
                },
                "filename": {
                    "type": "string",
                    "description": "Имя создаваемого файла (например, 'notes.txt')"
                }
            },
            "required": ["directory", "filename"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    pass
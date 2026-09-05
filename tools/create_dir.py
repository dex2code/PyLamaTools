from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


@logger.catch(reraise=False)
def create_dir(
    path: str,
    directory: str
) -> Dict[str, Any]:
    """
    Создаёт новый каталог по указанному пути.

    Аргументы:
        path (str): путь к родительской директории
        dir_name (str): имя создаваемого каталога

    Возвращает:
        dict: {
            "success": bool,
            "error": Union[None, str]  # Текст ошибки на русском языке
        }
    """
    result: dict[str, Any] = {
        "success": False,
        "error": None
    }

    if not path or not directory:
        result["error"] = "Не указаны обязательные параметры вызова функции!"
        return result

    try:
        base = Path(path).resolve()
        directory_path = base / directory
        directory_path.mkdir(parents=True, exist_ok=False)

    except FileExistsError:
        result['error'] = f"Каталог уже существует"

    except PermissionError:
        result['error'] = f"Недостаточно прав для создания каталога"

    except TypeError:
        result['error'] = f"Некорректный тип аргументов (ожидаются строки)"

    except ValueError:
        result['error'] = f"Некорректное значение аргумента (путь или имя)"

    except OSError as e:
        result['error'] = f"Ошибка операционной системы: {e}"

    except Exception as e:
        result['error'] = f"Неизвестная ошибка: {e}"

    else:
        result['success'] = True

    return result

create_dir.tool_description = {
    "type": "function",
    "function": {
        "name": "create_dir.create_dir",
        "description": "Создаёт новый каталог в указанной директории. Возвращает словарь с полями: success (bool), error (строка или None)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Путь к директории, где нужно создать новый каталог (например, '/tmp' или './data')"
                },
                "directory": {
                    "type": "string",
                    "description": "Имя создаваемого каталога (например, 'NewFolder')"
                }
            },
            "required": ["path", "directory"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    pass
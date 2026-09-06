from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


@logger.catch(reraise=False)
def create_dir(tool_path: str) -> Dict[str, Any]:
    """
    Создаёт новый каталог по указанному пути.

    Аргументы:
        tool_path (str): путь к создаваемому каталогу

    Возвращает:
        dict: {
            "success": bool,
            "error": Union[None, str]  # Текст ошибки
        }
    """
    result: dict[str, Any] = {
        "success": False,
        "error": None
    }

    if not tool_path:
        result["error"] = "Не указаны обязательные параметры вызова функции!"
        return result

    try:
        directory_path = Path(tool_path).resolve()
        directory_path.mkdir(parents=True, exist_ok=False)

    except FileExistsError:
        result['error'] = f"Каталог {directory_path} уже существует"

    except PermissionError:
        result['error'] = f"Недостаточно прав для создания каталога {directory_path}"

    except TypeError:
        result['error'] = f"Некорректный тип аргументов (ожидаются строки)"

    except ValueError:
        result['error'] = f"Некорректное значение аргумента"

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
        "description": "Создаёт новый каталог по указанному пути. "
        "Путь может быть абсолютным или относительным. "
        "Возвращает словарь с полями: success (bool), error (строка или None)",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": "Путь до создаваемого каталога "
                    "(например, '/tmp/new_dir' или './new_dir')"
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    pass
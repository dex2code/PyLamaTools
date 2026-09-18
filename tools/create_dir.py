from __future__ import annotations
from typing import Dict, Any
from pathlib import Path


def create_dir(tool_path: str) -> Dict[str, Any]:
    """
    Создаёт новый каталог по указанному пути включая промежуточные каталоги.
    Если путь уже существует — возвращает success=False с ошибкой

    Аргументы:
        tool_path (str): путь к создаваемому каталогу

    Возвращает:
        dict: {
            "success": bool,
            "error": Union[None, str]  # Текст ошибки
        }
    """
    result: Dict[str, Any] = {"success": False, "error": None}

    if not isinstance(tool_path, str):
        result["error"] = "Ошибка! tool_path должен быть непустой строкой!"
        return result
    tool_path = tool_path.strip()
    if not tool_path:
        result["error"] = "Ошибка! tool_path должен быть непустой строкой!"
        return result

    try:
        directory_path = Path(tool_path).resolve()
        directory_path.mkdir(parents=True, exist_ok=False)

    except FileExistsError:
        result["error"] = f"Путь {tool_path!r} уже существует"

    except PermissionError:
        result["error"] = f"Недостаточно прав для создания каталога {tool_path}"

    except TypeError:
        result["error"] = f"Некорректный тип аргументов (ожидаются строки)"

    except ValueError:
        result["error"] = f"Некорректное значение аргумента"

    except OSError as e:
        result["error"] = f"Ошибка операционной системы: {e}"

    except Exception as e:
        result["error"] = f"Неизвестная ошибка: {e}"

    else:
        result["success"] = True

    return result


create_dir.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.create_dir.create_dir",
        "description": "Создаёт новый каталог по указанному пути включая промежуточные каталоги. "
        "Путь может быть абсолютным или относительным. "
        "Возвращает словарь с полями: success (bool), error (строка или None)",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": "Путь до создаваемого каталога "
                    "(например, '/tmp/new_dir' или './new_dir')",
                }
            },
            "required": ["tool_path"],
            "additionalProperties": False,
        },
    },
}


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "x" / "y" / "z"

        assert create_dir(str(d))["success"] is True and d.is_dir()
        assert create_dir(str(d))["success"] is False  # exists
        assert create_dir(str(tmp))["success"] is False  # exists
        assert create_dir("")["success"] is False

    print("create_dir: OK")

from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


@logger.catch(reraise=False)
def touch_file(tool_path: str) -> Dict[str, Any]:
    """
    Создает пустой файл по пути tool_path.

    Args:
        tool_path:  Путь к файлу (абсолютный или относительный).

    Returns:
        Словарь с полями:
            - success (bool): True, если файл успешно создан.
            - error (Optional[str]): Описание ошибки (при success=False).
    """
    result: dict[str, Any] = {
        "success": False,
        "error": None
    }

    # Проверка пути до файла
    if not isinstance(tool_path, str) or not tool_path.strip():
        result["error"] = "Ошибка! tool_path должен быть непустой строкой!"
        return result

    try:
        file_path = Path(tool_path).resolve()

        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and file_path.is_dir():
            result["error"] = f"'{tool_path}' является директорией, а не файлом"
            return result

        file_path.touch(exist_ok=False)

    except FileExistsError:
        result["error"] = f"Файл '{tool_path}' уже существует!"

    except FileNotFoundError:
        result["error"] = f"Путь к файлу '{tool_path}' не существует!"

    except PermissionError:
        result["error"] = f"Нет прав для создания в '{tool_path}'"

    except IsADirectoryError:
        result["error"] = f"'{tool_path}' является директорией, а не файлом"

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
        "description": (
            "Создаёт ПУСТОЙ файл по указанному пути. "
            "Родительские каталоги создаются автоматически при необходимости. "
            "Если файл уже существует — success=False. "
            "Если tool_path указывает на директорию — success=False. "
            "Для записи данных используйте write_file. "
            "Возвращает словарь с полями: success (bool), error (строка или None)"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": (
                        "Путь до создаваемого файла "
                        "(например, '/tmp/new_file' или './data/new_file')"
                    ),
                }
            },
            "required": ["tool_path"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a" / "b" / "c.txt"

        assert touch_file(str(f))["success"] is True
        assert f.is_file() and f.stat().st_size == 0

        assert touch_file(str(f))["success"] is False                      # exists
        assert touch_file(str(tmp))["success"] is False                    # is_dir
        assert touch_file("")["success"] is False

    print("touch_file: OK")
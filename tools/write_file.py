from __future__ import annotations
from loguru import logger
from pathlib import Path
from typing import Dict, Any
import codecs


@logger.catch(reraise=False)
def write_file(tool_path: str,
               data: str,
               overwrite: bool = True,
               encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Записывает полученные данные в файл.
    Дописывает данные в конец файла или перезаписывает файл целиком.

    Аргументы:
        tool_path (str): путь к целевому файлу
        data (str): данные для записи в файл
        overwrite (bool): перезаписать файл целиком или дописать в конец?
        encoding (str): кодировка файла

    Возвращает:
        dict: {
            "success": bool,
            "error": Union[None, str]  # Текст ошибки
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "error": None
    }

    # Проверка пути до файла
    if not isinstance(tool_path, str) or not tool_path.strip():
        result["error"] = "Ошибка! tool_path должен быть непустой строкой!"
        return result

    # Проверка типа полученных данных
    if not isinstance(data, str):
        result['error'] = "Ошибка! Данные должны быть str!"
        return result

    if not isinstance(overwrite, bool):
        result['error'] = "Ошибка! overwrite должен быть bool!"
        return result

    # Проверка кодировки
    if not isinstance(encoding, str):
        result['error'] = "Ошибка! encoding должен быть строкой!"
        return result
    try:
        codecs.lookup(encoding)
    except LookupError:
        result['error'] = f"Ошибка! Неизвестная кодировка: '{encoding}'"
        return result

    file_path = None
    try:
        # Приводим путь к Path
        file_path = Path(tool_path).resolve()

        # Проверка, что путь не является директорией
        if file_path.exists() and file_path.is_dir():
            result['error'] = f"Ошибка! '{file_path}' является директорией, а не файлом"
            return result

        # Создаём родительские директории при необходимости
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Определяем режим открытия
        mode = "w" if overwrite else "a"
        with open(file_path, mode, encoding=encoding) as f:
            f.write(data)

    except FileNotFoundError as e:
        result['error'] = f"Ошибка! Файл или путь не найден: {e}"

    except PermissionError as e:
        result['error'] = f"Ошибка! Нет прав доступа: {e}"

    except IsADirectoryError as e:
        result['error'] = f"Ошибка! Указан путь к директории: {e}"

    except NotADirectoryError as e:
        result['error'] = f"Ошибка! Часть пути не является директорией: {e}"

    except UnicodeEncodeError as e:
        result['error'] = f"Ошибка! Проблема с кодировкой '{encoding}': {e}"

    except OSError as e:
        result['error'] = f"Ошибка ОС! {e}"

    except TypeError as e:
        result['error'] = f"Ошибка типа! {e}"

    except Exception as e:
        result['error'] = f"Непредвиденная ошибка! {e}"

    else:
        result['success'] = True

    return result

write_file.tool_description = {
    "type": "function",
    "function": {
        "name": "write_file.write_file",
        "description": (
            "Записывает данные в файл. "
            "Если overwrite=True — перезаписывает целиком, если False — дописывает в конец. "
            "Родительские каталоги создаются автоматически при необходимости. "
            "Возвращает словарь с полями: success (bool), error (строка или None)"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": "Путь до файла (например, '/tmp/new_file' или './data/new_file')"
                },
                "data": {
                    "type": "string",
                    "description": "Данные для записи в файл. Должны быть строкой."
                },
                "overwrite": {
                    "type": "boolean",
                    "description": (
                        "Флаг для определения режима открытия файла. "
                        "Если True - файл полностью перезаписывается новыми данными. "
                        "Если False - данные дописываются в конец файла."
                    )
                },
                "encoding": {
                    "type": "string",
                    "description": "Кодировка файла на диске (используется в open()). "
                    "По умолчанию utf-8."
                }
            },
            "required": ["tool_path", "data"],
            "additionalProperties": False
        }
    }
}


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a" / "b" / "c.txt"

        assert write_file(str(f), "hi")["success"] is True
        assert f.read_text("utf-8") == "hi"

        assert write_file(str(f), "!", overwrite=False)["success"] is True
        assert f.read_text("utf-8") == "hi!"

        assert write_file(str(f), "new", overwrite=True)["success"] is True
        assert f.read_text("utf-8") == "new"

        assert write_file(str(tmp), "x")["success"] is False               # is_dir
        assert write_file("", "x")["success"] is False                     # tool_path
        assert write_file(str(f), "x", encoding="cp9999")["success"] is False
        assert write_file(str(f), "😀", encoding="ascii")["success"] is False

    print("write_file: OK")

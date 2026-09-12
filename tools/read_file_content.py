from __future__ import annotations
from loguru import logger
from typing import Dict, Optional, Any
from pathlib import Path
import codecs


@logger.catch(reraise=False)
def read_file_content(tool_path: str,
                      encoding: str = 'utf-8',
                      max_chars: Optional[int] = None) -> Dict[str, Any]:
    """
    Читает содержимое текстового файла с возможностью ограничения размера.

    Args:
        tool_path:  Путь к файлу (абсолютный или относительный).
        encoding:   Кодировка файла (по умолчанию 'utf-8').
        max_chars:  Максимальное количество символов для чтения (если None – читается весь файл).

    Returns:
        Словарь с полями:
            - success (bool): True, если файл успешно прочитан.
            - file_path (str): Путь к файлу (абсолютный или относительный). 
            - content (Optional[str]): Содержимое файла (при success=True).
            - size_chars (int): Размер прочитанного содержимого в символах.
            - error (Optional[str]): Описание ошибки (при success=False).
    """
    result = {
        "success": False,
        "file_path": f"{tool_path}",
        "content": None,
        "size_chars": 0,
        "error": None
    }

    # Проверка пути до файла
    if not isinstance(tool_path, str) or not tool_path.strip():
        result['error'] = "Ошибка! tool_path должен быть непустой строкой!"
        return result

    # Проверка кодировки
    if not isinstance(encoding, str):
        result['error'] = "Ошибка! encoding должен быть строкой!"
        return result
    try:
        codecs.lookup(encoding)
    except LookupError:
        result['error'] = f"Неизвестная кодировка: '{encoding}'"
        return result

    # Проверка max_chars до try
    if max_chars is not None:
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
            result['error'] = "max_chars должен быть положительным целым или None"
            return result

    path_obj = None
    try:
        path_obj = Path(tool_path).resolve()

        if not path_obj.exists() or not path_obj.is_file():
            result['error'] = f"Файл '{path_obj}' не существует или не является файлом."
            return result

        with open(path_obj, 'r', encoding=encoding) as f:
            if max_chars is None:
                content = f.read()
            else:
                content = f.read(max_chars)

    except FileNotFoundError:
        result['error'] = f"Файл '{tool_path}' не найден (возможно, он был удален или перемещен)."

    except PermissionError:
        result['error'] = f"Нет прав доступа для чтения файла '{tool_path}'."
        
    except UnicodeDecodeError as e:
        result['error'] = (f"Ошибка декодирования файла '{tool_path}' "
                           f"(возможно, неверная кодировка или бинарный файл): {e}")

    except OSError as e:
        result['error'] = f"Ошибка при чтении файла '{tool_path}': {e}"

    except Exception as e:
        result['error'] =  f"Неизвестная ошибка при чтении файла '{tool_path}': {e}"

    else:
        result['success'] = True
        result['file_path'] = f"{path_obj}"
        result['content'] = content
        result['size_chars'] = len(content)

    return result

read_file_content.tool_description = {
    "type": "function",
    "function": {
        "name": "read_file_content.read_file_content",
        "description": "Читает содержимое текстового файла. "
        "Возвращает словарь с полями: success (bool), file_path (str), content (строка или None), "
        "size_chars (int), error (строка или None). Поддерживает указание кодировки "
        "(по умолчанию utf-8) и ограничение на объём чтения в символах (max_chars).",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": "Путь к файлу (абсолютный или относительный)."
                },
                "encoding": {
                    "type": "string",
                    "description": "Кодировка файла. По умолчанию 'utf-8'.",
                    "default": "utf-8"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Максимальное количество символов для чтения. "
                    "Если не указано – читается весь файл.",
                    "minimum": 1
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
        f = Path(tmp) / "hello.txt"
        f.write_text("Привет, мир!", encoding="utf-8")

        r = read_file_content(str(f))
        assert r["success"] is True and r["content"] == "Привет, мир!"
        assert r["size_chars"] == 12 and r["file_path"] == str(f.resolve())

        r = read_file_content(str(f), max_chars=6)
        assert r["success"] is True and r["content"] == "Привет"

        fc = Path(tmp) / "win.txt"
        fc.write_bytes("Привет".encode("cp1251"))
        assert read_file_content(str(fc), encoding="cp1251")["content"] == "Привет"

        assert read_file_content("")["success"] is False
        assert read_file_content(str(f), encoding="cp9999")["success"] is False
        assert read_file_content(str(f), max_chars=True)["success"] is False
        assert read_file_content(str(f), max_chars=0)["success"] is False
        assert read_file_content(str(tmp))["success"] is False             # is_dir
        assert read_file_content(str(Path(tmp) / "nope"))["success"] is False

        (Path(tmp) / "bin.dat").write_bytes(b"\xff\xfe\x00")
        assert read_file_content(str(Path(tmp) / "bin.dat"))["success"] is False

    print("read_file_content: OK")
from __future__ import annotations
from loguru import logger
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import os
import fnmatch


@logger.catch(reraise=False)
def find_files_and_dirs(
        directory: str,
        pattern: str,
        recursive: bool = True,
        include_dirs: bool = False
        ) -> Dict[str, Any]:
    """
    Ищет файлы и, опционально, каталоги по glob-шаблону в указанной директории.

    Args:
        directory:      Путь к корневой папке (абсолютный или относительный).
        pattern:        Glob-шаблон имени файла/каталога (например, "*.txt", "data_??.csv").
        recursive:      Если True, поиск выполняется во всех вложенных подпапках.
        include_dirs:   Если True, в результаты включаются каталоги, соответствующие шаблону.

    Returns:
        Словарь с полями:
            - success (bool):           True, если поиск выполнен без критических ошибок.
            - files (List[Dict]):       список найденных объектов, каждый содержит:
                - path (str):           абсолютный путь к объекту.
                - name (str):           имя объекта (файла или каталога).
                - size_bytes (int):     размер в байтах (для каталогов – 0).
                - modified (str):       дата последнего изменения в формате ISO 8601.
                - is_dir (bool):        True для каталогов, False для файлов.
            - count (int):              общее количество найденных объектов.
            - error (Optional[str]):    сообщение об ошибке, если success=False.
    """
    base_root = Path(directory).resolve()

    if not base_root.exists():
        return {
            "success": False,
            "files": [],
            "count": 0,
            "error": f"Директория '{directory}' не существует."
        }
    if not base_root.is_dir():
        return {
            "success": False,
            "files": [],
            "count": 0,
            "error": f"Путь '{directory}' не является директорией."
        }

    result_items: List[Dict[str, Any]] = []

    try:
        for current_root, dirs, files in os.walk(base_root):
            current_root_path = Path(current_root)

            # Обработка каталогов, если include_dirs=True
            if include_dirs:
                for dir_name in dirs:
                    dir_path = current_root_path / dir_name
                    if fnmatch.fnmatch(dir_name, pattern):
                        try:
                            stat_info = dir_path.stat()
                            mtime = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                        except Exception as e:
                            continue  # Пропускаем каталог, если не удалось получить информацию о нем
                        result_items.append({
                            "path": str(dir_path.resolve()),
                            "name": dir_name,
                            "size_bytes": 0,  # Размер каталогов устанавливаем в 0
                            "modified": mtime,
                            "is_dir": True
                        })

            # Обработка файлов
            for file_name in files:
                if fnmatch.fnmatch(file_name, pattern):
                    file_path = current_root_path / file_name
                    try:
                        stat_info = file_path.stat()
                        mtime = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    except Exception as e:
                        continue  # Пропускаем файл, если не удалось получить информацию о нем
                    result_items.append({
                        "path": str(file_path.resolve()),
                        "name": file_name,
                        "size_bytes": stat_info.st_size,
                        "modified": mtime,
                        "is_dir": False
                    })

            # Останавливаем рекурсивный обход, если recursive=False
            if not recursive:
                dirs.clear()

    except Exception as e:
        return {
            "success": False,
            "files": [],
            "count": 0,
            "error": f"Во время поиска файлов произошла ошибка: {str(e)}"
        }

    return {
        "success": True,
        "files": result_items,
        "count": len(result_items),
        "error": None
    }

find_files_and_dirs.tool_description = {
    "type": "function",
    "function": {
        "name": "find_files_and_dirs.find_files_and_dirs",
        "description": "Рекурсивно или не рекурсивно ищет файлы (и опционально каталоги) в заданной директории по glob-шаблону. Возвращает структурированный словарь с полями: success (bool), files (список найденных объектов с полями path, name, size_bytes, modified, is_dir), count (int), error (строка или null). Если поиск завершается с ошибкой, success=false и error содержит описание проблемы.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Путь к корневой папке для поиска (абсолютный или относительный). Должен существовать и быть директорией."
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob-шаблон имени файла/каталога. Поддерживаются символы *, ?, [..]. Примеры: '*.txt', 'data_??.csv', 'log[0-9].log'. Регистрозависимость определяется операционной системой."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Если True, поиск выполняется во всех вложенных подпапках рекурсивно. Если False, поиск ограничивается только указанной директорией. По умолчанию True.",
                    "default": True
                },
                "include_dirs": {
                    "type": "boolean",
                    "description": "Если True, в результаты включаются каталоги, имена которых соответствуют шаблону (размер для них будет 0). Если False, возвращаются только файлы. По умолчанию False.",
                    "default": False
                }
            },
            "required": ["directory", "pattern"],
            "additionalProperties": False
        }
    }
}


if __name__ == '__main__':
    pass
from __future__ import annotations
import os
from typing import Dict, Any, List


def _walk(
    tool_path: str,
    depth: int,
    max_depth: int,
    show_hidden: bool,
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []

    try:
        with os.scandir(tool_path) as it:
            items = list(it)
        items.sort(key=lambda e: e.name.lower())
    except Exception as e:
        return [
            {
                'name': os.path.basename(tool_path.rstrip(os.sep)) or tool_path,
                'path': tool_path,
                'type': "unknown",
                'size': None,
                'error': str(e),
            }
        ]

    for entry in items:
        if not show_hidden and entry.name.startswith("."):
            continue

        entry_data = {
            'name': entry.name,
            'path': entry.path,
            'type': "unknown",
            'size': None,
            'error': None,
        }

        try:
            is_dir = entry.is_dir(follow_symlinks=False)
            is_symlink = entry.is_symlink()
            is_file = entry.is_file(follow_symlinks=False)
        except Exception as e:
            entry_data['error'] = str(e)
            entries.append(entry_data)
            continue

        if is_symlink:
            entry_data['type'] = "symlink"
            entry_data['target'] = None
            try:
                entry_data['target'] = os.readlink(entry.path)
            except OSError as e:
                entry_data['error'] = str(e)
            entries.append(entry_data)
            continue

        if is_dir:
            entry_data['type'] = "dir"
            if depth < max_depth:
                entry_data['children'] = _walk(
                    tool_path=entry.path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    show_hidden=show_hidden
                )
            else:
                entry_data['children'] = []
            entries.append(entry_data)
            continue

        if is_file:
            entry_data['type'] = "file"

            try:
                st = entry.stat(follow_symlinks=False)
            except Exception as e:
                entry_data['error'] = str(e)
                entries.append(entry_data)
                continue

            entry_data['size'] = st.st_size
            entries.append(entry_data)
            continue

        entries.append(entry_data)

    return entries


def list_dir(
    tool_path: str,
    max_depth: int = 0,
    show_hidden: bool = False,
) -> Dict[str, Any]:
    """
    Возвращает содержимое каталога в виде дерева.

    :param tool_path: путь к каталогу
    :param max_depth: максимальная глубина рекурсии
        (0 — перечислить содержимое без рекурсии)
    :param show_hidden: показывать скрытые файлы
    :return: dict с полями success, error, result
    """
    result = {
        "success": False,
        "error": None,
        "result": [],
    }

    errors = []
    if not isinstance(tool_path, str) or not tool_path:
        errors.append("Параметр 'tool_path' должен быть непустой строкой")
    elif "\0" in tool_path:
        errors.append("Параметр 'tool_path' содержит недопустимый символ")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        errors.append("Параметр 'max_depth' должен быть неотрицательным целым числом")
    if not isinstance(show_hidden, bool):
        errors.append("Параметр 'show_hidden' должен быть boolean")
    if errors:
        result["error"] = "; ".join(errors)
        return result

    if not os.path.isdir(tool_path):
        result["error"] = (
            f"Путь не существует или не является доступным каталогом: {tool_path}"
        )
        return result

    try:
        result["result"] = _walk(
            tool_path=tool_path,
            depth=0,
            max_depth=max_depth,
            show_hidden=show_hidden,
        )
        result["success"] = True
    except Exception as e:  # noqa: BLE001
        result["error"] = f"непредвиденная ошибка: {e}"
        result["success"] = False

    return result


list_dir.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.list_dir.list_dir",
        "description": (
            "Возвращает содержимое каталога в виде дерева. "
            "Ответ содержит поля: success (bool), error (str или null), result (список узлов). "
            "success=true означает, что обход выполнен без фатальной ошибки; "
            "при этом отдельные узлы могут содержать непустой error. "

            "Каждый узел — словарь со следующими полями: "
            "  - name (str): имя записи (последний компонент пути); "
            "  - path (str): путь к записи; "
            "  - type ('dir' | 'file' | 'symlink' | 'unknown'): тип записи; "
            "  - size (int | null): размер в байтах для type='file' "
            "(0 — валидный размер пустого файла); для type='dir', 'symlink' и 'unknown' — null; "
            "  - error (str | null): заполнен, если при чтении записи произошла ошибка "
            "(нет доступа, битая ссылка и т.п.). Если error не null, остальные поля "
            "могут быть неполными и им нельзя доверять. "

            "Для type='dir' дополнительно возвращается поле: "
            "  - children (list): список дочерних узлов; пустой список, если глубина "
            "исчерпана или каталог пуст. "

            "Для type='symlink' дополнительно возвращается поле: "
            "  - target (str | null): путь, на который указывает ссылка; null, "
            "если прочитать ссылку не удалось (тогда error заполнен). "
            "Симлинки НЕ разворачиваются рекурсивно — внутрь ссылки обход не заходит, "
            "что исключает бесконечную рекурсию и циклы. Симлинк на каталог "
            "возвращается как type='symlink' без поля children. "

            "type='unknown' возвращается, если запись не удалось классифицировать "
            "(например, специальный файл — сокет, FIFO, device) или не удалось "
            "прочитать её метаданные. "

            "Скрытые записи (начинающиеся с '.') пропускаются, если show_hidden=false. "
            "Параметр max_depth ограничивает глубину рекурсии: 0 — только содержимое "
            "указанного каталога без захода во вложенные."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": "Путь к каталогу (абсолютный или относительный).",
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": (
                        "Показывать скрытые файлы и каталоги (начинающиеся с '.'). "
                        "По умолчанию false."
                    ),
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": (
                        "Максимальная глубина обхода. 0 — перечислить содержимое "
                        "каталога без рекурсии. По умолчанию 0."
                    ),
                    "default": 0,
                    "minimum": 0,
                },
            },
            "required": ["tool_path"],
            "additionalProperties": False,
        },
    },
}
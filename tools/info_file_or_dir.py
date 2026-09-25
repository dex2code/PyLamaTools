from __future__ import annotations

import os
import stat as stat_mod
from datetime import datetime, timezone
from typing import Dict, Any, Union


def _ok(result: Dict) -> Dict[str, Any]:
    return {"success": True, "error": None, "result": result}


def _not_found(path: str) -> Dict[str, Any]:
    return {
        "exists": False,
        "path": path,
        "type": None,
        "size": None,
        "mtime": None,
        "is_readable": None,
        "is_writable": None,
    }

def _fail(message: str) -> Dict[str, Any]:
    return {"success": False, "error": message, "result": {}}


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return "<unprintable>"


def _classify(st: os.stat_result) -> str:
    if stat_mod.S_ISDIR(st.st_mode):
        return "dir"
    if stat_mod.S_ISREG(st.st_mode):
        return "file"
    return "other"


def _iso(ts: float) -> Union[str, None]:
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return None


def info_file_or_dir(tool_path: str) -> Dict[str, Any]:
    """
    Метаданные файла/каталога.

    Возвращает:
        {
          "success": bool,
          "error": str | None,
          "result": {
              "exists": bool,
              "path": str,
              "type": "file" | "dir" | "other" | None,
              "size": int | None,        # только для file
              "mtime": str | None,       # ISO-8601 UTC
              "is_readable": bool | None,
              "is_writable": bool | None,
          },
        }
    """
    try:
        st = os.stat(tool_path)
    except FileNotFoundError:
        return _ok(_not_found(tool_path))
    except Exception as e:
        return _fail(_safe_str(e))

    kind = _classify(st)

    return _ok({
        "exists": True,
        "path": tool_path,
        "type": kind,
        "size": st.st_size if kind == "file" else None,
        "mtime": _iso(st.st_mtime),
        "is_readable": os.access(tool_path, os.R_OK),
        "is_writable": os.access(tool_path, os.W_OK),
    })


info_file_or_dir.tool_description = {
    "type": "function",
    "function": {
        "name": "tools.info_file_or_dir.info_file_or_dir",
        "description": (
            "Возвращает метаданные файла или каталога. "
            "Используй перед чтением или записью, чтобы "
            "проверить существование файла, его тип, размер и права.\n"
            "Ответ: {success: bool, error: str | null, result: {...}}.\n"
            "- success=False означает, что проверить путь не удалось "
            "(например, нет прав); error содержит текст ошибки.\n"
            "- success=True с result.exists=False означает, что путь "
            "проверен и файла нет — это НЕ ошибка.\n"
            "\n"
            "Поля result (при exists=True):\n"
            "- path: абсолютный путь (str)\n"
            "- type: 'file' | 'dir' | 'other'\n"
            "- size: размер в байтах (int, только для type='file')\n"
            "- mtime: время последнего изменения в ISO-8601 UTC\n"
            "- is_readable, is_writable: bool"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tool_path": {
                    "type": "string",
                    "description": (
                        "Путь к файлу или каталогу."
                    ),
                },
            },
            "required": ["tool_path"],
            "additionalProperties": False,
        },
    },
}
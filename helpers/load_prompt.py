from __future__ import annotations
from pathlib import Path
from loguru import logger


class FileReadError(Exception):
    """Ошибка чтения файла для промпта.

    Объединяет все проблемы, связанные с доступом к файлу:
    не удалось разрешить путь, файл не найден, путь не является
    обычным файлом, нет прав на чтение, файл превышает лимит
    размера, ошибка декодирования и т.п.
    """


def load_prompt(
    path: str,
    project_root: Path,
    *,
    encoding: str = "utf-8",
    max_size: int = 1 * 1024 * 1024,
) -> str:
    """Прочитать файл для использования в промпте.

    Относительный ``path`` разрешается относительно ``project_root``;
    после канонизации путь должен оставаться внутри ``project_root``.
    Файлы больше ``max_size`` байт отклоняются. Содержимое декодируется
    в ``encoding``, ведущий BOM срезается.

    :param path: путь к файлу (непустой, не тримится).
    :param project_root: существующий каталог-корень проекта (``Path``).
    :param encoding: имя текстовой кодировки.
    :param max_size: максимальный размер файла в байтах (> 0).

    :raises TypeError: неверный тип ``path``, ``project_root``,
        ``encoding`` или ``max_size``.
    :raises ValueError: ``path`` пустой или состоит только из пробелов;
        ``max_size`` не положительный.
    :raises FileReadError: любая проблема с файловой системой,
        превышение ``max_size`` или ошибка декодирования.
    """
    # Проверка типа аргумента
    if not isinstance(path, str):
        raise TypeError(f"Ожидалась строка (str), получено {type(path).__name__}")

    # Пустой путь
    if not path.strip():
        raise ValueError("Путь к файлу пустой")

    # project_root должен быть Path
    if not isinstance(project_root, Path):
        raise TypeError(
            f"Ожидался Path для project_root, получено {type(project_root).__name__}"
        )

    # encoding должен быть str
    if not isinstance(encoding, str):
        raise TypeError(
            f"Ожидался str для encoding, получено {type(encoding).__name__}"
        )

    # max_size должен быть int > 0:
    if not isinstance(max_size, int) or isinstance(max_size, bool):
        raise TypeError(
            f"Ожидался int для max_size, получено {type(max_size).__name__}"
        )
    if max_size <= 0:
        raise ValueError(f"max_size должен быть больше нуля, получено {max_size}")

    # Проверяем кодировку
    try:
        b"".decode(encoding)
    except (LookupError, UnicodeDecodeError) as e:
        raise FileReadError(
            f"Неизвестная или нетекстовая кодировка {encoding!r}"
        ) from e

    # Проверяем пути
    try:
        project_root_resolved = project_root.resolve()
    except (OSError, RuntimeError, ValueError) as e:
        raise FileReadError(f"Не удалось разрешить путь {project_root!r}: {e}") from e

    if not project_root_resolved.is_dir():
        raise FileReadError(
            f"project_root не является каталогом: {project_root_resolved}"
        )

    try:
        raw_path = Path(path)
        if not raw_path.is_absolute():
            raw_path = project_root_resolved / raw_path
        resolved_path = raw_path.resolve()
    except (OSError, RuntimeError, ValueError) as e:
        raise FileReadError(f"Не удалось разрешить путь {path!r}: {e}") from e

    if not resolved_path.is_relative_to(project_root_resolved):
        raise FileReadError(f"Файл промта вне project_root: {resolved_path}")

    # Это файл, а не каталог / устройство
    if not resolved_path.is_file():
        raise FileReadError(
            f"Путь не является файлом или файл не существует: {resolved_path}"
        )

    # Чтение с явной кодировкой
    try:
        with resolved_path.open("rb") as f:
            data = f.read(max_size + 1)
    except PermissionError as e:
        raise FileReadError(f"Доступ запрещён: {resolved_path}") from e
    except OSError as e:
        raise FileReadError(f"Ошибка ввода-вывода: {e}") from e

    if len(data) > max_size:
        raise FileReadError(
            f"Файл {resolved_path} больше ограничительного лимита {max_size} байт"
        )

    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as e:
        raise FileReadError(f"Файл {resolved_path} не в кодировке {encoding}") from e
    except LookupError as e:
        raise FileReadError(f"Кодировка {encoding!r} не является текстовой") from e

    text = text.removeprefix("\ufeff")
    if not text:
        logger.warning("Файл {} пустой.", resolved_path)

    return text

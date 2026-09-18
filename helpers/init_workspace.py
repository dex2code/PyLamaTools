from __future__ import annotations
from pathlib import Path
import tempfile


def init_workspace(project_root: Path, workspace_dir: Path) -> Path:
    """
    Создаёт рабочую директорию (если её нет) и проверяет запись в неё.

    Относительный ``workspace_dir`` разрешается относительно
    ``project_root``; cwd не участвует. Абсолютный ``workspace_dir``
    используется как есть. Итоговый путь приводится к каноническому
    виду через ``Path.resolve()`` (раскрываются симлинки и ``..``).
    Создание идемпотентно: если каталог уже существует, ошибка
    не возникает.

    Доступ на запись проверяется реальным созданием временного файла
    в каталоге — надёжнее, чем ``os.access``, поскольку учитывает
    read-only FS, квоты и монтирование.

    :param project_root: корень проекта; база для относительных путей
    :param workspace_dir: путь к рабочей директории (относительный
        или абсолютный)
    :return: канонический абсолютный путь к существующей директории,
        доступной для записи
    :raises FileExistsError: если по пути уже существует файл
        (или битый симлинк), а не директория
    :raises NotADirectoryError: если один из родителей пути —
        не директория
    :raises PermissionError: если нет прав на создание директории
        или на запись в неё
    :raises OSError: при прочих ошибках файловой системы
    """
    if not workspace_dir.is_absolute():
        workspace_dir = project_root / workspace_dir

    workspace_dir = workspace_dir.resolve()

    # Пытаемся создать (если уже создан - ок)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Проверяем доступ на запись созданием временного файла
    with tempfile.NamedTemporaryFile(dir=workspace_dir, delete=True):
        pass

    return workspace_dir

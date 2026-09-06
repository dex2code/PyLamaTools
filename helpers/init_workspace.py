from __future__ import annotations
from loguru import logger
from pathlib import Path


@logger.catch(reraise=True)
def init_workspace(workspace_path: str = "workspace") -> Path:
    """
    Подготавливает рабочую директорию.
    Возвращает абсолютный Path к существующей и доступной для записи директории.
    При ошибках выбрасывает PermissionError, NotADirectoryError, OSError.
    """
    logger.debug(" -> In function workspace.init_workspace()")

    # Разрешаем абсолютный путь до workspace
    target = Path(workspace_path).resolve()

    # Если не существует - пытаемся создать
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    # Если уже существует, но не каталог - выбрасываем исключение
    if not target.is_dir():
        raise NotADirectoryError(f"Каталог '{target}' уже существует и не является директорией!")

    # Проверяем доступ на запись созданием временного файла
    test_file = target / ".write_test"
    test_file.touch(exist_ok=True)
    test_file.unlink()

    logger.debug(" <- Out function workspace.init_workspace()")
    return target


if __name__ == "__main__":
    pass
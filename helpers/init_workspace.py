from __future__ import annotations
from loguru import logger
from pathlib import Path
import tempfile


def init_workspace(workspace_path: Path) -> Path:
    """
    Подготавливает рабочую директорию.
    Возвращает абсолютный Path к существующей и доступной для записи директории.
    При ошибках выбрасывает исключения OS.
    """
    # Базовая проверка пути
    if not str(workspace_path).strip():
        raise ValueError("workspace_path не может быть пустым")

    # Нормализуем путь и делаем его абсолютным (если он ещё не абсолютный)
    target = workspace_path.resolve()

    # Если не существует - пытаемся создать
    target.mkdir(parents=True, exist_ok=True)

    # Если уже существует, но не каталог - выбрасываем исключение
    if not target.is_dir():
        raise NotADirectoryError(f"Каталог '{target}' уже существует и не является директорией!")

    # Проверяем доступ на запись созданием временного файла
    with tempfile.NamedTemporaryFile(dir=target, delete=True):
        pass

    return target


if __name__ == "__main__":
    pass
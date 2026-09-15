from __future__ import annotations
from pathlib import Path

from loguru import logger

from helpers.validate_config import SettingsModel


def load_system_prompt(settings: SettingsModel,
                       project_root: Path) -> str:
    """
    Загружает системный промт из файла.

    Args:
        settings: Валидированная модель настроек.
        project_root: Базовый путь проекта.

    Returns:
        Содержимое файла без пробелов по краям.

    Raises:
        OSError: если файл не удаётся прочитать.
        UnicodeDecodeError: если кодировка не подходит.
        ValueError: если путь выходит за пределы project_root.
    """
    resolved_root = project_root.resolve()
    prompt_file = (resolved_root / settings.system_prompt_file).resolve()
    if not prompt_file.is_relative_to(resolved_root):
        logger.error("Файл промта вне project_root: {}", prompt_file)
        raise ValueError(f"Файл промта вне project_root: {prompt_file}")

    try:
        system_prompt = prompt_file.read_text(
            encoding=settings.system_prompt_file_encoding
        ).strip()
    except (OSError, UnicodeDecodeError):
        logger.exception("Системный промт не загружен: {}", prompt_file)
        raise

    if not system_prompt:
        logger.warning("Системный промт пуст")
    else:
        logger.debug("Системный промт загружен ({} символов)", len(system_prompt))

    return system_prompt

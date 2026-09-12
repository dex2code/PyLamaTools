from __future__ import annotations
from loguru import logger
from pathlib import Path
from helpers.validate_config import SettingsModel


def load_system_prompt(settings: SettingsModel,
                       base_dir: Path) -> str:
    """
    Загружает системный промт из файла.

    Args:
        settings: Валидированная модель настроек.
        base_dir: Базовый путь проекта.

    Returns:
        Содержимое файла без пробелов по краям.

    Raises:
        OSError: если файл не удаётся прочитать.
        UnicodeDecodeError: если кодировка не подходит.
    """

    prompt_file = base_dir / settings.system_prompt_file
    try:
        with open(prompt_file,
                  "r",
                  encoding=settings.system_prompt_file_encoding) as f:
            system_prompt = f.read()
    except (OSError, UnicodeDecodeError):
        logger.exception(f"Системный промт не загружен: '{prompt_file}'")
        raise

    logger.debug(f"Системный промт загружен ({len(system_prompt)} символов)")
    return system_prompt.strip()


if __name__ == "__main__":
    pass
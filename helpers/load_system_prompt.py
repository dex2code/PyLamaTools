from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


@logger.catch
def load_system_prompt(settings: Dict[str, Any],
                       base_dir: Path) -> str:
    """
    Загружает системный промпт из файла.

    Args:
        settings: Словарь настроек, должен содержать ключи:
            'system_prompt_file' – имя файла (относительно base_dir)
            'system_prompt_file_enc' – кодировка файла (например, 'utf-8')
        base_dir: Базовый путь.

    Returns:
        Содержимое файла с удалёнными пробелами по краям или пустую строку, если возникла ошибка.
    """
    logger.debug(f" -> In function helpers.load_system_prompt.load_system_prompt()")

    prompt_file = base_dir / settings['system_prompt_file']
    system_prompt = ""
    try:
        with open(prompt_file, "r",
                  encoding=settings["system_prompt_file_enc"]) as f:
            system_prompt = f.read()
    except Exception as e:
        logger.warning(f"Системный промт не загружен. "
                       f"Проверьте файл '{settings['system_prompt_file']}'")
    else:
        logger.debug(f"Системный промт: {system_prompt}")

    logger.debug(f" <- Out function helpers.load_system_prompt.load_system_prompt()")
    return system_prompt.strip()


if __name__ == "__main__":
    pass
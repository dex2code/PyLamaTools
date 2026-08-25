from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path


def load_system_prompt(settings: Dict[str, Any],
                       base_dir: Path) -> str:
    logger.debug(f" -> In function helpers.load_system_prompt.load_system_prompt()")

    prompt_file = base_dir / settings['system_prompt_file']
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
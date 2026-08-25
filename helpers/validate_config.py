from __future__ import annotations
from typing import Optional, Dict
from pydantic import BaseModel, ValidationError
from loguru import logger


class SettingsModel(BaseModel):
    log_level: str
    tools_dir: str
    system_prompt_file: str
    system_prompt_file_enc: str
    ollama_url: str
    ollama_model: str
    display_thinking: bool
    chat_streaming: bool
    model_thinking: bool
    options: Optional[Dict] = None


@logger.catch
def validate_config(config: dict) -> bool:
    try:
        SettingsModel.model_validate(config)
    except ValidationError:
        logger.warning("Ошибка валидации конфигурационного файла!")
        return False

    return True


if __name__ == "__main__":
    pass
from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from loguru import logger


class SettingsModel(BaseModel):
    """Модель конфигурации приложения"""
    log_level: str
    tools_dir: str
    system_prompt_file: str
    system_prompt_file_enc: str
    ollama_url: str
    ollama_model: str
    tool_iterations: int
    context_max_tokens: int
    context_encoding: str
    display_thinking: bool
    model_thinking: bool
    options: Optional[Dict] = None


@logger.catch
def validate_config(config: Dict[str, Any]) -> bool:
    """
    Проверяет, что переданный словарь соответствует схеме SettingsModel.

    Args:
        config: Словарь с настройками.

    Returns:
        True, если конфигурация валидна, иначе False.
    """
    try:
        SettingsModel.model_validate(config)
    except ValidationError as e:
        logger.error(f"Ошибка валидации конфигурационного файла! {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при валидации конфигурационного файла! {e}")
        return False

    return True


if __name__ == "__main__":
    pass

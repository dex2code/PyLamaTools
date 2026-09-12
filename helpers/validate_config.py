from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, AnyHttpUrl


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    tools_dir: str = Field(min_length=1)
    workspace_dir: str = Field(min_length=1)
    system_prompt_file: str = Field(min_length=1)
    system_prompt_file_encoding: str = Field(min_length=1)
    ollama_url: AnyHttpUrl
    ollama_model: str = Field(min_length=1)
    tool_iterations: int = Field(ge=1)
    context_max_tokens: int = Field(ge=0)
    context_encoding: Literal["cl100k_base", "o200k_base"]
    display_thinking: bool
    model_thinking: bool
    options: Optional[Dict[str, Any]] = None


def validate_config(config: Dict[str, Any]) -> SettingsModel:
    """
    Валидирует конфиг и возвращает нормализованную модель.

    Args:
        config: Словарь с настройками.

    Returns:
        SettingsModel: Валидированная модель.

    Raises:
        ValidationError: если конфиг не соответствует схеме.
    """
    return SettingsModel.model_validate(config)


if __name__ == "__main__":
    pass

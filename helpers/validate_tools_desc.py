from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict, Any, List
from loguru import logger


class ParameterProperty(BaseModel):
    """Свойство параметра функции (схема JSON Schema)."""
    type: str
    description: str
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    class Config:
        extra = 'allow'


class Parameters(BaseModel):
    type: str = Field(..., pattern=r'^object$')
    properties: Dict[str, ParameterProperty]
    required: Optional[List[str]] = None
    additionalProperties: bool = False
    class Config:
        extra = 'allow'


class Function(BaseModel):
    name: str
    description: str
    parameters: Parameters


class Tool(BaseModel):
    type: str = Field(..., pattern=r'^function$')
    function: Function


@logger.catch(reraise=True)
def validate_tool_desc(tool_dict: Dict[str, Any]) -> bool:
    """
    Загружает и валидирует описание инструмента.

    Args:
        tool_dict: Словарь, соответствующий схеме Tool.

    Returns:
        True при успехе, иначе False.
    """
    try:
        Tool.model_validate(tool_dict)
    except ValidationError as e:
        logger.error(f"Ошибка валидации описания инструмента! {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при валидации описания инструмента! {e}")
        return False

    return True


if __name__ == "__main__":
    pass

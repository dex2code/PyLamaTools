from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from loguru import logger


class ParameterProperty(BaseModel):
    """Свойство параметра функции (схема JSON Schema)."""
    model_config = ConfigDict(extra="allow")
    type: Literal["string", "number", "integer", "boolean", "array", "object"]
    description: str
    default: Any = None
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None


class Parameters(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["object"] = "object"
    properties: Dict[str, ParameterProperty]
    required: List[str] = []
    additionalProperties: bool = False


class Function(BaseModel):
    name: str
    description: str
    parameters: Parameters


class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: Function


def validate_tool_desc(tool_dict: Dict[str, Any]) -> bool:
    """
    Валидирует описание инструмента по схеме Tool.

    Args:
    tool_dict: Словарь, соответствующий схеме Tool.

    Returns:
        True при успехе, иначе False.
    """
    try:
        Tool.model_validate(tool_dict)
    except Exception as e:
        logger.error(f"Ошибка при валидации описания инструмента! {e}")
        return False

    return True


if __name__ == "__main__":
    pass

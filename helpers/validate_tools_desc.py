from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from typing import Optional, Dict, Any, List, Literal, Union
from loguru import logger


class ParameterProperty(BaseModel):
    """Свойство параметра функции (схема JSON Schema)."""
    model_config = ConfigDict(extra="allow")
    type: Literal["string", "number", "integer", "boolean", "array", "object"]
    description: str
    default: Any = Field(default=None)
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None


class Parameters(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["object"] = "object"
    properties: Dict[str, ParameterProperty]
    required: List[str] = []
    additionalProperties: Union[bool, Dict[str, Any]] = False


class Function(BaseModel):
    name: str
    description: str
    parameters: Parameters


class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: Function


def is_valid_tool_desc(tool_dict: Dict[str, Any]) -> bool:
    """
    Валидирует описание инструмента по схеме Tool.

    Args:
        tool_dict: Словарь, соответствующий схеме Tool.

    Returns:
        True при успехе, иначе False.
    """
    try:
        Tool.model_validate(tool_dict)
    except ValidationError as e:
        logger.exception("Ошибка при валидации описания инструмента!")
        return False

    return True

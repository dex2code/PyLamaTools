from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict, Any, List
from loguru import logger


class ParameterProperty(BaseModel):
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


@logger.catch
def validate_tool_desc(tool_dict: Dict) -> bool:
    try:
        Tool.model_validate(tool_dict)
    except ValidationError as e:
        logger.warning("Ошибка валидации описания инструмента!")
        return False

    return True


if __name__ == "__main__":
    pass

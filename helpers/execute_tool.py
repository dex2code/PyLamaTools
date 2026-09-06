from __future__ import annotations
from loguru import logger
from typing import Dict, Any
from pathlib import Path
import ollama
import json


@logger.catch(reraise=True)
def execute_tool(tool_call: ollama.Message.ToolCall,
                 tool_functions: Dict[str, Any],
                 workspace_dir: Path) -> str:
    """
    Выполняет вызов инструмента на основе данных от LLM.

    Args:
        tool_call: Словарь, содержащий информацию о вызове инструмента.
                   Ожидается структура: {"function": {"name": "...", "arguments": {...}}}
        tool_functions: Словарь, сопоставляющий имена функций с вызываемыми объектами.

    Returns:
        Результат выполнения инструмента в виде строки или сообщение об ошибке.
    """
    logger.debug(f" -> In function execute_tool.execute_tool()")

    # Проверяем наличие объекта "function" в tool_call
    func_info: ollama.Message.ToolCall.Function = tool_call.get("function")
    if not func_info:
        err_msg = f"Ошибка: в tool_call отсутствует объект 'function'"
        logger.error(err_msg)
        return err_msg

    # Получаем значение name вызываемой функции из объекта function и проверяем валидность
    func_name = func_info.get("name")
    if not func_name or not isinstance(func_name, str):
        err_msg = "Ошибка: в объекте 'function' отсутствует корректное имя функции 'name'"
        logger.error(err_msg)
        return err_msg

    # Проверяем, что имя функции присутствует в инструментарии
    if func_name not in tool_functions:
        err_msg = f"Ошибка: функция '{func_name}' не найдена в инструментарии!"
        logger.error(err_msg)
        return err_msg

    # Получаем аргументы функции из объекта function и проверяем валидность
    func_args = func_info.get("arguments", {})
    if isinstance(func_args, str):
        try:
            func_args = json.loads(func_args)
        except Exception as e:
            err_msg = f"Ошибка: неверный формат аргументов для {func_name}: {func_args} ({e})"
            logger.error(err_msg)
            return err_msg

    if not isinstance(func_args, dict):
        err_msg = f"Ошибка: аргументы для {func_name} должны быть Dict"
        logger.error(err_msg)
        return err_msg

    # Если в аргументах есть 'path' - проверяем на соответствие ограничения workspace_dir
    if "tool_path" in func_args:
        tool_path_str = func_args.get("tool_path", "")
        try:
            _ = Path(tool_path_str).resolve().relative_to(workspace_dir)
        except ValueError:
            err_msg = (f"Ошибка безопасности! "
                       f"Инструмент '{func_name}' пытается выйти из песочницы! "
                       f"Инструменты могут работать только в каталоге '{workspace_dir}'!")
            logger.error(err_msg)
            return err_msg

    # Вызываем функцию с аргументами
    func = tool_functions[func_name]
    try:
        func_result = func(**func_args)
    except Exception as e:
        err_msg = f"Ошибка при вызове инструмента '{func_name}': {e}"
        logger.error(err_msg)
        return err_msg

    # Пробуем преобразовать результат в строку, если нужно
    if not isinstance(func_result, str):
        try:
            func_result_dump = json.dumps(func_result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Неверный формат ответа инструмента '{func_name}': {func_result}. "
                         f"Ошибка: {e}")
            return f"Неверный формат ответа инструмента '{func_name}'!"

    logger.debug(f" <- Out function execute_tool.execute_tool()")
    return func_result_dump


if __name__ == "__main__":
    pass
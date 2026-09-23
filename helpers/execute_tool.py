from __future__ import annotations
from loguru import logger
from typing import Dict, Any, Union
from pathlib import Path
import ollama
import json


def _is_path_correct(v: str) -> bool:
    if not isinstance(v, str) or not v.strip():
        return False
    if "\x00" in v:
        return False
    return True


def _resolve_sandboxed_path(
    v: str,
    project_root: Path,
    workspace_dir: Path,
) -> Union[Path, None]:

    # Приводим tool_path к абсолютному пути относительно project_root
    tool_path = Path(v)
    if not tool_path.is_absolute():
        tool_path = project_root / tool_path

    try:
        tool_path_resolved = tool_path.resolve()
        tool_path_resolved.relative_to(workspace_dir)
    except (ValueError, OSError, RuntimeError):
        return None

    return tool_path_resolved


def execute_tool(
    tool_call: ollama.Message.ToolCall,
    tool_functions: Dict[str, Any],
    project_root: Path,
    workspace_dir: Path,
) -> str:
    """
    Выполняет вызов инструмента на основе данных от LLM.

    Args:
        tool_call: Структура вызова от модели.
        tool_functions: Реестр {имя: callable}.
        workspace_dir: Песочница; инструменты не должны выходить за её пределы.

    Returns:
        Результат инструмента в виде строки или текст ошибки. Функция
        не пробрасывает исключения наружу — любая ошибка возвращается
        строкой, чтобы модель могла её обработать.
    """
    # Проверяем наличие объекта "function" в tool_call
    func_info = getattr(tool_call, "function", None)
    if func_info is None:
        err_msg = "Ошибка: в tool_call отсутствует объект 'function'"
        logger.error(err_msg)
        return err_msg

    # Получаем значение name вызываемой функции из объекта function и проверяем валидность
    func_name = getattr(func_info, "name", None)
    if not isinstance(func_name, str) or not func_name:
        err_msg = (
            "Ошибка: в объекте 'function' отсутствует корректное имя функции 'name'"
        )
        logger.error(err_msg)
        return err_msg

    # Проверяем, что имя функции присутствует в инструментарии
    if not isinstance(tool_functions, dict):
        err_msg = "Ошибка: tool_functions должен быть словарём"
        logger.error(err_msg)
        return err_msg

    if func_name not in tool_functions:
        err_msg = f"Ошибка: функция '{func_name}' не найдена в инструментарии!"
        logger.error(err_msg)
        return err_msg

    # Получаем аргументы функции из объекта function и проверяем валидность
    func_args = getattr(func_info, "arguments", None)
    if func_args is None:
        func_args = {}
    if isinstance(func_args, str):
        try:
            func_args = json.loads(func_args)
        except Exception:
            err_msg = f"Ошибка: неверный формат аргументов для {func_name}: {func_args}"
            logger.error(err_msg)
            return err_msg

    if not isinstance(func_args, dict):
        err_msg = f"Ошибка: аргументы для {func_name} должны быть словарем."
        logger.error(err_msg)
        return err_msg

    # Если в аргументах есть '*_path' - проверяем на соответствие ограничения workspace_dir
    for arg_key, raw_arg_value in func_args.items():
        if not isinstance(arg_key, str) or not arg_key.endswith("_path"):
            continue

        if not _is_path_correct(v=raw_arg_value):
            err_msg = (
                f"Ошибка! Инструмент '{func_name}': "
                f"аргумент '{arg_key}' должен быть непустой строкой-путём "
                f"и не должен содержать NUL-байты. "
                f"Получено: {raw_arg_value!r}."
            )
            logger.error(err_msg)
            return err_msg

        arg_value = _resolve_sandboxed_path(
            v=raw_arg_value,
            project_root=project_root,
            workspace_dir=workspace_dir,
        )

        if arg_value is None:
            err_msg = (
                f"Ошибка безопасности! "
                f"Инструмент '{func_name}' пытается выйти из песочницы! "
                f"Аргумент '{arg_key}' == '{raw_arg_value}'. "
                f"Инструменты могут работать только в каталоге '{workspace_dir}'!"
            )
            logger.error(err_msg)
            return err_msg

        func_args[arg_key] = str(arg_value)

    # Вызываем функцию с аргументами
    try:
        func = tool_functions[func_name]
        if not callable(func):
            return f"Ошибка: '{func_name}' не является вызываемым объектом"
        func_result = func(**func_args)
    except Exception as e:
        err_msg = (
            f"Ошибка при вызове инструмента '{func_name}': {type(e).__name__}: {e}"
        )
        logger.exception(err_msg)
        return err_msg

    # Пробуем преобразовать результат в строку, если нужно
    if isinstance(func_result, str):
        return func_result

    try:
        return json.dumps(func_result, ensure_ascii=False, default=str)
    except Exception:
        logger.error(
            f"Неверный формат ответа инструмента '{func_name}': {func_result}"
        )
        return f"Неверный формат ответа инструмента '{func_name}'!"

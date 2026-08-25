from __future__ import annotations
from loguru import logger
from helpers.validate_tools_desc import validate_tool_desc
from typing import Dict, Any, List, Tuple
from pathlib import Path
import sys
import json
import importlib


@logger.catch
def load_tools(
        settings: Dict[str, Any],
        base_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Загружает функции-инструменты из модулей в каталоге tools_dir.

    Args:
        settings: Словарь с настройками, должен содержать ключ 'tools_dir'.
        base_dir: Базовый путь, относительно которого ищется каталог инструментов.

    Returns:
        Кортеж (tool_functions, tool_descriptions):
            - tool_functions: словарь {имя_функции: вызываемый объект}
            - tool_descriptions: список словарей с описаниями (атрибут tool_description)

    Raises:
        FileNotFoundError: если каталог инструментов не существует.
    """
    logger.debug(f" -> In function helpers.load_tools.load_tools()")

    # Собираем имена файлов *.py в каталоге утилит (settings['tools_dir'])
    tools_path = base_dir / settings['tools_dir']
    tools_dir = tools_path.name
    if not tools_path.exists() or not tools_path.is_dir():
        logger.error(f"Каталог инструментов '{tools_dir}' не найден")
        raise FileNotFoundError(f"Каталог инструментов '{tools_dir}' не найден")

    # Проверяем наличие __init__.py - нужен для импорта модулей
    init_file = tools_path / "__init__.py"
    if not init_file.exists():
        logger.warning(f"Отсутствует __init__.py в {tools_dir}, импорт может не сработать")

    # Собираем список модулей в tools_dir
    module_names = []
    for module in tools_path.glob('*.py'):
        if module.stem != "__init__":
            module_names.append(module.stem)
            logger.info(f"Найден модуль {tools_dir}.{module.stem}")

    # Собираем имена функций утилит из найденных файлов.
    tool_functions = {}
    tool_descriptions = []
    for module_name in module_names:
        # Импортируем найденный модуль
        try:
            module = importlib.import_module(f"{tools_dir}.{module_name}")
        except Exception as e:
            logger.warning(f"Не могу импортировать модуль {tools_dir}.{module_name}: "
                           f"{e}")
            continue

        # Итерируемся по атрибутам (функциям, переменным) загруженного модуля
        for module_attr in dir(module):
            # Если атрибут модуля начинается с '_' - пропускаем его
            if module_attr.startswith('_'):
                continue

            # Получаем объект атрибута модуля (саму функцию, переменную)
            module_object = getattr(module, module_attr)
            # Проверяем, что обект callable (функция) и объявлен именно в этом 
            # модуле (не импортирован в нем)
            if (callable(module_object)
                and getattr(module_object, "__module__", "") == module.__name__):
                # У функции-инструмента должен быть атрибут 
                # tool_description с правильным типом dict и правильной схемой
                tool_description = getattr(module_object, "tool_description", None)
                if (not isinstance(tool_description, dict)
                    or not validate_tool_desc(tool_description)):
                    logger.warning(f"У функции "
                                   f"{tools_dir}.{module_name}.{module_attr}() "
                                   f"неверный атрибут 'tool_description'. "
                                   f"Функция не будет использована.")
                    continue

                # Запоминаем набор функций и их описания
                tool_functions[f"{module_name}.{module_attr}"] = module_object
                tool_descriptions.append(tool_description)
                logger.info(f"Импортирована функция {module_attr} "
                            f"из модуля {tools_dir}.{module_name}")

        if not tool_functions:
            logger.warning("Не загружено ни одного инструмента! "
                           "Работа с функциями будет недоступна.")

        logger.debug(f"Список функций: {tool_functions.keys()}")
        logger.debug(f"Описания функций: \n"
                     f"{json.dumps(tool_descriptions, indent=2, ensure_ascii=False)}")

    logger.debug(f" <- Out function helpers.load_tools.load_tools()")
    return tool_functions, tool_descriptions


if __name__ == "__main__":
    pass
from __future__ import annotations
from loguru import logger
from helpers.validate_tools_desc import is_valid_tool_desc
from typing import Dict, Any, List, Tuple, Callable
from pathlib import Path
from helpers.validate_config import SettingsModel
import json
import importlib
import sys


def load_tools(
    settings: SettingsModel, project_root: Path
) -> Tuple[Dict[str, Callable], List[Dict[str, Any]]]:
    """
    Загружает функции-инструменты из модулей в каталоге settings.tools_dir.

    Каталог инструментов должен:
      - существовать;
      - содержать __init__.py (обычный пакет, не namespace);
      - находиться внутри project_root.

    project_root добавляется в sys.path (если его там ещё нет),
    чтобы importlib мог найти пакет инструментов.

    Инструментом считается атрибут модуля, который:
      - не начинается с '_';
      - является callable;
      - объявлен в самом модуле (не импортирован в него);
      - имеет атрибут tool_description — dict, проходящий
        validate_tool_desc.

    Атрибуты, не удовлетворяющие этим условиям, пропускаются;
    для невалидного tool_description пишется warning в лог.

    :param settings: валидированная модель настроек (поле tools_dir)
    :param project_root: резолвнутый (Path.resolve()) корень проекта;
        база для tools_dir и точка импорта пакета инструментов
    :return: кортеж (tool_functions, tool_descriptions):
        - tool_functions: словарь {dotted-имя: вызываемый объект},
          где dotted-имя имеет вид "<package>.<module>.<attr>"
        - tool_descriptions: список словарей-описаний; порядок
          соответствует порядку ключей в tool_functions
    :raises FileNotFoundError: если каталог инструментов не существует
        или в нём отсутствует __init__.py
    :raises ValueError: если каталог инструментов выходит за пределы
        project_root
    """
    # Проверяем tools_dir
    project_root = project_root.resolve()
    tools_dir = (project_root / settings.tools_dir).resolve()

    if not tools_dir.is_dir():
        raise FileNotFoundError(f"Каталог инструментов '{tools_dir}' не найден")

    # Проверяем наличие __init__.py - нужен для импорта модулей
    init_file = tools_dir / "__init__.py"
    if not init_file.is_file():
        raise FileNotFoundError(
            f"Отсутствует __init__.py в {tools_dir}, импорт может не сработать"
        )

    # Формируем dotted-имя пакета инструментов
    try:
        relative = tools_dir.relative_to(project_root)
        if not relative.parts:
            raise ValueError("tools_dir не может совпадать с project_root")
        package_name = ".".join(relative.parts)
    except ValueError as e:
        raise ValueError(
            f"Каталог инструментов '{tools_dir}' должен находиться "
            f"внутри project_root '{project_root}'"
        ) from e

    # Чтобы importlib нашёл пакет, project_root должен быть в sys.path.
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    tool_functions: Dict[str, Callable] = {}
    tool_descriptions: List[Dict[str, Any]] = []

    for module_file in sorted(tools_dir.glob("*.py")):
        module_name = module_file.stem
        if module_name == "__init__":
            continue

        module_name = f"{package_name}.{module_name}"
        logger.info(f"Найден модуль {module_name}")

        try:
            module = importlib.import_module(module_name)
        except ImportError:
            logger.exception(f"Не могу импортировать модуль '{module_name}'")
            continue
        except SyntaxError:
            logger.exception(f"Синтаксическая ошибка в '{module_name}'")
            continue
        except Exception:
            logger.exception(f"Неожиданная ошибка в '{module_name}'")
            continue

        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue

            module_attr = getattr(module, attr_name)

            if not callable(module_attr):
                continue
            if getattr(module_attr, "__module__", "") != module.__name__:
                continue

            module_desc = getattr(module_attr, "tool_description", None)
            if not isinstance(module_desc, dict) or not is_valid_tool_desc(module_desc):
                logger.warning(
                    f"У функции {module_name}.{attr_name}() неверный "
                    f"атрибут 'tool_description'. Функция не будет использована."
                )
                continue

            tool_functions[f"{module_name}.{attr_name}"] = module_attr
            tool_descriptions.append(module_desc)

            logger.info(f"Импортирована функция {attr_name} из модуля {module_name}")

    if not tool_functions:
        logger.warning(
            "Не загружено ни одного инструмента! "
            "Работа с функциями будет недоступна."
        )

    logger.debug(f"Список функций: {tool_functions.keys()}")
    logger.debug(
        f"Описания функций: \n"
        f"{json.dumps(tool_descriptions, indent=2, ensure_ascii=False)}"
    )

    return tool_functions, tool_descriptions

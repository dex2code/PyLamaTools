from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, List

import colorama
import platform
import ollama
from loguru import logger
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

from config import settings as raw_settings
from chat_model import chat_model
from helpers.parse_args import parse_args
from helpers.cut_messages import count_tokens, count_messages_tokens
from helpers.get_ollama_client import get_ollama_client
from helpers.init_workspace import init_workspace
from helpers.load_prompt import load_prompt
from helpers.load_tools import load_tools
from helpers.validate_config import SettingsModel, validate_config


def main(
    settings: SettingsModel,
    ollama_client: ollama.Client,
    messages: List[Dict[str, Any]],
    tool_descriptions: List[Dict[str, Any]],
    tool_functions: Dict[str, Any],
    project_root: Path,
    workspace_dir: Path,
    initial_prompt: str = "",
    quit_after_prompt: bool = False,
) -> None:
    # Входим в цикл чата
    while True:
        try:
            user_input = prompt(
                message="\n👤 Вы: ",
                style=Style.from_dict({"prompt": "ansiyellow"}),
                multiline=bool(initial_prompt),
                default=initial_prompt,
                accept_default=bool(initial_prompt),
            )
        except EOFError:
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "выход"):
            break
        if cmd == "reset":
            del messages[1:]
            print(f"🧹 {colorama.Fore.LIGHTRED_EX}Контекст очищен!{colorama.Style.RESET_ALL}")
            context_tokens = count_messages_tokens(messages, settings.context_encoding)
            print(
                f"{colorama.Style.DIM}"
                f"📏 Размер контекста: {context_tokens} токенов"
                f"{colorama.Style.RESET_ALL}",
                flush=True,
            )
            continue

        # Делаем копию контекста для восстановления, если что-то пошло не так
        messages_before = copy.deepcopy(messages)
        try:
            # Добавляем в контекст вопрос пользователя
            messages.append({"role": "user", "content": user_input})
            # Вызываем модель с обновленным контекстом
            messages = chat_model(
                settings=settings,
                messages=messages,
                ollama_client=ollama_client,
                tool_descriptions=tool_descriptions,
                tool_functions=tool_functions,
                project_root=project_root,
                workspace_dir=workspace_dir,
            )
        except Exception:
            logger.exception("🔴 Ошибка взаимодействия с моделью. Контекст был очищен.")
            messages = messages_before
            continue

        user_input = ""
        initial_prompt = ""

        if quit_after_prompt:
            break


if __name__ == "__main__":
    if platform.system() == "Windows":
        colorama.just_fix_windows_console()
        colorama.init(autoreset=True, convert=True)
    else:
        colorama.init(autoreset=True)

    logger.remove()
    logger.add(sys.stderr, level="WARNING")  # Временный, до валидации конфига

    # Парсим и читаем аргументы командной строки
    try:
        args = parse_args()
        if args.ollama_model:
            raw_settings["ollama_model"] = args.ollama_model
    except Exception:
        logger.exception("Ошибка парсинга аргументов командной строки")
        sys.exit(1)

    # Валидируем конфиг
    try:
        settings = validate_config(raw_settings=raw_settings)
    except Exception:
        logger.exception("Ошибка валидации конфига!")
        sys.exit(1)

    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)

    init_stage = "init_workspace"
    try:
        # Фиксируем корень проекта
        project_root = Path(__file__).resolve().parent

        # Пытаемся инициализировать workspace
        workspace_dir = init_workspace(
            project_root=project_root, workspace_dir=Path(settings.workspace_dir)
        )

        # Получаем инструменты и их описания
        init_stage = "load_tools"
        tool_functions, tool_descriptions = load_tools(
            settings=settings, project_root=project_root
        )

        # Загружаем системный промт
        init_stage = "load_system_prompt"
        system_prompt = load_prompt(path=settings.system_prompt_file, project_root=project_root)
        system_prompt_tokens = count_tokens(
            text=system_prompt, encoding_name=settings.context_encoding
        )

        # Инициализируем пустой контекст сообщений
        init_stage = "init_messages"
        messages: List[Dict[str, Any]] = []
        # Добавляем в контекст системный промт
        messages.append({"role": "system", "content": system_prompt})

        # Пытаемся загрузить промты из аргументов командной строки
        init_stage = "load_user_prompt"
        initial_prompt = args.prompt.strip()
        if args.prompt_file:
            initial_prompt = load_prompt(
                path=args.prompt_file, project_root=project_root
            )

        # Подключаемся к Ollama API и получаем клиента
        init_stage = "get_ollama_client"
        ollama_client = get_ollama_client(settings=settings)
    except Exception:
        logger.exception("Ошибка инициализации окружения (этап {})", init_stage)
        sys.exit(1)

    print(f"\n✅ {colorama.Fore.GREEN}Инициализация завершена:")

    print(
        f"🔧 {colorama.Style.DIM}"
        f"Инструментов: {len(tool_descriptions)}"
        f"{colorama.Style.RESET_ALL}"
    )

    print(
        f"🚧 {colorama.Style.DIM}"
        f"Песочница: '{workspace_dir}'"
        f"{colorama.Style.RESET_ALL}"
    )

    print(
        f"🔌 {colorama.Style.DIM}"
        f"API: '{settings.ollama_url}'"
        f"{colorama.Style.RESET_ALL}"
    )

    print(
        f"🧠 {colorama.Style.DIM}"
        f"Модель: '{settings.ollama_model}'"
        f"{colorama.Style.RESET_ALL}"
    )

    print(
        f"📏 {colorama.Style.DIM}"
        f"Ограничение контекста (токенов): {settings.context_max_tokens or '♾️'}"
        f"{colorama.Style.RESET_ALL}"
    )

    print(
        f"📜 {colorama.Style.DIM}"
        f"Системный промт (токенов): {system_prompt_tokens}"
        f"{colorama.Style.RESET_ALL}"
    )

    # Печатаем welcome message, если у нас интерактивный режим
    welcome_msg = (
        f"{colorama.Style.RESET_ALL}"
        "✨ Этот чат работает с языковой моделью, которая умеет выполнять полезные действия.\n"
        "   Инструментарий находится в каталоге tools и вы можете расширять его самостоятельно.\n\n"

        f"ℹ️  {colorama.Fore.LIGHTCYAN_EX}"
        "https://github.com/dex2code/PyLamaTools"
        f"{colorama.Style.RESET_ALL}\n\n"

        "❓ Чтобы узнать, что умеет модель - спросите: "
        f"'{colorama.Fore.LIGHTYELLOW_EX}Что ты умеешь?{colorama.Style.RESET_ALL}'.\n"
        "🚪 Если хотите закончить — напишите "
        f"'{colorama.Fore.LIGHTYELLOW_EX}exit{colorama.Style.RESET_ALL}' "
        f"или '{colorama.Fore.LIGHTYELLOW_EX}выход{colorama.Style.RESET_ALL}'.\n"
        "🧹 Для очистки контекста используйте команду "
        f"'{colorama.Fore.LIGHTYELLOW_EX}reset{colorama.Style.RESET_ALL}'."
    )
    if not initial_prompt:
        print()
        print(colorama.Fore.LIGHTWHITE_EX + welcome_msg)

    # Исполняем главную функцию с отслеживанием Ctrl+C
    try:
        main(
            settings=settings,
            ollama_client=ollama_client,
            messages=messages,
            tool_descriptions=tool_descriptions,
            tool_functions=tool_functions,
            project_root=project_root,
            workspace_dir=workspace_dir,
            initial_prompt=initial_prompt,
            quit_after_prompt=args.quit_after_prompt,
        )
    except KeyboardInterrupt:
        logger.warning("Выполнение прервано по KeyboardInterrupt")
        sys.exit(130)
    except Exception:
        logger.exception("Неожиданная ошибка!")
        sys.exit(1)

    sys.exit(0)

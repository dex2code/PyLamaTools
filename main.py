from __future__ import annotations
from config import settings as raw_settings
from pathlib import Path
from loguru import logger
from helpers.validate_config import validate_config, SettingsModel
from helpers.init_workspace import init_workspace
from helpers.load_tools import load_tools
from helpers.load_system_prompt import load_system_prompt
from helpers.get_ollama_client import get_ollama_client
from chat_model import chat_model
from helpers.cut_messages import count_tokens
from typing import List, Dict, Any
import colorama
import sys
import ollama


def main(settings: SettingsModel,
         system_prompt: str,
         ollama_client: ollama.Client,
         tool_descriptions: List[Dict[str, Any]],
         tool_functions: Dict[str, Any],
         workspace_dir: Path) -> None:
    welcome_msg = (
        "✨ Этот чат работает с языковой моделью, которая умеет выполнять полезные действия: "
        "инструментарий находится в каталоге tools и вы можете расширять его самостоятельно.\n"
        "Просто задайте вопрос на русском языке — например, «Какая сейчас погода?». "
        "Модель сама решит, когда нужно вызвать инструмент и ответит полученным значением.\n"
        "Чтобы узнать, что умеет модель - спросите: \"Что ты умеешь?\". "
        "Если хотите закончить — напишите 'exit' или 'выход'."
    )
    print(welcome_msg)

    # Инициализируем пустой контекст сообщений
    messages: List[Dict[str, Any]] = []
    # Добавляем в контекст системный промт
    messages.append(
        {
            "role": "system",
            "content": system_prompt
        }
    )

    # Входим в цикл чата
    while True:
        try:
            user_input = input(f"\n👤 {colorama.Fore.YELLOW}Вы{colorama.Fore.WHITE}: ")
        except EOFError:
            break

        user_input = user_input.strip()
        if user_input.lower() in ("exit", "выход"):
            break
        if not user_input:
            continue

        messages_before = list(messages)
        try:
            # Добавляем в контекст вопрос пользователя
            messages.append(
                {
                    "role": "user",
                    "content": user_input
                }
            )

            # Вызываем обработчик чата
            messages = chat_model(settings=settings,
                                  messages=messages,
                                  ollama_client=ollama_client,
                                  tool_descriptions=tool_descriptions,
                                  tool_functions=tool_functions,
                                  workspace_dir=workspace_dir)
        except Exception:
            logger.exception("🔴 Ошибка взаимодействия с моделью. Контекст был очищен.")
            messages = messages_before
            continue
        

if __name__ == "__main__":
    colorama.init(autoreset=True)
    logger.remove()
    logger.add(sys.stderr, level="WARNING") # Временный, до валидации конфига

    # Валидируем конфиг
    try:
        settings = validate_config(raw_settings)
    except Exception:
        logger.exception("Ошибка валидации конфига!")
        sys.exit(1)

    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)

    try:
        # Фиксируем корень проекта
        base_dir = Path(__file__).resolve().parent

        # Пытаемся инициализировать workspace
        workspace_path = Path(settings.workspace_dir)
        if not workspace_path.is_absolute():
            workspace_path = base_dir / workspace_path
        workspace_dir = init_workspace(workspace_path=workspace_path)

        # Получаем инструменты и их описания
        tools_functions, tool_descriptions = load_tools(settings=settings,
                                                        base_dir=base_dir)

        # Загружаем системный промт
        system_prompt = load_system_prompt(settings=settings,
                                           base_dir=base_dir)
        if not system_prompt:
            raise ValueError("Ошибка загрузки системного промта - пустая строка!")
        system_prompt_tokens = count_tokens(text=system_prompt,
                                            encoding_name=settings.context_encoding)

        # Подключаемся к Ollama API и получаем клиента
        ollama_client = get_ollama_client(settings=settings)
    except Exception:
        logger.exception("Ошибка инициализации окружения!")
        sys.exit(1)

    print(f"\n{colorama.Fore.GREEN}✅ Инициализация завершена:")
    print(f"  🤖 {colorama.Style.DIM}Инструментов: {len(tool_descriptions)}")
    print(f"  🛑 {colorama.Style.DIM}Песочница: '{workspace_dir}'")
    print(f"  🤝 {colorama.Style.DIM}API: '{settings.ollama_url}'")
    print(f"  🧠 {colorama.Style.DIM}Модель: '{settings.ollama_model}'")
    print(f"  💬 {colorama.Style.DIM}Системный промт (токенов): {system_prompt_tokens}")
    print()

    # Исполняем главную функцию с отслеживанием Ctrl+C
    try:
        main(settings=settings,
             system_prompt=system_prompt,
             ollama_client=ollama_client,
             tool_descriptions=tool_descriptions,
             tool_functions=tools_functions,
             workspace_dir=workspace_dir)
    except KeyboardInterrupt:
        print()
        logger.warning("Выполнение прервано по KeyboardInterrupt")
        sys.exit(130)
    except Exception:
        print()
        logger.exception("Неожиданная ошибка!")
        sys.exit(1)

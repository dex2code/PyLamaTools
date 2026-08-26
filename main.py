from __future__ import annotations
from config import settings
from pathlib import Path
from loguru import logger
from helpers.validate_config import validate_config
from helpers.load_tools import load_tools
from helpers.load_system_prompt import load_system_prompt
from helpers.get_ollama_client import get_ollama_client
from chat_model import chat_model
from cut_messages import truncate_by_tokens
from typing import List, Dict, Any
import colorama
import sys
import json
import ollama


@logger.catch
def main(system_prompt: str,
         ollama_client: ollama.Client,
         tool_descriptions: List[Dict[str, Any]],
         tool_functions: Dict[str, Any]) -> None:
    welcome_msg = (
        f"✨ Этот чат работает с языковой моделью, которая умеет выполнять полезные действия: "
        f"инструментарий находится в каталоге tools и вы можете расширять его самостоятельно.\n"
        f"Просто задайте вопрос на русском языке — например, «Какая погода в Москве?». "
        f"Модель сама решит, когда нужно вызвать инструмент и ответит полученным значением.\n"
        f"Чтобы узнать, что умеет модель - спросите: \"Что ты умеешь?\". "
        f"Если хотите закончить — напишите 'exit' или 'выход'."
    )
    print(welcome_msg)

    # Инициализируем пустой контекст сообщений
    messages: List[Dict[str, Any]] = []
    # Добавляем в контекст системный промт
    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt
            }
        )

    # Входим в цикл чата
    while True:
        user_input = input(f"\n👤 {colorama.Fore.YELLOW}Вы{colorama.Fore.WHITE}: ")
        if user_input.lower() in ("exit", "выход"):
            break

        if not user_input:
            continue

        # Добавляем в контекст вопрос пользователя
        messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )
        messages = truncate_by_tokens(messages=messages,
                                      max_tokens=settings['context_max_tokens'],
                                      encoding_name=settings['context_encoding'])
        logger.debug(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")

        try:
            # Вызываем обработчик чата
            messages = chat_model(messages=messages,
                                  ollama_client=ollama_client,
                                  tool_descriptions=tool_descriptions,
                                  tool_functions=tool_functions)
        except Exception as e:
            logger.error(f"Ошибка взаимодействия с моделью: {e}")
            if messages and messages[-1]["role"] == "user":
                messages.pop()
            continue

        logger.debug(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")
        

if __name__ == "__main__":
    # Устанавливаем логгер и цветной вывод stdout
    logger.remove()
    logger.add(sys.stdout, level=settings.get("log_level", "WARNING"))
    colorama.init(autoreset=True)

    # Проверяем конфиг
    if not validate_config(settings):
        logger.critical(f"Ошибка валидации конфига приложения!")
        sys.exit(1)

    # Фиксируем корень проекта
    base_dir = Path(__file__).parent

    try:
        # Получаем инструменты и их описания
        tools_functions, tool_descriptions = load_tools(settings=settings, base_dir=base_dir)

        # Загружаем системный промт
        system_prompt = load_system_prompt(settings=settings, base_dir=base_dir)

        # Подключаемся к Ollama API и получаем клиента
        ollama_client = get_ollama_client(settings=settings)
    except Exception as e:
        logger.error(f"Ошибка инициализации окружения: {e}")
        sys.exit(1)

    logger.info("Инициализация завершена!")
    print(f"\n{colorama.Fore.GREEN}✅ Инициализация завершена:")
    print(f"  🤖 {colorama.Style.DIM}Инструментов: {len(tool_descriptions)}")
    print(f"  🤝 {colorama.Style.DIM}API: {settings['ollama_url']}")
    print(f"  🧠 {colorama.Style.DIM}Модель: {settings['ollama_model']}")
    print(f"  💬 {colorama.Style.DIM}Системный промт (символов): {len(system_prompt)}")
    print()

    # Исполняем главную функцию с отслеживанием Ctrl+C
    try:
        main(system_prompt=system_prompt,
             ollama_client=ollama_client,
             tool_descriptions=tool_descriptions,
             tool_functions=tools_functions)
    except KeyboardInterrupt:
        print()
        logger.warning("Выполнение прервано по KeyboardInterrupt Exception")
    except Exception as e:
        print()
        logger.error(f"Неожиданная ошибка: {e}")

    print("\n🚪 Выход\n")

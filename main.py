from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, List

import colorama
import ollama
from loguru import logger

from chat_model import chat_model
from config import settings as raw_settings
from helpers.cut_messages import count_tokens
from helpers.get_ollama_client import get_ollama_client
from helpers.init_workspace import init_workspace
from helpers.load_system_prompt import load_system_prompt
from helpers.load_tools import load_tools
from helpers.validate_config import SettingsModel, validate_config


def main(settings: SettingsModel,
         system_prompt: str,
         ollama_client: ollama.Client,
         tool_descriptions: List[Dict[str, Any]],
         tool_functions: Dict[str, Any],
         project_root: Path,
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
            user_input = input(f"\n👤 {colorama.Fore.YELLOW}Вы{colorama.Style.RESET_ALL}: ")
        except EOFError:
            break

        user_input = user_input.strip()
        if user_input.lower() in ("exit", "выход"):
            break
        if not user_input:
            continue

        # Делаем копию контекста для восстановления, если что-то пошло не так
        messages_before = copy.deepcopy(messages)
        try:
            # Добавляем в контекст вопрос пользователя
            messages.append(
                {
                    "role": "user",
                    "content": user_input
                }
            )

            # В зависимости от флага streaming вызываем тот или иной обработчик чата
            if settings.model_streaming:
                raise NotImplementedError("Streaming-режим пока не реализован")
            else:
                messages = chat_model(settings=settings,
                                      messages=messages,
                                      ollama_client=ollama_client,
                                      tool_descriptions=tool_descriptions,
                                      tool_functions=tool_functions,
                                      project_root=project_root,
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
        workspace_dir = init_workspace(project_root=project_root,
                                       workspace_dir=Path(settings.workspace_dir))
        init_stage = "load_tools"
        # Получаем инструменты и их описания
        tools_functions, tool_descriptions = load_tools(settings=settings,
                                                        project_root=project_root)

        init_stage = "load_system_prompt"
        # Загружаем системный промт
        system_prompt = load_system_prompt(settings=settings,
                                           project_root=project_root)
        init_stage = "count_tokens"
        system_prompt_tokens = count_tokens(text=system_prompt,
                                            encoding_name=settings.context_encoding)

        init_stage = "get_ollama_client"
        # Подключаемся к Ollama API и получаем клиента
        ollama_client = get_ollama_client(settings=settings)
    except Exception:
        logger.exception("Ошибка инициализации окружения (этап {})", init_stage)
        sys.exit(1)

    print(f"\n{colorama.Fore.GREEN}✅ Инициализация завершена:")

    print(f"  🤖 {colorama.Style.DIM}"
          f"Инструментов: {len(tool_descriptions)}"
          f"{colorama.Style.RESET_ALL}")

    print(f"  🛑 {colorama.Style.DIM}"
          f"Песочница: '{workspace_dir}'"
          f"{colorama.Style.RESET_ALL}")

    print(f"  🤝 {colorama.Style.DIM}"
          f"API: '{settings.ollama_url}'"
          f"{colorama.Style.RESET_ALL}")

    print(f"  🧠 {colorama.Style.DIM}"
          f"Модель: '{settings.ollama_model}'"
          f"{colorama.Style.RESET_ALL}")

    print(f"  📋 {colorama.Style.DIM}"
          f"Ограничение контекста (токенов): {settings.context_max_tokens or '♾️'}"
          f"{colorama.Style.RESET_ALL}")

    print(f"  💬 {colorama.Style.DIM}"
          f"Системный промт (токенов): {system_prompt_tokens}"
          f"{colorama.Style.RESET_ALL}")

    print()

    # Исполняем главную функцию с отслеживанием Ctrl+C
    try:
        main(settings=settings,
             system_prompt=system_prompt,
             ollama_client=ollama_client,
             tool_descriptions=tool_descriptions,
             tool_functions=tools_functions,
             project_root=project_root,
             workspace_dir=workspace_dir)
    except KeyboardInterrupt:
        logger.warning("Выполнение прервано по KeyboardInterrupt")
        sys.exit(130)
    except Exception:
        logger.exception("Неожиданная ошибка!")
        sys.exit(1)

from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger
from helpers.execute_tool import execute_tool
from helpers.cut_messages import count_messages_tokens, truncate_by_tokens
from pathlib import Path
from helpers.validate_config import SettingsModel
import colorama
import ollama

def chat_model(settings: SettingsModel,
               messages: List[Dict[str, Any]],
               ollama_client: ollama.Client,
               tool_descriptions: List[Dict[str, Any]],
               tool_functions: Dict[str, Any],
               project_root: Path,
               workspace_dir: Path) -> List[Dict[str, Any]]:
    """
    Выполняет один или несколько шагов диалога с языковой моделью через Ollama,
    обрабатывая вызовы инструментов.

    Функция циклически отправляет текущий контекст сообщений в модель. Если модель
    запрашивает вызов инструментов, функция выполняет их, добавляет результаты в
    контекст и повторяет запрос. Если модель возвращает текстовый ответ, он
    добавляется в контекст, и функция завершается. Перед каждым запросом контекст
    обрезается по максимальному количеству токенов.

    Args:
        settings (SettingsModel): Настройки приложения, включая имя модели,
            лимит итераций инструментов, максимальный размер контекста и т.д.
        messages (List[Dict[str, Any]]): Текущий список сообщений в формате чата
            (роли, content, tool_calls и т.д.).
        ollama_client (ollama.Client): Клиент для взаимодействия с Ollama API.
        tool_descriptions (List[Dict[str, Any]]): Описания доступных инструментов
            в формате, ожидаемом Ollama.
        tool_functions (Dict[str, Any]): Словарь, сопоставляющий имена инструментов
            с вызываемыми функциями.
        project_root (Path): Корневая директория проекта.
        workspace_dir (Path): Директория песочницы для выполнения инструментов.

    Returns:
        List[Dict[str, Any]]: Обновлённый список сообщений, включающий ответы
        ассистента и результаты вызовов инструментов.

    Side Effects:
        - Выводит в stdout информацию о вызовах инструментов, размышлениях модели
          и ответах ассистента.
        - Записывает отладочные сообщения через logger.
        - Может изменять состояние внешних систем через вызываемые инструменты.
    """
    assistant_nick = f"🤖 {colorama.Fore.YELLOW}{settings.ollama_model}{colorama.Style.RESET_ALL}"

    tool_iteration = 0
    while tool_iteration < settings.tool_iterations:
        tool_iteration += 1
        print("⏳ ", end="", flush=True)

        # Чистим контекст
        messages = truncate_by_tokens(messages,
                                      max_tokens=settings.context_max_tokens,
                                      encoding_name=settings.context_encoding)

        # Передаем в модель контекст чата и получаем ответ
        response_model = ollama_client.chat(
            model=settings.ollama_model,
            messages=messages,
            tools=tool_descriptions,
            think=settings.model_thinking,
            options=settings.options
        )
        logger.debug("{}", response_model)

        message_model = response_model.message
        if message_model is None:
            logger.warning("Модель вернула ответ без поля 'message'")
            break

        message_thinking = getattr(message_model, "thinking", None)
        if message_thinking and settings.display_thinking:
            print(f"{colorama.Style.DIM}{message_thinking}{colorama.Style.RESET_ALL}", flush=True)

        tool_calls = getattr(message_model, "tool_calls", None) or []
        content = getattr(message_model, "content", None) or ""

        # Если модель вернула вызов инструмента
        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [tc.model_dump() for tc in tool_calls],
                    "content": content
                }
            )
            for tool_call in tool_calls:
                print(f"\r⚙️  {colorama.Fore.LIGHTMAGENTA_EX}"
                      f"Вызов инструмента '{tool_call.function.name}' "
                      f"с аргументами {tool_call.function.arguments}"
                      f"{colorama.Style.RESET_ALL}")
                tool_result = execute_tool(tool_call=tool_call,
                                           tool_functions=tool_functions,
                                           project_root=project_root,
                                           workspace_dir=workspace_dir)
                print(f"↩️  {colorama.Fore.LIGHTCYAN_EX}"
                      f"Инструмент '{tool_call.function.name}' вернул значение: "
                      f" {tool_result}"
                      f"{colorama.Style.RESET_ALL}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_call.function.name,
                        "content": tool_result
                    }
                )
                logger.debug("{}", messages)
            continue

        # Если модель вернула ответ
        if content:
            print(f"\r{assistant_nick}: {colorama.Fore.LIGHTWHITE_EX}{content}{colorama.Style.RESET_ALL}",
                  flush=True)
            messages.append(
                {
                    "role": "assistant",
                    "content": content
                }
            )
            context_tokens = count_messages_tokens(messages, settings.context_encoding)
            print(f"   {colorama.Style.DIM}"
                  f"Размер контекста: {context_tokens} токенов"
                  f"{colorama.Style.RESET_ALL}")
            logger.debug("{}", messages)
            break

        # Если произошло непонятное и модель не вернула ничего
        logger.warning("Модель вернула пустой ответ без tool_calls")
        messages.append(
            {
                "role": "user",
                "content": "[СИСТЕМНОЕ УВЕДОМЛЕНИЕ] Модель вернула пустой ответ."
            }
        )
        break

    else:
        logger.warning(f"Достигнуто максимальное количество вызовов инструментов "
                       f"на запрос пользователя. {settings.tool_iterations=}")
        messages.append(
            {
                "role": "user",
                "content": (
                    "[СИСТЕМНОЕ УВЕДОМЛЕНИЕ] "
                    f"Достигнут лимит вызовов инструментов за один ответ "
                    f"({settings.tool_iterations}). "
                    "Учти это ограничение в следующих итерациях."
                )
            }
        )

    return messages


def chat_model_streaming(settings: SettingsModel,
                         messages: List[Dict[str, Any]],
                         ollama_client: ollama.Client,
                         tool_descriptions: List[Dict[str, Any]],
                         tool_functions: Dict[str, Any],
                         project_root: Path,
                         workspace_dir: Path) -> List[Dict[str, Any]]:
    assistant_nick = f"🤖 {colorama.Fore.YELLOW}{settings.ollama_model}{colorama.Style.RESET_ALL}"

    return messages

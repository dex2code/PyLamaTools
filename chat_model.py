from __future__ import annotations
from typing import List, Dict, Any, Literal, Iterable
from collections.abc import Iterator
from loguru import logger
from helpers.execute_tool import execute_tool
from helpers.cut_messages import count_messages_tokens, truncate_by_tokens
from pathlib import Path
from helpers.validate_config import SettingsModel
import colorama
import ollama

# Фаза вывода: "THINKING" | "TOOL_CALL" | "ANSWERING"
Phase = Literal["THINKING", "TOOL_CALL", "ANSWERING"]


def _iter_chunks(
    response: Iterator[ollama.ChatResponse] | ollama.ChatResponse,
) -> Iterable[ollama.ChatResponse]:
    """
    Нормализует ответ ollama.Client.chat:
      - stream=True  -> генератор ChatResponse
      - stream=False -> одиночный ChatResponse (оборачиваем в [response])

    Важно: ChatResponse — pydantic-модель, у неё есть __iter__,
    поэтому проверять нужно именно __next__ (т.е. Iterator), иначе
    цикл молча пойдёт по парам (поле, значение).
    """
    if isinstance(response, Iterator):
        return response
    return iter([response])


def _switch_phase(phase: Phase, new: Phase, prefix: str = "") -> Phase:
    """
    Переключает текущую фазу вывода модели и, при смене фазы, печатает
    ANSI-сброс стиля и (опционально) префикс новой фазы.

    Args:
        phase: Текущая активная фаза вывода (до переключения).
        new: Фаза, в которую нужно перейти.
        prefix: Строка-префикс для новой фазы
    Returns:
        Фаза `new`.
    """
    if phase != new:
        if prefix:
            print(colorama.Style.RESET_ALL, flush=True)
            print(prefix, end="  ", flush=True)
    return new


def chat_model(
    settings: SettingsModel,
    messages: List[Dict[str, Any]],
    ollama_client: ollama.Client,
    tool_descriptions: List[Dict[str, Any]],
    tool_functions: Dict[str, Any],
    project_root: Path,
    workspace_dir: Path,
) -> List[Dict[str, Any]]:
    """
    Запускает диалог с моделью Ollama, обрабатывая потоковый вывод,
    вызовы инструментов и формируя итоговый ответ.

    Функция управляет циклом общения с моделью: отправляет текущий контекст,
    получает ответ (в потоковом или обычном режиме), обрабатывает фазы вывода
    (размышление, вызов инструмента, ответ), выполняет инструменты при их вызове
    и добавляет результаты в историю сообщений. Цикл повторяется до тех пор,
    пока модель не вернёт финальный ответ или не будет достигнут лимит
    вызовов инструментов (`settings.tool_iterations`).

    Args:
        settings: Настройки чата, включая имя модели, параметры генерации,
            максимальное количество итераций инструментов, максимальный размер
            контекста в токенах и т.д.
        messages: Список сообщений чата (история). Функция изменяет этот список,
            добавляя ответы ассистента и результаты вызовов инструментов.
        ollama_client: Экземпляр клиента Ollama для взаимодействия с моделью.
        tool_descriptions: Список описаний инструментов в формате, ожидаемом
            моделью (для передачи в параметр `tools`).
        tool_functions: Словарь, сопоставляющий имена инструментов с их
            реализациями (функциями).
        project_root: Путь к корневой директории проекта (передаётся в
            инструменты).
        workspace_dir: Путь к рабочей директории (передаётся в инструменты).

    Returns:
        Обновлённый список сообщений `messages`, включающий все новые сообщения,
        добавленные в ходе диалога (ответы ассистента, результаты инструментов,
        системные уведомления).

    Notes:
        - Перед каждым вызовом модели контекст обрезается с помощью
          `truncate_by_tokens`, чтобы не превысить `settings.context_max_tokens`.
        - Для нормализации ответа модели (потоковый или одиночный) используется
          вспомогательная функция `_iter_chunks`.
        - Если модель возвращает вызовы инструментов, они выполняются, а их
          результаты добавляются в `messages` с ролью `"tool"`. Затем цикл
          продолжается.
        - Если модель возвращает только текстовый ответ (без вызовов
          инструментов), он добавляется в `messages` с ролью `"assistant"`,
          и цикл завершается.
        - Если достигнут лимит `settings.tool_iterations`, в `messages`
          добавляется системное уведомление, и функция завершается.
        - Функция не обрабатывает исключения, возникающие при вызове
          инструментов или клиента Ollama; они пробрасываются вызывающему коду.
    """
    # Формируем отображаемое имя ассистента для консольного вывода.
    assistant_nick = (
        f"🤖 {colorama.Fore.YELLOW}{settings.ollama_model}{colorama.Style.RESET_ALL}:"
    )

    # Счётчик итераций цикла "модель -> инструменты -> модель".
    tool_iteration = 0
    while tool_iteration < settings.tool_iterations:
        tool_iteration += 1
        print("🤔 ", end="", flush=True)

        # Чистим контекст
        messages = truncate_by_tokens(
            messages,
            max_tokens=settings.context_max_tokens,
            encoding_name=settings.context_encoding,
        )

        # Передаем в модель контекст чата и получаем ответ
        model_answer = ollama_client.chat(
            model=settings.ollama_model,
            messages=messages,
            tools=tool_descriptions,
            stream=settings.model_streaming,
            think=settings.model_thinking,
            options=settings.options,
        )

        # Накопители для потокового текста и вызовов инструментов.
        accumulated_content: str = ""
        raw_tool_calls: List[ollama.Message.ToolCall] = []
        dumped_tool_calls: List[Dict] = []
        # Предустанавливаем фазу ответа
        phase: Phase = "THINKING"

        # Разбираем потоковые чанки ответа модели.
        for chunk in _iter_chunks(model_answer):
            logger.trace(chunk)
            message = getattr(chunk, "message", None)
            if message is None:
                continue

            # Извлекаем возможные части чанка: размышление, вызовы, контент.
            thinking_chunk: str = getattr(message, "thinking", None) or ""
            tool_calls_chunk: List = getattr(message, "tool_calls", None) or []
            content_chunk: str = getattr(message, "content", None) or ""

            if thinking_chunk:
                # Переключаем фазу и печатаем размышление.
                phase = _switch_phase(phase, "THINKING", "🤔")
                print(f"{colorama.Style.DIM}{thinking_chunk}", end="", flush=True)

            if content_chunk:
                # Накапливаем и печатаем текстовый ответ.
                accumulated_content += content_chunk
                phase = _switch_phase(phase, "ANSWERING", assistant_nick)
                print(
                    f"{colorama.Fore.LIGHTWHITE_EX}{content_chunk}", end="", flush=True
                )

            if tool_calls_chunk:
                # Сохраняем вызовы инструментов в исходном и сериализованном виде.
                for tc in tool_calls_chunk:
                    raw_tool_calls.append(tc)
                    dumped_tool_calls.append(tc.model_dump(exclude_none=True))

        # Если модель вернула вызов инструмента
        if raw_tool_calls:
            phase = _switch_phase(phase, "TOOL_CALL", "⚙️")
            # Добавляем в историю ответ ассистента с вызовами инструментов.
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": dumped_tool_calls,
                    "content": accumulated_content,
                }
            )
            logger.debug("{}", messages)
            for tool_call in raw_tool_calls:
                print(
                    f"{colorama.Fore.LIGHTMAGENTA_EX}"
                    f"Вызов инструмента '{tool_call.function.name}' "
                    f"с аргументами {tool_call.function.arguments}"
                    f"{colorama.Style.RESET_ALL}",
                    flush=True,
                )
                # Выполняем вызванный инструмент.
                tool_result = execute_tool(
                    tool_call=tool_call,
                    tool_functions=tool_functions,
                    project_root=project_root,
                    workspace_dir=workspace_dir,
                )
                print(
                    f"↩️  {colorama.Fore.LIGHTCYAN_EX}"
                    f"Инструмент '{tool_call.function.name}' вернул значение: "
                    f" {tool_result}"
                    f"{colorama.Style.RESET_ALL}",
                    flush=True,
                )
                # Добавляем результат инструмента в историю.
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_call.function.name,
                        "content": tool_result,
                    }
                )
                logger.debug("{}", messages)
            continue

        # Если модель вернула ответ
        if accumulated_content:
            # Фиксируем финальный текстовый ответ ассистента.
            messages.append({"role": "assistant", "content": accumulated_content})
            logger.debug("{}", messages)
            # Считаем и показываем размер контекста после ответа.
            context_tokens = count_messages_tokens(messages, settings.context_encoding)
            print(colorama.Style.RESET_ALL, flush=True)
            print(
                f"{colorama.Style.DIM}"
                f"[ Размер контекста: {context_tokens} токенов ]"
                f"{colorama.Style.RESET_ALL}",
                flush=True,
            )
            break

        # Если произошло непонятное и модель не вернула ничего
        logger.warning("Модель вернула пустой ответ без tool_calls")
        messages.append(
            {
                "role": "user",
                "content": "[СИСТЕМНОЕ УВЕДОМЛЕНИЕ] Модель вернула пустой ответ.",
            }
        )
        logger.debug("{}", messages)
        break

    # Срабатывает, если цикл завершился по исчерпанию лимита tool_iterations.
    else:
        logger.warning(
            f"Достигнуто максимальное количество вызовов инструментов "
            f"на запрос пользователя. {settings.tool_iterations=}"
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "[СИСТЕМНОЕ УВЕДОМЛЕНИЕ] "
                    f"Достигнут лимит вызовов инструментов за один ответ "
                    f"({settings.tool_iterations}). "
                    "Учти это ограничение в следующих итерациях."
                ),
            }
        )

    return messages

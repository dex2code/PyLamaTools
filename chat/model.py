from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Dict, List, Tuple

import ollama
from loguru import logger

from chat.renderer import ConsoleRenderer
from helpers.cut_messages import count_messages_tokens, truncate_by_tokens
from helpers.execute_tool import execute_tool
from helpers.validate_config import SettingsModel


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


def chat_model(
    settings: SettingsModel,
    messages: List[Dict[str, Any]],
    ollama_client: ollama.Client,
    tool_descriptions: List[Dict[str, Any]],
    tool_functions: Dict[str, Any],
    project_root: Path,
    workspace_dir: Path,
    cb: ConsoleRenderer,
) -> list[dict]:

    tool_iteration = 0
    while tool_iteration < settings.tool_iterations:
        tool_iteration += 1

        messages = truncate_by_tokens(
            messages,
            max_tokens=settings.context_max_tokens,
            encoding_name=settings.context_encoding,
        )

        model_answer = ollama_client.chat(
            model=settings.ollama_model,
            messages=messages,
            tools=tool_descriptions,
            stream=settings.model_streaming,
            think=settings.model_thinking,
            options=settings.options,
        )

        accumulated_content = ""
        raw_tool_calls: List[Tuple[str, ollama.Message.ToolCall]] = []
        dumped_tool_calls: List[Dict] = []

        for chunk in _iter_chunks(model_answer):
            logger.trace(chunk)
            message = getattr(chunk, "message", None)
            if message is None:
                continue

            thinking_chunk = getattr(message, "thinking", None) or ""
            tool_calls_chunk = getattr(message, "tool_calls", None) or []
            content_chunk = getattr(message, "content", None) or ""

            if thinking_chunk:
                cb.on_thinking(thinking_chunk)

            if tool_calls_chunk:
                for idx, tc in enumerate(tool_calls_chunk):
                    dumped = tc.model_dump(exclude_none=True)
                    call_id = dumped.get("id") or f"call_{tool_iteration}_{idx}"
                    dumped["id"] = call_id
                    raw_tool_calls.append((call_id, tc))
                    dumped_tool_calls.append(dumped)

            if content_chunk:
                accumulated_content += content_chunk
                cb.on_content(content_chunk)

        # --- единая запись ответа ассистента ---
        if raw_tool_calls or accumulated_content:
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": accumulated_content,
            }
            if raw_tool_calls:
                assistant_msg["tool_calls"] = dumped_tool_calls
            messages.append(assistant_msg)
            logger.debug("{}", messages)

        # --- ветка с инструментами ---
        if raw_tool_calls:
            for call_id, tool_call in raw_tool_calls:
                name = tool_call.function.name
                args = tool_call.function.arguments
                cb.on_tool_call(name, args)

                tool_result = execute_tool(
                    tool_call=tool_call,
                    tool_functions=tool_functions,
                    project_root=project_root,
                    workspace_dir=workspace_dir,
                )
                cb.on_tool_result(name, tool_result)

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "tool_call_id": call_id,
                        "content": tool_result,
                    }
                )
                logger.debug("{}", messages)
            continue

        # --- ветка финального ответа ---
        if accumulated_content:
            tokens = count_messages_tokens(messages, settings.context_encoding)
            cb.on_context_size(tokens)
            break

        # --- пустой ответ ---
        logger.warning("Модель вернула пустой ответ без tool_calls")
        cb.on_empty_response()
        messages.append(
            {
                "role": "user",
                "content": "[СИСТЕМНОЕ УВЕДОМЛЕНИЕ] Модель вернула пустой ответ.",
            }
        )
        logger.debug("{}", messages)
        break

    else:
        logger.warning(
            f"Достигнут лимит вызовов инструментов. {settings.tool_iterations=}"
        )
        cb.on_iteration_limit(settings.tool_iterations)
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

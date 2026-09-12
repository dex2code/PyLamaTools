from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger
from helpers.execute_tool import execute_tool
from helpers.cut_messages import count_messages_tokens, truncate_by_tokens
from pathlib import Path
from helpers.validate_config import SettingsModel
import colorama
import ollama
import json


def chat_model(settings: SettingsModel,
               messages: List[Dict[str, Any]],
               ollama_client: ollama.Client,
               tool_descriptions: List[Dict[str, Any]],
               tool_functions: Dict[str, Any],
               workspace_dir: Path) -> List[Dict[str, Any]]:
    assistant_nick = f"🤖 {colorama.Fore.CYAN}{settings.ollama_model}{colorama.Fore.WHITE}"

    iteration = 0
    while iteration < settings.tool_iterations:
        iteration += 1

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
        logger.debug(f"{response_model}")

        message_model = response_model.message
        if message_model is None:
            logger.warning("Модель вернула ответ без поля 'message'")
            break

        message_thinking = message_model.thinking
        if message_thinking and settings.display_thinking:
            print(f"{colorama.Style.DIM}{message_thinking}{colorama.Style.RESET_ALL}", flush=True)

        if message_model.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [tc.model_dump() for tc in message_model.tool_calls],
                    "content": ""
                }
            )
            for tool_call in message_model.tool_calls:
                print(f"\r⚙️  {colorama.Fore.LIGHTMAGENTA_EX}"
                      f"Вызов инструмента '{tool_call.function.name}' "
                      f"с аргументами {tool_call.function.arguments}")
                tool_result = execute_tool(tool_call=tool_call,
                                           tool_functions=tool_functions,
                                           workspace_dir=workspace_dir)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_call.function.name,
                        "content": tool_result
                    }
                )
                logger.debug(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")
            continue

        if message_model.content:
            print(f"\r{assistant_nick}: {colorama.Fore.WHITE}{message_model.content}",
                  flush=True)
            messages.append(
                {
                    "role": "assistant",
                    "content": message_model.content
                }
            )
            context_tokens = count_messages_tokens(messages, settings.context_encoding)
            print(f"   {colorama.Style.DIM}"
                  f"Размер контекста: {context_tokens} токенов"
                  f"{colorama.Style.RESET_ALL}")
            logger.debug(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")
            break

    return messages


if __name__ == "__main__":
    pass
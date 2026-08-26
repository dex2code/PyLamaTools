from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger
from config import settings
from execute_tool import execute_tool
from cut_messages import count_tokens, truncate_by_tokens
import colorama
import ollama
import json


@logger.catch(reraise=True)
def chat_model(messages: List[Dict[str, Any]],
               ollama_client: ollama.Client,
               tool_descriptions: List[Dict[str, Any]],
               tool_functions: Dict[str, Any]) -> List[Dict[str, Any]]:
    logger.debug(" -> In function chat_model.chat_model()")

    assistant_nick = f"🤖 {colorama.Fore.CYAN}{settings['ollama_model']}{colorama.Fore.WHITE}"

    iteration = 0
    while iteration < settings['tool_iterations']:
        iteration += 1

        print("⏳ ", end="", flush=True)

        # Передаем в модель контекст чата и получаем ответ
        response_model = ollama_client.chat(
            model=settings['ollama_model'],
            messages=messages,
            tools=tool_descriptions,
            think=settings['model_thinking'],
            options=settings['options']
        )
        logger.debug(f"{response_model}")

        if "message" not in response_model:
            logger.warning("Модель вернула пустой ответ!")
            continue

        message_model = response_model["message"]

        if settings['display_thinking']:
            if "thinking" in message_model and message_model['thinking']:
                print(f"{colorama.Style.DIM}{message_model['thinking']}{colorama.Style.RESET_ALL}",
                      flush=True)

        if "content" in message_model and message_model['content']:
            print(f"\r{assistant_nick}: {colorama.Fore.WHITE}{message_model['content']}",
                  flush=True)
            messages.append(
                {
                    "role": "assistant",
                    "content": message_model['content']
                }
            )

        if "tool_calls" in message_model and message_model['tool_calls']:
            tool_call: ollama.Message.ToolCall
            for tool_call in message_model['tool_calls']:
                print(f"⚙️ {colorama.Fore.LIGHTRED_EX}Вызов инструмента "
                      f"'{tool_call['function']['name']}' "
                      f"с аргументами {tool_call['function']['arguments']}")
                tool_result = execute_tool(tool_call=tool_call, tool_functions=tool_functions)
                messages.append(
                    {
                        "role": "tool",
                        "name": tool_call['function']['name'],
                        "content": tool_result
                    }
                )
                logger.debug(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")
            continue
        else:
            messages = truncate_by_tokens(messages=messages,
                                          max_tokens=settings['context_max_tokens'],
                                          encoding_name=settings['context_encoding'])
            print(f"   {colorama.Style.DIM}Размер контекста: "
                  f"{count_tokens(messages=messages, encoding_name=settings['context_encoding'])}/"
                  f"{settings['context_max_tokens']} ток.{colorama.Style.RESET_ALL}")
            break

    logger.debug(" <- Out function chat_model.chat_model()")
    return messages


if __name__ == "__main__":
    pass
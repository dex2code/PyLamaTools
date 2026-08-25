from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger
from config import settings
import colorama
import json
import ollama


@logger.catch
def chat_model(messages: List[Dict[str, Any]],
               ollama_client: ollama.Client,
               tool_descriptions: List[Dict[str, Any]],
               tool_functions: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("⏳", end=" ", flush=True)

    # Передаем в модель контекст чата и получаем стриминг ответа по чанкам
    response_stream = ollama_client.chat(
        model=settings['ollama_model'],
        messages=messages,
        tools=tool_descriptions,
        stream=settings['chat_streaming'],
        think=settings['model_thinking'],
        options=settings['options']
    )

    first_token = True
    is_thinking = False
    full_answer = ""
    stats_answer = {}
    assistant_nick = f"🤖 {colorama.Fore.CYAN}{settings['ollama_model']}{colorama.Fore.WHITE}"

    # Цикл пока не кончились чанки в стриме
    for chunk in response_stream:
        logger.debug(f"{chunk}")

        # Последний чанк содержит флаг done - собираем из него статистику
        if "done" in chunk and chunk['done']:
            stats_answer['eval_count'] = chunk.get("eval_count", 0)
            stats_answer['total_duration'] = round(chunk.get("total_duration", 0) / 1e9)
            continue

        # Если в чанке нет сообщения - пропускаем его
        if "message" not in chunk:
            continue

        chunk_message = chunk['message']

        # Выводим рассуждения модели
        if "thinking" in chunk_message and chunk_message['thinking'] is not None:
            if first_token:
                first_token = False
                is_thinking = True

            if not is_thinking:
                is_thinking = True
                if settings['display_thinking']:
                    print("\n⏳", end=" ", flush=True)

            if settings['display_thinking']:
                print(f"{colorama.Style.DIM}{chunk_message['thinking']}{colorama.Style.RESET_ALL}",
                      end="", flush=True)

        # Выводим ответ модели
        if "content" in chunk_message and chunk_message['content']:
            if first_token or is_thinking:
                first_token = False
                is_thinking = False
                if settings['display_thinking']:
                    print(f"\n{assistant_nick}:", end=" ", flush=True)
                else:
                    print(f"\r{assistant_nick}:", end=" ", flush=True)

            print(f"{colorama.Fore.WHITE}{chunk_message['content']}", end="", flush=True)
            # Собираем из чанков полную строку ответа
            full_answer += chunk_message['content']

    # Добавляем в контекст ответ модели
    if full_answer:
        messages.append(
            {
                "role": "assistant",
                "content": full_answer
            }
        )
    else:
        logger.warning(f"Модель не вернула полный ответ")

    # Если заполнена статистика - выводим
    if stats_answer:
        print(f"{colorama.Style.DIM}\n   ⌁ {stats_answer['eval_count']} токенов "
              f"за {stats_answer['total_duration']} сек.{colorama.Style.RESET_ALL}")

    logger.debug(f"{json.dumps(stats_answer, indent=2, ensure_ascii=False)}")
    return messages


if __name__ == "__main__":
    pass
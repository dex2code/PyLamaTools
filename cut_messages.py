from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger
import json
import tiktoken


@logger.catch(reraise=True)
def count_tokens(messages: List[Dict[str, Any]], encoding_name: str) -> int:
    """
    Подсчитывает количество токенов в списке сообщений, сериализуя каждое сообщение в JSON.
    """
    logger.debug(" -> In function cut.messages.count_tokens()")

    encoder = tiktoken.get_encoding(encoding_name)
    text = json.dumps(messages, ensure_ascii=False)

    logger.debug(" <- Out function cut.messages.count_tokens()")
    return len(encoder.encode(text))


@logger.catch(reraise=True)
def truncate_by_tokens(messages: List[Dict[str, Any]],
                       max_tokens: int,
                       encoding_name: str) -> List[Dict[str, Any]]:
    """
    Обрезает список сообщений до указанного размера, возвращает обрезанный список
    """
    logger.debug(" -> In function cut.messages.truncate_by_tokens()")

    if not max_tokens or not messages:
        return messages

    truncated = messages.copy()
    while len(truncated) > 1 and count_tokens(truncated, encoding_name) > max_tokens:
        truncated.pop(1)  # удаляем второе (самое старое не-системное)

    logger.debug(" <- Out function cut.messages.truncate_by_tokens()")
    return truncated
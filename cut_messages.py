from __future__ import annotations
from config import settings
from typing import List, Dict, Any
from loguru import logger
import tiktoken


@logger.catch(reraise=True)
def count_tokens(messages: str,
                 encoding_name: str = settings['context_encoding']) -> int:
    """
    Подсчитывает количество токенов в списке сообщений, сериализуя каждое сообщение в JSON.
    """
    logger.debug(" -> In function cut.messages.count_tokens()")

    encoder = tiktoken.get_encoding(encoding_name)

    logger.debug(" <- Out function cut.messages.count_tokens()")
    return len(encoder.encode(messages))


@logger.catch(reraise=True)
def truncate_by_tokens(messages: List[Dict[str, Any]],
                       max_tokens: int = settings['context_max_tokens'],
                       encoding_name: str = settings['context_encoding']) -> List[Dict[str, Any]]:
    """
    Обрезает список сообщений до указанного размера, возвращает обрезанный список
    """
    logger.debug(" -> In function cut.messages.truncate_by_tokens()")

    if not max_tokens or not messages:
        return messages

    truncated = messages.copy()
    while len(truncated) > 1 and count_tokens(str(truncated), encoding_name) > max_tokens:
        truncated.pop(1)  # удаляем второе (самое старое не-системное)

    logger.debug(" <- Out function cut.messages.truncate_by_tokens()")
    return truncated
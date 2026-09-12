from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Dict, Any

import puretiktoken


# Эмпирическая надбавка на chat-шаблон одного сообщения
# (роль + служебные маркеры). Откалибруйте под свою модель по
# `prompt_eval_count` из ответов Ollama.
_MESSAGE_OVERHEAD_TOKENS = 4

# Надбавка за начало/конец диалога в chat-шаблоне.
_DIALOG_OVERHEAD_TOKENS = 2


@lru_cache(maxsize=None)
def _get_encoder(encoding_name: str):
    """Кешированный BPE-энкодер."""
    return puretiktoken.get_encoding(encoding_name)


def count_tokens(text: str, encoding_name: str) -> int:
    """
    Число токенов в строке text.

    Внимание: используется энкодер OpenAI (puretiktoken), а не токенизатор
    модели из Ollama. Для русского текста оценка обычно завышена — то есть
    безопасна для обрезки контекста.
    """
    if not text:
        return 0
    return len(_get_encoder(encoding_name).encode(text))


def _message_tokens(message: Dict[str, Any], encoding_name: str) -> int:
    """Токены одного сообщения: overhead + content + tool_calls."""
    total = _MESSAGE_OVERHEAD_TOKENS

    content = message.get("content") or ""
    if content:
        total += count_tokens(content, encoding_name=encoding_name)

    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        total += count_tokens(json.dumps(tool_calls, ensure_ascii=False),
                              encoding_name=encoding_name)
    return total


def count_messages_tokens(messages: List[Dict[str, Any]], encoding_name: str) -> int:
    """Суммарное число токенов в списке сообщений."""
    if not messages:
        return 0
    return (sum(_message_tokens(m, encoding_name) for m in messages)
            + _DIALOG_OVERHEAD_TOKENS)


def truncate_by_tokens(messages: List[Dict[str, Any]],
                       max_tokens: int,
                       encoding_name: str) -> List[Dict[str, Any]]:
    """
    Обрезает историю сообщений до max_tokens.

    Гарантии:
      * Сообщение с role='system' в позиции 0 сохраняется всегда.
      * История режется целыми ходами (от 'user' до следующего 'user'),
        чтобы не разрывать пары assistant(tool_calls) ↔ tool(response).
      * Последний ход пользователя не удаляется, даже если он один
        превышает лимит — резать дальше нечего.
    """
    if not max_tokens or not messages:
        return messages

    truncated = list(messages)

    has_system = truncated[0].get("role") == "system"
    head_size = 1 if has_system else 0

    while (len(truncated) > head_size + 1
           and count_messages_tokens(truncated, encoding_name) > max_tokens):

        # Ищем границу следующего хода — индекс следующего 'user'.
        next_user_idx = next(
            (i for i in range(head_size + 1, len(truncated))
             if truncated[i].get("role") == "user"),
            None,
        )
        if next_user_idx is None:
            break  # ходов больше нет

        del truncated[head_size:next_user_idx]

    return truncated


if __name__ == "__main__":
    pass
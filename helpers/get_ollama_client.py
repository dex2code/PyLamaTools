from __future__ import annotations
from loguru import logger
from typing import Dict, Any
import sys
import ollama


def get_ollama_client(settings: Dict[str, Any]) -> ollama.Client:
    logger.debug(f" -> In function helpers.ollama_client.ollama.client()")

    ollama_client = ollama.Client(settings['ollama_url'])
    try:
        list_models = ollama_client.list()
    except Exception as e:
        logger.error(f"Ошибка подключения к API Ollama по адресу "
                     f"{settings['ollama_url']} ({e})")
        sys.exit(1)

    # Проверяем, что наша модель есть в Ollama
    model_names = [model.model for model in list_models.models]
    if settings['ollama_model'] not in model_names:
        logger.error(f"Модель, указанная в настройках ({settings['ollama_model']}), "
                     f"отсутствует в списке 'ollama ls'.\n"
                     f"Список доступных моделей: {model_names}"
                     f"\nСкачайте указанную модель: 'ollama pull {settings['ollama_model']}'")
        sys.exit(1)

    logger.debug(f" <- Out function helpers.ollama_client.ollama.client()")
    return ollama_client


if __name__ == "__main__":
    pass
from __future__ import annotations
from loguru import logger
from typing import Dict, Any
import ollama


@logger.catch(reraise=True)
def get_ollama_client(settings: Dict[str, Any]) -> ollama.Client:
    """
    Создаёт клиента Ollama и проверяет доступность указанной модели.

    Args:
        settings: Словарь с настройками, должен содержать ключи:
            'ollama_url' – URL сервера Ollama,
            'ollama_model' – имя модели.

    Returns:
        Объект ollama.Client.

    Raises:
        ConnectionError: если не удаётся подключиться к Ollama.
        RuntimeError: если указанная модель отсутствует.
    """
    logger.debug(f" -> In function helpers.get_ollama_client.get_ollama_client()")

    try:
        ollama_client = ollama.Client(settings['ollama_url'])
        list_models = ollama_client.list()
    except Exception as e:
        logger.error(f"Ошибка подключения к API Ollama по адресу "
                     f"{settings['ollama_url']} ({e})")
        raise ConnectionError(f"Ошибка подключения к API Ollama")

    # Проверяем, что наша модель есть в Ollama
    our_model: str = settings['ollama_model']
    model_names = [model.model for model in list_models.models]
    if our_model not in model_names:
        logger.error(f"Модель, указанная в настройках ({our_model}), "
                     f"отсутствует в списке 'ollama ls'.\n"
                     f"Список доступных моделей: {model_names}"
                     f"\nСкачайте указанную модель: 'ollama pull {our_model}'")
        raise RuntimeError(f"Некорректное название модели в настройках")

    logger.info(f"Успешно подключились к Ollama API {settings['ollama_url']} "
                f"и выбрали модель {settings['ollama_model']}")

    logger.debug(f" <- Out function helpers.get_ollama_client.get_ollama_client()")
    return ollama_client


if __name__ == "__main__":
    pass
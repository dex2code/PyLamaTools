from __future__ import annotations
from loguru import logger
from helpers.validate_config import SettingsModel
import ollama


def get_ollama_client(settings: SettingsModel) -> ollama.Client:
    """
    Создаёт клиента Ollama и проверяет доступность указанной модели.

    Args:
        settings: Валидированная модель настроек.

    Returns:
        Объект ollama.Client.

    Raises:
        ConnectionError: если не удаётся подключиться к Ollama.
        RuntimeError: если указанная модель отсутствует.
    """
    try:
        ollama_client = ollama.Client(
            str(settings.ollama_url)
        )
        list_models = ollama_client.list()
    except Exception as e:
        logger.exception(f"Ошибка подключения к API Ollama по адресу {settings.ollama_url}")
        raise ConnectionError("Ошибка подключения к API Ollama") from e

    # Проверяем, что наша модель есть в Ollama
    model_names = [model.model for model in list_models.models]
    if settings.ollama_model not in model_names:
        logger.error(f"Модель, указанная в настройках ({settings.ollama_model}), "
                     f"отсутствует в списке 'ollama ls'.\n"
                     f"Список доступных моделей: {model_names}"
                     f"\nСкачайте указанную модель: 'ollama pull {settings.ollama_model}'")
        raise RuntimeError("Некорректное название модели в настройках")

    logger.info(f"Успешно подключились к Ollama API {settings.ollama_url} "
                f"и выбрали модель {settings.ollama_model}")

    return ollama_client


if __name__ == "__main__":
    pass
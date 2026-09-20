from __future__ import annotations
import argparse
from typing import Optional, Sequence


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="PyLamaTools - LLM чат-оркестратор с локальными инструментами.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        type=str,
        default="",
        help="Промт, передаваемый в контекст при запуске.",
        dest="prompt",
    )
    parser.add_argument(
        "-f",
        "--prompt-file",
        type=str,
        default="",
        help="Путь к файлу с текстом промта. Текст передается в контекст при запуске.",
        dest="prompt_file",
    )
    parser.add_argument(
        "-q",
        "--quit-after-prompt",
        action="store_true",
        help="Выйти из программы после первого ответа модели.",
        dest="quit_after_prompt",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="",
        help="Название модели Ollama. Переопределяет значение из конфига.",
        dest="ollama_model",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Парсит аргументы CLI. argv удобен для тестов."""
    parser = build_parser()
    return parser.parse_args(args=argv)

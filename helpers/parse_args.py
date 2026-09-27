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
    parser.add_argument(
        "-o",
        "--output-format",
        type=str,
        choices=["plain", "json", "interactive"],
        default="interactive",
        help=(
            "Формат вывода. По умолчанию 'interactive'. "
            "При указании 'plain' или 'json' автоматически "
            "включается режим --quit-after-prompt и требуется задать "
            "хотя бы один из --prompt или --prompt-file."
        ),
        dest="output_format",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Парсит аргументы CLI. argv удобен для тестов."""
    parser = build_parser()
    args = parser.parse_args(args=argv)

    if args.prompt and not args.prompt.strip():
        parser.error("--prompt не должен быть пустой строкой или строкой из пробелов")

    if args.output_format in ("plain", "json"):
        args.quit_after_prompt = True

        if not args.prompt and not args.prompt_file:
            parser.error(
                f"--output-format {args.output_format} требует указания "
                f"--prompt или --prompt-file"
            )

    return args

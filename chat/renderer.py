from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import colorama

Phase = Literal["INIT", "THINKING", "TOOL_CALL", "ANSWERING"]


class ConsoleRenderer:
    """Печатает события чата в консоль. Управляет фазами и ANSI-стилями."""

    def __init__(
        self,
        assistant_nick: str,
        *,
        display_thinking: bool = True,
        display_answer: bool = True,
        display_tool_call: bool = True,
        display_content_length: bool = True,
    ) -> None:
        self._phase: Phase = "INIT"
        self._nick = assistant_nick
        self._show_thinking = display_thinking
        self._show_answer = display_answer
        self._show_tool = display_tool_call
        self._show_length = display_content_length

    def _switch_phase(self, new: Phase, disp_new: bool, prefix: str = "") -> Phase:
        """Точная копия старой _switch_phase, но с self._phase."""
        if self._phase != new:
            print(colorama.Style.RESET_ALL, end="", flush=True)
            if disp_new:
                print(flush=True)
                if prefix:
                    print(f"{prefix}", end="", flush=True)
        self._phase = new
        return new

    # --- колбэки ---

    def on_thinking(self, chunk: str) -> None:
        self._switch_phase("THINKING", self._show_thinking, "🤔 ")
        if self._show_thinking:
            print(f"{colorama.Style.DIM}{chunk}", end="", flush=True)

    def on_content(self, chunk: str) -> None:
        self._switch_phase("ANSWERING", self._show_answer, self._nick)
        if self._show_answer:
            print(f"{colorama.Style.NORMAL}{chunk}", end="", flush=True)

    def on_tool_call(self, name: str, arguments: Mapping[str, Any]) -> None:
        self._switch_phase("TOOL_CALL", self._show_tool, "🔨 ")
        if self._show_tool:
            print(
                f"{colorama.Fore.LIGHTMAGENTA_EX}"
                f"Вызов инструмента '{name}' "
                f"с аргументами {arguments}"
                f"{colorama.Style.RESET_ALL}",
                flush=True,
            )

    def on_tool_result(self, name: str, result: str) -> None:
        if self._show_tool:
            print(
                f"{colorama.Fore.LIGHTCYAN_EX}"
                f"Инструмент '{name}' вернул значение: "
                f" {result}"
                f"{colorama.Style.RESET_ALL}",
                flush=True,
            )

    def on_context_size(self, tokens: int) -> None:
        if self._show_length:
            print(colorama.Style.RESET_ALL, flush=True)
            print(
                f"{colorama.Style.DIM}"
                f"Размер контекста: {tokens} токенов"
                f"{colorama.Style.RESET_ALL}",
                flush=True,
            )

    def on_empty_response(self) -> None:
        pass

    def on_iteration_limit(self, limit: int) -> None:
        pass

"""Keyboard builders with style passthrough."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Button:
    """Framework-neutral inline button spec."""

    text: str
    callback_data: str
    style: str | None = None
    copy_text: str | None = None


def button(text: str, callback_data: str, *, style: str | None = None) -> Button:
    """Create a button spec."""

    return Button(text=text, callback_data=callback_data, style=style)


def rows(*items: Button | list[Button]) -> list[list[Button]]:
    """Build keyboard rows."""

    result: list[list[Button]] = []
    for item in items:
        if isinstance(item, list):
            result.append(item)
        else:
            result.append([item])
    return result


def as_aiogram_markup(keyboard: list[list[Button]]) -> Any:
    """Convert to aiogram InlineKeyboardMarkup when aiogram is installed."""

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    inline_rows: list[list[InlineKeyboardButton]] = []
    for row in keyboard:
        inline_row: list[InlineKeyboardButton] = []
        for item in row:
            kwargs: dict[str, Any] = {"text": item.text, "callback_data": item.callback_data}
            if item.style is not None:
                kwargs["style"] = item.style
            inline_row.append(InlineKeyboardButton(**kwargs))
        inline_rows.append(inline_row)
    return InlineKeyboardMarkup(inline_keyboard=inline_rows)


def open_menu_reply_keyboard() -> Any:
    """Build persistent reply keyboard for opening the menu."""

    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть меню")]],
        resize_keyboard=True,
        is_persistent=True,
    )

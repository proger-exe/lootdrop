"""User start and legal handlers."""

from app.data.texts import LEGAL_VERSION, TEXTS
from app.db.repositories.protocols import UserRepository
from app.keyboards.factories import Button
from app.keyboards.user.menu import legal_keyboard, main_menu_keyboard


async def render_start(user_id: int, has_legal: bool) -> tuple[str, list[list[Button]]]:
    """Render the first screen for a user."""

    if has_legal:
        return TEXTS["menu.main"], main_menu_keyboard()
    return f"{TEXTS['legal.welcome']}\n\n{TEXTS['legal.accept_note']}", legal_keyboard()


async def accept_legal(
    user_repository: UserRepository, user_id: int, language_code: str | None
) -> tuple[str, list[list[Button]]]:
    """Accept legal documents and return main menu."""

    await user_repository.accept_legal(user_id, LEGAL_VERSION, language_code)
    return TEXTS["menu.main"], main_menu_keyboard()

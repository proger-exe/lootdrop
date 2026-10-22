"""Background worker entrypoint."""

import asyncio
from contextlib import suppress

from app.config.loader import load_settings


async def run_worker() -> None:
    """Run background jobs forever."""

    settings = load_settings()
    stop_event = asyncio.Event()
    while True:
        # Real job wiring is initialized after SQLite and in-memory services setup.
        with suppress(TimeoutError):
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.payments.poll_interval_seconds,
            )


def main() -> None:
    """Run the worker process."""

    with suppress(KeyboardInterrupt):
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()

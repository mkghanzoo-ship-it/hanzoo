from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from bot_manager.client import BotConfig, BotManagerBotClient
from bot_manager.command_handler import CommandHandler
from bot_manager import permissions

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "bots.json"
LOG_PATH = ROOT / "bot_manager.log"


def configure_logging() -> None:
    """Configure console and file logging."""
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def load_bot_configs(config_path: Path) -> list[BotConfig]:
    """Load bot configuration entries from JSON."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Bot configuration file not found: {config_path.absolute()}"
        )

    with config_path.open("r", encoding="utf-8") as handle:
        raw_configs = json.load(handle)

    configs: list[BotConfig] = []
    for entry in raw_configs:
        trusted_admins = entry.get("trusted_admins", [])
        if trusted_admins is None:
            trusted_admins = []
        configs.append(
            BotConfig(
                username=str(entry.get("username", "")),
                server=entry.get("server"),
                token=str(entry.get("token", "")),
                present=entry.get("present"),
                display_name=str(entry.get("display_name", "Unnamed Bot")),
                trusted_admins=trusted_admins,
                command_handler=entry.get("command_handler", False),
            )
        )

    return configs


async def async_input(prompt: str = "") -> str:
    """Read console input in an asynchronous-friendly way."""
    return await asyncio.to_thread(input, prompt)


async def command_loop(handler: CommandHandler) -> None:
    """Run the interactive command loop until the user exits."""
    logging.info("Command loop ready. Type !help for available commands.")
    while True:
        try:
            raw_line = await async_input("> ")
        except (EOFError, KeyboardInterrupt):
            logging.info("Shutdown requested by user.")
            break

        if not raw_line.strip():
            continue

        should_continue = await handler.execute(raw_line)
        if not should_continue:
            break


async def main() -> None:
    """Bootstrap the bot manager application."""
    configure_logging()
    logging.info("Starting Python Multi-Bot Manager...")

    # Render Secret File support
    if Path("bots.json").exists() and not Path("config/bots.json").exists():
        Path("config").mkdir(exist_ok=True)
        shutil.copy("bots.json", "config/bots.json")
        logging.info("Copied bots.json from root to config/bots.json")

    # Initialize permission system
    trusted_admins_path = ROOT / "config" / "trusted_admins.json"
    permissions.initialize_permissions(trusted_admins_path)
    logging.info("Permission system initialized.")

    bot_configs = load_bot_configs(CONFIG_PATH)
    bots = [BotManagerBotClient(config) for config in bot_configs]

    # Start all bots and keep their reconnect loops active.
    await asyncio.gather(*(bot.start() for bot in bots))

    try:
        handler = CommandHandler(bots)
        await command_loop(handler)
    finally:
        logging.info("Shutting down all bots...")
        await asyncio.gather(*(bot.stop() for bot in bots), return_exceptions=True)
        logging.info("Bot manager shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())

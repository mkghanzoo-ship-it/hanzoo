from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from bot_manager.client import BotManagerBotClient


class CommandHandler:
    """Parses commands and dispatches them to managed bot clients."""

    PREFIX = "!"

    def __init__(self, bots: Iterable[BotManagerBotClient]) -> None:
        self.bots = list(bots)
        self.logger = logging.getLogger("CommandHandler")

    async def execute(self, raw_command: str) -> bool:
        """Execute a raw command line and return whether to continue."""
        raw_command = raw_command.strip()
        if not raw_command.startswith(self.PREFIX):
            self.logger.warning("Only prefix commands are supported: %s", raw_command)
            return True

        parts = raw_command[len(self.PREFIX) :].split()
        if not parts:
            return True

        command = parts[0].lower()
        args = parts[1:]

        command_map = {
            "say": self._handle_say,
            "follow": self._handle_follow,
            "stop": self._handle_stop,
            "jump": self._handle_jump,
            "spam": self._handle_spam,
            "status": self._handle_status,
            "help": self._handle_help,
            "exit": self._handle_exit,
        }

        handler = command_map.get(command)
        if handler is None:
            self.logger.warning("Unknown command: %s", command)
            return True

        await handler(args)
        return command != "exit"

    async def _broadcast(self, coro_factory) -> None:
        """Run an action for all bots concurrently."""
        tasks = [asyncio.create_task(coro_factory(bot)) for bot in self.bots]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.logger.exception("Bot action failed: %s", result)

    async def _handle_say(self, args: list[str]) -> None:
        """Broadcast a message to every connected bot."""
        if not args:
            self.logger.warning("Usage: !say <message>")
            return

        message = " ".join(args).strip()
        await self._broadcast(lambda bot: bot.say(message))

    async def _handle_follow(self, args: list[str]) -> None:
        """Broadcast a follow command to every bot."""
        if not args:
            self.logger.warning("Usage: !follow <target>")
            return

        target = " ".join(args).strip()
        await self._broadcast(lambda bot: bot.follow(target))

    async def _handle_stop(self, args: list[str]) -> None:
        """Broadcast stop to every bot."""
        await self._broadcast(lambda bot: bot.stop_action())

    async def _handle_jump(self, args: list[str]) -> None:
        """Broadcast a jump command to every bot."""
        await self._broadcast(lambda bot: bot.jump())

    async def _handle_spam(self, args: list[str]) -> None:
        """Broadcast a spam command to every bot."""
        if len(args) < 2:
            self.logger.warning("Usage: !spam <count> <message>")
            return

        try:
            count = int(args[0])
        except ValueError:
            self.logger.warning("Usage: !spam <count> <message> — count must be numeric.")
            return

        message = " ".join(args[1:]).strip()
        await self._broadcast(lambda bot: bot.spam(count, message))

    async def _handle_status(self, args: list[str]) -> None:
        """Report the status of all managed bots."""
        for bot in self.bots:
            self.logger.info(bot.status())

    async def _handle_help(self, args: list[str]) -> None:
        """Show available commands."""
        help_text = (
            "Available commands:\n"
            "  !say <message>   - Make all bots repeat the message.\n"
            "  !follow <target> - Make all bots follow the target.\n"
            "  !stop            - Make all bots stop their current action.\n"
            "  !jump            - Make all bots perform a jump action.\n"
            "  !spam <count> <message> - Make all bots send the message multiple times.\n"
            "  !status          - Print the connection status of all bots.\n"
            "  !help            - Print this help text.\n"
            "  !exit            - Shut down the bot manager.\n"
        )
        self.logger.info("%s", help_text)

    async def _handle_exit(self, args: list[str]) -> None:
        """Stop the manager and exit the application."""
        self.logger.info("Exit command received.")

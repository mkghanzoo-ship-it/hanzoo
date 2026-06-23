from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from bot_manager.client import BotManagerBotClient
from bot_manager import permissions


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
            "trust": self._handle_trust,
            "untrust": self._handle_untrust,
            "trusted": self._handle_trusted,
            "setowner": self._handle_setowner,
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
            "\n"
            "Permission Commands (Owner Only):\n"
            "  !setowner <user_id>   - Set the owner (initial setup).\n"
            "  !trust <user_id>      - Add a user as trusted admin.\n"
            "  !untrust <user_id>    - Remove a user from trusted admins.\n"
            "  !trusted              - Show list of trusted admins.\n"
            "\n"
            "  !exit            - Shut down the bot manager.\n"
        )
        self.logger.info("%s", help_text)

    async def _handle_exit(self, args: list[str]) -> None:
        """Stop the manager and exit the application."""
        self.logger.info("Exit command received.")

    async def _handle_setowner(self, args: list[str]) -> None:
        """Set the owner ID (initial setup only)."""
        if len(args) != 1:
            self.logger.warning("Usage: !setowner <user_id>")
            return

        try:
            owner_id = int(args[0])
        except ValueError:
            self.logger.error("❌ Invalid user ID. Must be numeric.")
            return

        if not permissions.is_valid_user_id(str(owner_id)):
            self.logger.error(f"❌ Invalid Discord user ID: {owner_id}")
            return

        current_owner = permissions.get_owner_id()
        if current_owner is not None:
            self.logger.error("❌ Owner already set. Current owner cannot be changed without manual config editing.")
            return

        permissions.set_owner(owner_id)
        self.logger.info(f"✅ Owner set to {owner_id}")

    async def _handle_trust(self, args: list[str]) -> None:
        """Add a user as a trusted admin (Owner only)."""
        if len(args) != 1:
            self.logger.warning("Usage: !trust <user_id>")
            return

        # This is a console command, so we check if owner is set
        # In real Discord implementation, this would check message.author.id
        if permissions.get_owner_id() is None:
            self.logger.error("❌ No owner set. Run !setowner first.")
            return

        try:
            user_id = int(args[0])
        except ValueError:
            self.logger.error("❌ Invalid user ID. Must be numeric.")
            return

        success, message = permissions.add_trusted_admin(user_id)
        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)

    async def _handle_untrust(self, args: list[str]) -> None:
        """Remove a user from trusted admins (Owner only)."""
        if len(args) != 1:
            self.logger.warning("Usage: !untrust <user_id>")
            return

        if permissions.get_owner_id() is None:
            self.logger.error("❌ No owner set. Run !setowner first.")
            return

        try:
            user_id = int(args[0])
        except ValueError:
            self.logger.error("❌ Invalid user ID. Must be numeric.")
            return

        success, message = permissions.remove_trusted_admin(user_id)
        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)

    async def _handle_trusted(self, args: list[str]) -> None:
        """Show the list of trusted admins (Owner only)."""
        if permissions.get_owner_id() is None:
            self.logger.error("❌ No owner set. Run !setowner first.")
            return

        admins = permissions.get_trusted_admins_list()
        owner_id = permissions.get_owner_id()

        self.logger.info(f"Owner: {owner_id}")

        if not admins:
            self.logger.info("No trusted admins currently set.")
            return

        self.logger.info("Trusted Admins:")
        for admin_id in admins:
            self.logger.info(f"  • {admin_id}")


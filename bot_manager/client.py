from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal

import discord
from discord import Client, Intents, TextChannel, Message
from discord.errors import LoginFailure


@dataclass
class BotConfig:
    """Holds a bot profile configuration."""

    username: str
    server: str | None = None
    token: str = ""
    present: str | None = None
    display_name: str = "Unnamed Bot"
    trusted_admins: list[int] = field(default_factory=list)
    command_handler: bool = False


BotConnectionState = Literal["connected", "disconnected", "reconnecting"]


class BotManagerBotClient:
    """Represents a managed Discord bot instance with automatic reconnect."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(f"BotManagerBotClient[{self.config.username}]")
        self.state: BotConnectionState = "disconnected"
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._action: str | None = None
        self._stop_spam = False
        self._state_lock = asyncio.Lock()
        self.client: Client | None = None
        self._channel: TextChannel | None = None

    async def start(self) -> None:
        """Start the bot and maintain a Discord client loop."""
        self._running = True
        self._task = asyncio.create_task(self._run_client_loop())
        self.logger.info("Starting bot client.")

    async def stop(self) -> None:
        """Shut down the bot cleanly."""
        self._running = False
        if self.client is not None and not self.client.is_closed():
            await self.client.close()

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        async with self._state_lock:
            self.state = "disconnected"
            self._action = None
            self._channel = None
        self.logger.info("Bot client stopped.")

    async def _run_client_loop(self) -> None:
        """Run the Discord client and reconnect automatically if needed."""
        while self._running:
            if not self.config.token:
                self.logger.error(
                    "Missing token for bot %s. Add a token to config/bots.json.",
                    self.config.username,
                )
                await self._set_state("disconnected")
                return

            self.client = self._create_client()
            try:
                await self.client.start(self.config.token)
            except LoginFailure as error:
                self.logger.error(
                    "Discord login failed for %s: %s",
                    self.config.username,
                    error,
                )
                await self._set_state("disconnected")
                return
            except asyncio.CancelledError:
                self.logger.debug("Discord client loop canceled.")
                return
            except Exception as error:  # noqa: BLE001
                self.logger.exception(
                    "Unexpected Discord client error for %s: %s",
                    self.config.username,
                    error,
                )
                await self._set_state("reconnecting")
                await asyncio.sleep(10)
            finally:
                self.client = None
                self._channel = None

    def _create_client(self) -> Client:
        """Create a Discord client and attach event handlers."""
        intents = Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        client = Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            self.logger.info(
                "%s signed in as %s.",
                self.config.display_name,
                client.user,
            )
            await self._set_state("connected")
            self._channel = await self._resolve_channel()
            if self._channel is not None:
                self.logger.info("Resolved channel %s for %s.", self._channel, self.config.username)
            else:
                self.logger.warning(
                    "No channel resolved for %s. Add present in config/bots.json.",
                    self.config.username,
                )

        @client.event
        async def on_message(message: Message) -> None:
            # Ignore bot's own messages
            if message.author == client.user:
                return
            
            # Ignore other bots' messages
            if message.author.bot:
                return
            
            # Only process commands if this bot is designated as command handler
            if not self.config.command_handler:
                return
            
            # Process commands from any channel
            if message.content.startswith("!"):
                await self.handle_command(message)

        @client.event
        async def on_disconnect() -> None:
            self.logger.warning("Discord client disconnected for %s.", self.config.username)
            await self._set_state("disconnected")

        @client.event
        async def on_resumed() -> None:
            self.logger.info("Discord client resumed for %s.", self.config.username)
            await self._set_state("connected")

        @client.event
        async def on_error(event_method: str, *args, **kwargs) -> None:
            self.logger.exception("Discord client error in %s", event_method)

        return client

    async def _set_state(self, state: BotConnectionState) -> None:
        """Update the bot connection state safely."""
        async with self._state_lock:
            self.state = state

    def is_connected(self) -> bool:
        """Return true when the bot is currently connected."""
        return self.state == "connected" and self.client is not None and self.client.is_ready()

    async def _resolve_channel(self) -> TextChannel | None:
        """Resolve the outgoing text channel for the bot."""
        if self.client is None or not self.client.is_ready():
            return None

        if self.config.present is not None:
            # Try to parse present as a channel ID
            try:
                channel_id = int(self.config.present)
                channel = self.client.get_channel(channel_id)
                if isinstance(channel, TextChannel):
                    return channel
            except (ValueError, TypeError):
                pass
            self.logger.warning("Configured present %s not found.", self.config.present)

        for channel in self.client.get_all_channels():
            if isinstance(channel, TextChannel):
                return channel

        return None

    async def _send_to_channel(self, content: str, channel: TextChannel | None = None) -> None:
        """Send content to the specified channel, or the resolved text channel if not specified."""
        if not self.is_connected():
            self.logger.warning("Unable to send message because bot is disconnected.")
            return

        target_channel = channel
        if target_channel is None:
            target_channel = self._channel
            if target_channel is None:
                target_channel = await self._resolve_channel()
                self._channel = target_channel

        if target_channel is None:
            self.logger.warning("Unable to send message: no channel resolved for %s.", self.config.username)
            return

        try:
            await target_channel.send(content)
        except Exception as error:  # noqa: BLE001
            self.logger.exception("Failed to send message in channel for %s: %s", self.config.username, error)

    async def say(self, message: str, channel: TextChannel | None = None) -> None:
        """Send a message through the bot if connected."""
        if not self.is_connected():
            self.logger.warning("Say command skipped because bot is disconnected.")
            return

        self.logger.info("Sending message: %s", message)
        await self._send_to_channel(message, channel)

    async def follow(self, target: str, channel: TextChannel | None = None) -> None:
        """Make the bot follow the specified target."""
        if not self.is_connected():
            self.logger.warning("Follow command skipped because bot is disconnected.")
            return

        self._action = f"following {target}"
        self.logger.info("Following target: %s", target)
        await self._send_to_channel(f"{self.config.display_name} is now following {target}.", channel)

    async def stop_action(self, channel: TextChannel | None = None) -> None:
        """Stop the bot's current action."""
        if not self.is_connected():
            self.logger.warning("Stop command skipped because bot is disconnected.")
            return

        # Interrupt spam if in progress
        if "spamming" in (self._action or ""):
            self._stop_spam = True
            self.logger.info("Stopping spam action.")
            await self._send_to_channel(f"{self.config.display_name} stopped spamming.", channel)
            return

        if self._action is not None:
            self.logger.info("Stopping action: %s", self._action)
            await self._send_to_channel(f"{self.config.display_name} stopped {self._action}.", channel)
            self._action = None
        else:
            self.logger.info("No active action to stop.")
            await self._send_to_channel(f"{self.config.display_name} is idle.", channel)

    async def jump(self, channel: TextChannel | None = None) -> None:
        """Make the bot perform a jump action."""
        if not self.is_connected():
            self.logger.warning("Jump command skipped because bot is disconnected.")
            return

        self._action = "jumping"
        self.logger.info("Jumping.")
        await self._send_to_channel(f"{self.config.display_name} jumped.", channel)

    async def spam(self, amount: int, message: str, channel: TextChannel | None = None) -> None:
        """Spam the specified message a number of times."""
        if not self.is_connected():
            self.logger.warning("Spam command skipped because bot is disconnected.")
            return

        if amount <= 0:
            self.logger.warning("Spam amount must be positive.")
            return

        self._stop_spam = False
        self._action = f"spamming {amount} messages"
        
        for index in range(amount):
            if self._stop_spam:
                self.logger.info("Spam stopped by user.")
                break
            
            self.logger.info("Spam %d/%d: %s", index + 1, amount, message)
            await self._send_to_channel(message, channel)
            await asyncio.sleep(0.2)
        
        self._action = None

    def status(self) -> str:
        """Return a human-readable summary of the bot's current status."""
        state = self.state
        action = self._action or "idle"
        return f"{self.config.display_name} ({self.config.username}) is {state} and {action}."

    async def handle_command(self, message: Message) -> None:
        """Handle an incoming message command."""
        if not message.content.startswith("!"):
            return

        parts = message.content[1:].split()
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]
        
        # Check if user is a trusted admin - if list is not empty, user must be in it
        # If list is empty, deny all commands (restrict by default)
        if len(self.config.trusted_admins) == 0:
            await self._send_to_channel(
                f"❌ {message.author.mention}, no trusted admins configured. Commands are disabled.",
                message.channel if isinstance(message.channel, TextChannel) else None
            )
            return
        
        if message.author.id not in self.config.trusted_admins:
            await self._send_to_channel(
                f"❌ {message.author.mention}, you don't have permission to use bot commands.",
                message.channel if isinstance(message.channel, TextChannel) else None
            )
            return
        
        # Get the channel where the message was sent
        command_channel = message.channel if isinstance(message.channel, TextChannel) else None

        if command == "say" and args:
            msg = " ".join(args).strip()
            await self.say(msg, command_channel)
        elif command == "follow" and args:
            target = " ".join(args).strip()
            await self.follow(target, command_channel)
        elif command == "stop":
            await self.stop_action(command_channel)
        elif command == "jump":
            await self.jump(command_channel)
        elif command == "spam":
            if len(args) < 2:
                await self._send_to_channel("❌ Usage: !spam <count> <message>", command_channel)
                return
            try:
                count = int(args[0])
                if count <= 0:
                    await self._send_to_channel("❌ Spam count must be greater than 0", command_channel)
                    return
                spam_msg = " ".join(args[1:]).strip()
                await self.spam(count, spam_msg, command_channel)
            except ValueError:
                await self._send_to_channel("❌ Usage: !spam <count> <message>", command_channel)
        elif command == "status":
            await self._send_to_channel(self.status(), command_channel)
        else:
            await self._send_to_channel(f"❌ Unknown command: {command}. Type !help for available commands.", command_channel)

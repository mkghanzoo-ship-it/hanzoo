# Python Multi-Bot Manager

A Python 3.11+ multi-bot manager application that runs several bot clients in parallel with shared command handling.

## Features

- Multiple bots managed from one script
- Asynchronous command handling with `asyncio`
- Shared command prefix: `!`
- Commands: `!say`, `!follow`, `!stop`, `!jump`, `!spam`, `!status`, `!help`, `!exit`
- **Owner-controlled permission system** with `!trust`, `!untrust`, `!trusted` commands
- Automatic reconnect when a bot disconnects
- Configurable bot profiles in `config/bots.json`
- Centralized permission management in `config/trusted_admins.json`
- Logging and error handling

## Requirements

- Python 3.11 or newer
- discord.py>=2.3.0

## Setup

1. Open the workspace in VS Code.
2. Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install requirements:

```powershell
pip install -r requirements.txt
```

## Running

From the workspace root:

```powershell
python main.py
```

## Configuration

### Bot Profiles (`config/bots.json`)

Create bots.json with bot credentials:

```json
[
  {
    "username": "alpha_bot",
    "password": "password-here",
    "token": "discord-token-here",
    "server": "game.example.net",
    "present": null,
    "display_name": "AlphaBot",
    "command_handler": true
  }
]
```

**Important:** `trusted_admins` is no longer set per-bot. Use the global permission system instead.

### Permissions (`config/trusted_admins.json`)

Automatically created on first run. Example:

```json
{
  "owner_id": 1305914685110878280,
  "trusted_admins": [123456789, 987654321]
}
```

## Commands

### Standard Commands

- `!say <message>` — all connected bots repeat the message
- `!follow <target>` — all bots follow the specified target
- `!stop` — all bots stop their current action
- `!jump` — all bots perform a jump action
- `!spam <count> <message>` — all bots send the message repeatedly
- `!status` — show connection status of all bots
- `!help` — display available commands
- `!exit` — shutdown the bot manager

### Permission Management Commands (Owner Only)

- `!trust <user_id>` — add a user as trusted admin
- `!untrust <user_id>` — remove a user from trusted admins
- `!trusted` — show owner and all trusted admins
- `!setowner <user_id>` — set the owner (initial setup only)

## Permission System

### Owner

- Has all permissions automatically
- Can add/remove trusted admins
- Cannot be removed from the system

### Trusted Admins

- Can execute all bot commands
- Cannot manage permissions
- Cannot add or remove other admins

### Usage Example

```
> !setowner 1305914685110878280
✅ Owner set to 1305914685110878280

> !trust 123456789012345678
✅ User 123456789012345678 added as trusted admin

> !trusted
Owner: 1305914685110878280
Trusted Admins:
  • 123456789012345678
```

## Deployment

### Local Deployment

Run directly in terminal:
```powershell
python main.py
```

### Render Deployment

1. Push code to GitHub
2. On Render:
   - Create new Web Service from GitHub
   - Add secret `bots.json` with your bot configuration
   - Add secret `trusted_admins.json` with owner and admin IDs
3. Set start command: `python main.py`

### Replit Deployment

1. Import from GitHub
2. Create `config/bots.json` with bot credentials
3. Create `config/trusted_admins.json` with permissions
4. Run: `python main.py`
- `!status` — show connection status for all bots
- `!help` — print the command list
- `!exit` — shut down all bots cleanly

## Configuration

Edit `config/bots.json` to add, remove, or update bot definitions.

## VS Code Compatibility

A `.vscode/settings.json` file is included to configure Python analysis and interpreter support.

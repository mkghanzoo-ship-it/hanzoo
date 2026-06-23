# Python Multi-Bot Manager

A Python 3.11+ multi-bot manager application that runs several bot clients in parallel with shared command handling.

## Features

- Multiple bots managed from one script
- Asynchronous command handling with `asyncio`
- Shared command prefix: `!`
- Commands: `!say`, `!follow`, `!stop`, `!jump`, `!spam`, `!status`, `!help`, `!exit`
- Automatic reconnect when a bot disconnects
- Configurable bot profiles in `config/bots.json`
- Logging and error handling

## Requirements

- Python 3.11 or newer
- No external dependencies required

## Setup

1. Open the workspace in VS Code.
2. Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install requirements (none required for this project, but this command ensures the environment is prepared):

```powershell
pip install -r requirements.txt
```

## Running

From the workspace root:

```powershell
python main.py
```

## Commands

- `!say <message>` — all connected bots repeat the message
- `!follow <target>` — all bots follow the specified target
- `!stop` — all bots stop their current action
- `!jump` — all bots perform a jump action
- `!spam <count> <message>` — all bots send the message repeatedly
- `!status` — show connection status for all bots
- `!help` — print the command list
- `!exit` — shut down all bots cleanly

## Configuration

Edit `config/bots.json` to add, remove, or update bot definitions.

## VS Code Compatibility

A `.vscode/settings.json` file is included to configure Python analysis and interpreter support.

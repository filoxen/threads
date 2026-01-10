# clothing-upload-bot

A FastAPI service for reuploading clothing assets to Roblox groups, used in *Filoxen Research Facilities*. This app fetches clothing from existing Roblox assets and reuploads them to a target group.

## Prerequisites

- Python 3.13+
- `uv` (install from [astral.sh/uv](https://astral.sh/uv))
- Valid Roblox `ROBLOSECURITY` cookie in your environment

## Installation

Clone the repository and install dependencies with `uv`:

```bash
uv sync
```

This will create a virtual environment and install all required packages.

## Configuration

Create a `.env` file in the project root with the following variables:

```
TARGET_ID=<group_id>               # The Roblox group ID to upload clothing to
VALID_API_KEY=<your_api_key>       # API key for authorizing requests to this service
ROBLOSECURITY_TOKEN=<cookie>       # Your Roblox roblosecurity cookie
PUBLISHER_USER_ID=<user_id>        # The Roblox user ID for the cookie
DISCORD_WEBHOOK_URL=<url>          # (Optional) Discord webhook for upload notifications
```

**Important:** `PUBLISHER_USER_ID` must match the user ID of the account that owns the `ROBLOSECURITY_TOKEN`.

## Running

### Development Server
Start the development server with hot-reload (listens on `127.0.0.1` only):

```bash
uv run fastapi dev src/main.py
```

### Production Server
Start the production server (listens on `0.0.0.0`):

```bash
uv run fastapi run src/main.py
```

The server will run on port 8000 by default.

## Project Structure

```
src/
├── main.py        # FastAPI application and endpoints
├── models.py      # Data models for Roblox assets
├── database.py    # SQLite database layer for duplicate tracking
└── utils/         # Utility modules
    ├── roblox_service.py
    ├── hashing.py
    └── discord.py
```

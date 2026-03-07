# Threads

A FastAPI service for reuploading clothing assets to Roblox groups, used in *Filoxen Research Facilities*. This app fetches clothing from existing Roblox assets, reuploads them to a target group, and automatically puts them on sale.

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

Create a `.env` file in the project root (see `.env.example`):

```
TARGET_ID=<group_id>               # The Roblox group ID to upload clothing to
VALID_API_KEY=<your_api_key>       # API key for authorizing requests to this service
ROBLOSECURITY_TOKEN=<cookie>       # Your Roblox roblosecurity cookie
PUBLISHER_USER_ID=<user_id>        # The Roblox user ID for the cookie
DISCORD_WEBHOOK_URL=<url>          # (Optional) Discord webhook for upload notifications
```

**Important:** `PUBLISHER_USER_ID` must match the user ID of the account that owns the `ROBLOSECURITY_TOKEN`.

### Separate onsale account

You can optionally use a different Roblox account for putting items on sale. If not set, the upload account is used for both.

```
ONSALE_ROBLOSECURITY_TOKEN=<cookie>   # Roblox cookie for the onsale account
ONSALE_PUBLISHER_USER_ID=<user_id>    # User ID for the onsale account
```

### Other optional settings

```
ROBLOX_PROXY=<url>                 # Proxy for Roblox APIs (e.g., roproxy.com)
RETRY_INTERVAL_SECONDS=60          # How often to check the onsale retry queue (default: 60)
RETRY_DELAY_SECONDS=300            # Delay before retrying a failed onsale (default: 300)
```

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

## API Endpoints

All endpoints require an `x-api-key` header matching `VALID_API_KEY`.

### `GET /asset/{asset_id}`

Fetch info about a Roblox asset.

### `POST /create/?asset_id={asset_id}`

Reupload a clothing asset to the target group. The service will:

1. Fetch the original asset and its image
2. Deduplicate by image hash (returns existing upload if already processed)
3. Upload the clothing image to the target group
4. Wait 5 seconds, then put the item on sale
5. If rate-limited, queue the onsale for automatic retry
6. Send a Discord webhook notification on success

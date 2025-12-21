# clothing-upload-bot

A FastAPI service for reuploading clothing assets to Roblox groups, used in *Filoxen Research Facilities*. This app fetches clothing from existing Roblox assets and reuploads them to a target group.

## Disclaimer

This tool uses Roblox's APIs in a way that violates their Terms of Service. Roblox may moderate or ban accounts that use this. Use at your own risk.
This is beta software with potential issues. It's generally a good idea to not run it if you do not understand the source code.

## Prerequisites

- Python 3.13+
- `uv` (install from [astral.sh/uv](https://astral.sh/uv))
- Valid Roblox `roblosecurity` cookie in your environment

## Installation

Clone the repository and install dependencies with `uv`:

```bash
uv sync
```

This will create a virtual environment and install all required packages.

## Configuration

Create a `.env` file in the project root with the following variables:

```
TARGET_ID=<group_id>           # The Roblox group ID to upload clothing to
VALID_API_KEY=<your_api_key>   # API key for authorizing requests to this service
ROBLOSECURITY=<cookie>         # Your Roblox roblosecurity cookie (only needed for authed APIs)
```

## Running

Start the FastAPI server:

```bash
uv run fastapi run src/main.py
```

The server will run on `http://0.0.0.0:8000` by default.

## Usage

Make authenticated requests using the `x-api-key` header:

```bash
curl -H "x-api-key: your_api_key" http://localhost:8000/asset/{asset_id}
```

# WhatsApp MCP Bridge

A lightweight bridge that connects WhatsApp via Node.js (`whatsapp-web.js` + Express) to a Python tool interface (FastMCP). It exposes simple HTTP endpoints to send messages and fetch recent chats, and provides Python tools for easy programmatic use.

## Features

- Send WhatsApp messages and fetch recent messages via HTTP endpoints
- QR-based local auth with session caching (no re-scan each run once cached)
- Python FastMCP tools to interact programmatically
- Minimal setup, runs locally by default

## Architecture

- Node.js server (`index.js`):
  - Uses `whatsapp-web.js` with `LocalAuth` for session storage
  - Exposes Express endpoints on `http://localhost:3000`
- Python tools (`main.py`):
  - Uses `fastmcp` and `httpx` to call the Node server
  - Provides tools: `send_message`, `get_recent_messages`, `get_conversation`

## Requirements

- Node.js 18+
- Python 3.9+

## Setup

Important: `node_modules` are not committed. Be sure to install dependencies locally.

### 1) Install Node dependencies

```bash
npm install
```

This installs:

- `express`
- `whatsapp-web.js`
- `qrcode-terminal`
- `sqlite3`

### 2) Install Python dependencies

Using `uv` (recommended):

```bash
uv sync
```

Or using `pip`:

```bash
pip install -r requirements.txt
```

This installs:

- `fastmcp`
- `httpx`

### 3) Environment

Optional, defaults to the local server:

```bash
# Python tools talk to the Node server
set NODE_BASE_URL=http://localhost:3000  # Windows PowerShell
# export NODE_BASE_URL=http://localhost:3000  # macOS/Linux
```

## Running

### Start the Node server (Express + whatsapp-web.js)

```bash
node index.js
```

- On first run, a QR code is printed to the terminal. Scan it with your WhatsApp app.
- Session is cached locally via `LocalAuth` so you won’t need to re-scan each time.
- Server listens on `http://localhost:3000`.

### Start the Python FastMCP server (optional)

```bash
# uv (recommended)
uv run fastmcp run ./main.py

# or with Python directly (ensure deps installed)
python ./main.py
```

This exposes MCP tools that call the Node server.

## HTTP API

Base URL: `http://localhost:3000`

- GET `/mcp/get_recent_messages`

  - Query: `to` (phone or WhatsApp ID) OR `chatId`, optional `limit` (1-50, default 10)
  - Returns latest text messages for the chat
- POST `/mcp/send_message`

  - JSON body: `{ "to": "<phone or WhatsApp ID>", "text": "<message>" }`
  - Sends a message to the given recipient

### Examples

Fetch recent messages (last 10) by phone number:

```bash
curl "http://localhost:3000/mcp/get_recent_messages?to=15551234567&limit=10"
```

Send a message:

```bash
curl -X POST "http://localhost:3000/mcp/send_message" \
  -H "Content-Type: application/json" \
  -d '{"to":"15551234567","text":"Hello from MCP!"}'
```

## Python MCP Tools

Available when running `main.py`:

- `send_message(to, text|message, include_context=True)`
- `get_recent_messages(to|chatId, limit=10)`
- `get_conversation(to|chatId, limit=10)`

They normalize phone numbers like `15551234567` to WhatsApp IDs like `15551234567@c.us` when needed.

## Using with Claude Desktop (optional)

Example tool configuration snippet:

```json
"whatsapp-mcp": {
  "command": "C:\\Users\\leoli\\.local\\bin\\uv",
  "args": [
    "run",
    "--with",
    "fastmcp",
    "fastmcp",
    "run",
    "C:\\Users\\leoli\\Desktop\\whatsapp\\main.py"
  ],
  "env": {
    "NODE_BASE_URL": "http://localhost:3000"
  }
}
```

## Notes & Tips

- If you see “WhatsApp client not ready”, ensure you’ve scanned the QR and the session is active.
- For group chats, use a `@g.us` chat ID.
- Keep your terminal open while the server is running; closing it will disconnect the session.

## License

The project currently declares `ISC` in `package.json`. If you prefer MIT wording, you can switch by:

- Updating `package.json` to `"license": "MIT"`
- Adding a `LICENSE` file with the MIT text
- Keeping a brief license note in this README

---

Made for local workflows and experimentation. PRs welcome!

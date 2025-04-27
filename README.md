# Server + Client Setup Instructions

## Server Machine Setup

1. Ensure Python 3.12+ and `uv` are installed.
2. Navigate to your project folder.
3. Ensure your database is configured at `~/scouting_data/app.db`.
4. Start the server with:

```bash
uv run uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

5. Make sure port 8000 is open on the server firewall.
6. Server now listens on the network (e.g., 192.168.1.123:8000).

## Client Machine Setup

1. Install Python 3.12+ and uv.
2. Copy the project folder (only need the client part).
3. Edit settings.toml:
```bash
[server]
host = "192.168.1.123"
port = 8000
```
(Change host to match server IP.)
4. Start the client:
```bash
PYTHONPATH=. uv run -m client.main
```
5. Client GUI will show connection status.

# Systemd deployment for Daily Tracker

This project is already designed for environment-based configuration and a persistent local database path. The example below shows a production-style systemd unit for a Linux deployment.

## 1. Prepare the service environment

Create or update a `.env` file in the project root with the required runtime configuration:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_PATH=/var/lib/daily-tracker/tracker.db
```

Optional values:

```env
WELCOME_STICKER_ID=
SUCCESS_STICKER_ID=
ERROR_STICKER_ID=
```

The bot reads configuration from environment variables via `python-dotenv` on startup, so the service can load the project root `.env` file without needing code changes.

## 2. Example systemd unit

Create `/etc/systemd/system/tracker.service`:

```ini
[Unit]
Description=Daily Tracker Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/daily-tracker
EnvironmentFile=/opt/daily-tracker/.env
User=tracker
Group=tracker
ExecStart=/opt/daily-tracker/venv/bin/python /opt/daily-tracker/bot.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## 3. Recommended deployment layout

Example filesystem layout:

```text
/opt/daily-tracker/
├── bot.py
├── config.py
├── .env
├── requirements.txt
├── requirements-dev.txt
├── venv/
├── logs/
└── ...
```

Use a persistent database path such as:

```text
/var/lib/daily-tracker/tracker.db
```

This keeps the SQLite database outside the source checkout so it survives application updates and is easier to back up.

## 4. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable tracker.service
sudo systemctl start tracker.service
```

## 5. Check status and logs

```bash
sudo systemctl status tracker.service
sudo journalctl -u tracker.service -f
```

## 6. Notes for future Docker readiness

This setup is already close to container-friendly behavior because:

- configuration is read from environment variables
- the database path is configurable via `DATABASE_PATH`
- logging can be directed to stdout/stderr when containerized
- runtime files are kept in clearly separated locations such as `/var/lib/daily-tracker` and `/opt/daily-tracker/logs`

No Dockerfile is added here; this is intentionally kept as a deployment example only.

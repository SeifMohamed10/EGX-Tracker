# EGX Tracker — Deployment Guide

Local dev (this machine), Windows:

    py -m pip install -r requirements.txt
    py -m streamlit run app.py --server.port 8510 --server.headless true

Optional shell-rob win: set `EGX_SHELL_ROB=1` to re-enable the winsound alert block (the code no-ops silently on failure on any other OS).

## Storage notes

- Data lives in SQLite: `db/history.sqlite` (created on first run by `storage/db.py`).
- Secrets/settings are plain SQLite rows — nothing cloud-hosted, no API keys needed by default (TradingView streaming widget is public/embeddable).
- If deploying from a synced folder (OneDrive/Dropbox), SQLite can accumulate -wal/-shm files that conflict with sync. Prefer a local checkout, or set a dedicated data dir env before managing db paths (`storage/db.py` is the single place to change).

## Option A: streamlit Cloud (fastest, free tier)

1. Push this folder to a GitHub repo.
2. streamlit.app → New app → pick repo/branch/main → entry point `app.py`.
3. On Community Cloud SQLite writes are read-local and ephemeral (container resets periodicly). If you already deply with persistent data, attach it via a small storage add-on volume or use a tiny Postgres backend instead — swap `storage/db.py` for a `psycopg2` version with same function names.
4. Windows-only `winsound` (sound trigger) is wrapped in try/except — it no-ops on Linux, app still runs.

## Option B: Docker + any VPS (fully controlled)

1. Dockerfile in project root:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV EGX_SHELL_ROB=0
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
```

2. Build & run on the server:
   `docker build -t egx-tracker . && docker run -d --name egx -p 8501:8501 -v egx_data:/app/data egx-tracker`
3. Reverse proxy with HTTPS in front (Nginx/Caddy). The TradingView widget embed is an iframe over `https://` so make sure the site is HTTPS or the widget may get blocked.

## Option C: Bare VPS, systemd + nginx

    py -m pip install -U pip && pip install -r requirements.txt
    streamlit run app.py --server.port 8501 --server.headless true  # test once
    # then a systemd unit like:
    [Unit]
    Description=EGX tracker
    [Service]
    WorkingDirectory=/opt/egx-tracker
    ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port 8501 --server.headless true
    Restart=always
    [Install]
    WantedBy=multi-user.target

## Checklist before any deploy

- [ ] `requirements.txt` includes `streamlit_autorefresh` (auto-refresh on Overview + Market News tabs).
- [ ] No hardcoded Windows paths in `storage/db.py` / `data/*` that would break on Linux.
- [ ] `winsound` alert block properly guarded (try/except) — app must run headless without audio.
- [ ] EGX live prices depend on RMS/network scraping; on a server outside Egypt some market-data endpoints rate-limit or geo-block. Test `data/live.py::get_quotes` from the deploy region before promising uptime.
- [ ] TradingView chart iframe works only if outbound network to `tradingview.com` is open from the browser (client-side, not server-side).
- [ ] Set Streamlit server config via CLI flags or `.streamlit/config.toml` (port, maxUploadSize small — app has no big uploads).

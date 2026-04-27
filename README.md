# YouTube Auto-Subscribe

Bulk-subscribe to a list of YouTube channels using the YouTube Data API v3. Progress is tracked in a Supabase database so runs can be safely interrupted and resumed.

## Requirements

- Python 3
- A Google Cloud project with the YouTube Data API v3 enabled and OAuth 2.0 credentials
- A [Supabase](https://supabase.com) project for backend data storage

## Setup

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Google OAuth credentials

Download your OAuth 2.0 client credentials from the [Google Cloud Console](https://console.cloud.google.com/) and save the file as `client_secret.json` in the project root.

### 3. Supabase backend

This project uses Supabase to store channel data and track subscription progress. You need to create the `channels` table in your Supabase project.

**Using Supabase MCP (recommended):** Connect the [Supabase MCP server](https://supabase.com/docs/guides/getting-started/mcp) to Claude Code and run:

```sql
create table channels (
  id            uuid        default gen_random_uuid() primary key,
  channel_id    text        unique not null,
  title         text,
  status        text        default 'pending'
                            check (status in ('pending', 'subscribed', 'duplicate', 'error')),
  processed_at  timestamptz,
  created_at    timestamptz default now()
);
```

**Alternatively**, run the SQL above directly in the Supabase dashboard → SQL Editor.

### 4. Environment variables

Get your project URL and anon key from **Supabase dashboard → Settings → API**:

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_KEY="<your-anon-key>"
```

### 5. Add channels

Populate `subscriptions.csv` with the channels you want to subscribe to. The file should have these columns:

```
Channel ID,Channel title
UCxxxxxxxxxxxxxxxxxxxxxx,Channel Name
```

### 6. Seed the database (one-time)

If migrating from an existing `subscriptions.csv` (and optionally a `progress.txt`):

```bash
python3 migrate.py
```

## Usage

```bash
python3 subscribe.py
```

The script will:
- Load all channels from Supabase
- Skip channels already marked as `subscribed` or `duplicate`
- Subscribe to remaining channels and update their status in real time
- Stop gracefully if the YouTube API quota is exceeded — re-run the next day to continue

## Files

| File | Description |
|---|---|
| `subscribe.py` | Main script |
| `migrate.py` | One-time migration: seeds Supabase from `subscriptions.csv` and `progress.txt` |
| `subscriptions.csv` | Source list of YouTube channel IDs |
| `client_secret.json` | Google OAuth credentials (not committed) |
| `token.json` | Google OAuth token, auto-generated (not committed) |

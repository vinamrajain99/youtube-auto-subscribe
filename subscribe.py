import os
import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from supabase import create_client

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"ERROR: '{CLIENT_SECRET_FILE}' not found.")
                print("Download OAuth 2.0 credentials from Google Cloud Console and place it here.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def load_channels():
    rows = supabase.table("channels").select("channel_id, title").execute()
    return [(r["channel_id"], r["title"] or "") for r in rows.data]


def load_progress():
    rows = (
        supabase.table("channels")
        .select("channel_id")
        .neq("status", "pending")
        .execute()
    )
    return {r["channel_id"] for r in rows.data}


def save_progress(channel_id, status="subscribed"):
    supabase.table("channels").update(
        {"status": status, "processed_at": "now()"}
    ).eq("channel_id", channel_id).execute()


def main():
    creds = authenticate()
    youtube = build("youtube", "v3", credentials=creds)

    channels = load_channels()
    processed = load_progress()
    print(f"Loaded {len(channels)} channels from Supabase")
    print(f"Already processed (will skip): {len(processed)}\n")

    subscribed = 0
    skipped = 0
    errors = 0

    for i, (channel_id, title) in enumerate(channels, 1):
        label = title or channel_id
        if channel_id in processed:
            print(f"[{i}/{len(channels)}] Skipping (already processed): {label}")
            continue
        try:
            youtube.subscriptions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "resourceId": {
                            "kind": "youtube#channel",
                            "channelId": channel_id,
                        }
                    }
                },
            ).execute()
            print(f"[{i}/{len(channels)}] Subscribed: {label}")
            subscribed += 1
            save_progress(channel_id, "subscribed")
        except HttpError as e:
            if e.status_code in (409, 400) and "subscriptionDuplicate" in str(e):
                print(f"[{i}/{len(channels)}] Already subscribed: {label}")
                skipped += 1
                save_progress(channel_id, "duplicate")
            elif e.status_code == 403:
                reason = ""
                if e.error_details:
                    reason = e.error_details[0].get("reason", "")
                if reason == "quotaExceeded":
                    print(f"\nQuota exceeded after {subscribed} new subscriptions.")
                    print("Re-run tomorrow — already-processed channels will be skipped automatically.")
                    break
                else:
                    print(f"[{i}/{len(channels)}] Forbidden ({reason}): {label}")
                    errors += 1
                    save_progress(channel_id, "error")
            else:
                print(f"[{i}/{len(channels)}] Error {e.status_code}: {label} — {e}")
                errors += 1
                save_progress(channel_id, "error")

    print(f"\nDone. Subscribed: {subscribed} | Already subscribed (skipped): {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()

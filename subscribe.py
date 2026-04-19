import csv
import os
import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CSV_FILE = "subscriptions.csv"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"
PROGRESS_FILE = "progress.txt"


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def save_progress(channel_id):
    with open(PROGRESS_FILE, "a") as f:
        f.write(channel_id + "\n")


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
    channels = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channel_id = row.get("Channel ID", "").strip()
            title = row.get("Channel title", "").strip()
            if channel_id:
                channels.append((channel_id, title))
    return channels


def main():
    creds = authenticate()
    youtube = build("youtube", "v3", credentials=creds)

    channels = load_channels()
    processed = load_progress()
    print(f"Loaded {len(channels)} channels from {CSV_FILE}")
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
            save_progress(channel_id)
        except HttpError as e:
            if e.status_code in (409, 400) and "subscriptionDuplicate" in str(e):
                print(f"[{i}/{len(channels)}] Already subscribed: {label}")
                skipped += 1
                save_progress(channel_id)
            elif e.status_code == 403:
                reason = ""
                if e.error_details:
                    reason = e.error_details[0].get("reason", "")
                if reason == "quotaExceeded":
                    print(f"\nQuota exceeded after {subscribed} new subscriptions.")
                    print("Re-run tomorrow — already-subscribed channels will be skipped automatically.")
                    break
                else:
                    print(f"[{i}/{len(channels)}] Forbidden ({reason}): {label}")
                    errors += 1
            else:
                print(f"[{i}/{len(channels)}] Error {e.status_code}: {label} — {e}")
                errors += 1

    print(f"\nDone. Subscribed: {subscribed} | Already subscribed (skipped): {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()

import csv
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_FILE = "subscriptions.csv"
PROGRESS_FILE = "progress.txt"


def load_csv_channels():
    channels = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channel_id = row.get("Channel ID", "").strip()
            title = row.get("Channel title", "").strip() or None
            if channel_id:
                channels.append({"channel_id": channel_id, "title": title, "status": "pending"})
    return channels


def load_progress_ids():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def main():
    channels = load_csv_channels()
    print(f"Loaded {len(channels)} channels from {CSV_FILE}")

    # Upsert all channels with status=pending (won't overwrite existing status)
    batch_size = 100
    inserted = 0
    for i in range(0, len(channels), batch_size):
        batch = channels[i:i + batch_size]
        supabase.table("channels").upsert(batch, on_conflict="channel_id", ignore_duplicates=True).execute()
        inserted += len(batch)
        print(f"  Upserted {inserted}/{len(channels)}")

    # Mark already-processed channels from progress.txt as 'subscribed'
    processed = load_progress_ids()
    print(f"\nMarking {len(processed)} channels from {PROGRESS_FILE} as 'subscribed'")
    for i, channel_id in enumerate(processed, 1):
        supabase.table("channels").update({"status": "subscribed"}).eq("channel_id", channel_id).execute()
        if i % 50 == 0:
            print(f"  Updated {i}/{len(processed)}")

    print("\nMigration complete.")
    print(f"  Total channels: {len(channels)}")
    print(f"  Pre-marked as subscribed: {len(processed)}")
    print(f"  Remaining pending: {len(channels) - len(processed)}")


if __name__ == "__main__":
    main()

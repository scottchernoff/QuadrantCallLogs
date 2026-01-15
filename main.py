import os
import requests
import pandas as pd
from datetime import datetime, timezone

# -------------------------------
# CONFIGURATION
# -------------------------------

# Your Zoom Account ID (replace with your actual ID)
ZOOM_ACCOUNT_ID = "no1aFaVMQsSbU6exGpf2lA"

# Get Client ID and Secret from environment variables (GitHub Actions or local .env)
ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET")

# CSV output path
CSV_PATH = "external_outbound_calls.csv"

# -------------------------------
# FUNCTIONS
# -------------------------------

def get_access_token():
    """Get a fresh Server-to-Server OAuth token from Zoom"""
    url = "https://zoom.us/oauth/token?grant_type=client_credentials"
    # Use HTTPBasicAuth for S2S OAuth
    r = requests.post(url, auth=requests.auth.HTTPBasicAuth(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET))
    r.raise_for_status()
    token_data = r.json()
    print("Access token retrieved successfully")
    return token_data["access_token"]

def get_users(token):
    """Get all users in the Zoom account"""
    url = "https://api.zoom.us/v2/users"
    headers = {"Authorization": f"Bearer {token}"}
    users = []
    page_number = 1

    while True:
        params = {"page_size": 300, "page_number": page_number}
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        users.extend(data.get("users", []))
        if page_number * 300 >= data.get("total_records", 0):
            break
        page_number += 1
    print(f"Retrieved {len(users)} users")
    return users

def get_call_logs(token, account_id, start_date, end_date):
    """Get all external outbound calls for each user in the account"""
    url = "https://api.zoom.us/v2/phone/call_logs"
    headers = {"Authorization": f"Bearer {token}"}
    all_calls = []

    users = get_users(token)
    for user in users:
        user_id = user["id"]
        page_number = 1
        while True:
            params = {
                "account_id": account_id,
                "user_id": user_id,
                "from": start_date + "T00:00:00Z",
                "to": end_date + "T23:59:59Z",
                "direction": "outbound",
                "call_type": "external",
                "page_size": 300,
                "page_number": page_number
            }
            r = requests.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            calls = data.get("call_logs", [])
            if not calls:
                break
            all_calls.extend(calls)
            if page_number * 300 >= data.get("total_records", 0):
                break
            page_number += 1

    print(f"Total external outbound calls retrieved: {len(all_calls)}")
    return all_calls

def aggregate_per_user(calls):
    """Aggregate total calls and total talk time per user"""
    if not calls:
        print("No calls found for today.")
        return

    df = pd.DataFrame(calls)

    # Ensure caller_name column exists
    if "caller_name" not in df.columns:
        df["caller_name"] = df.get("caller_id", "Unknown")

    summary = df.groupby("caller_name").agg(
        total_calls=pd.NamedAgg(column="id", aggfunc="count"),
        total_talk_time=pd.NamedAgg(column="duration", aggfunc="sum")
    ).reset_index()

    summary.to_csv(CSV_PATH, index=False)
    print(f"Aggregated call data saved to {CSV_PATH}")

# -------------------------------
# MAIN
# -------------------------------

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    token = get_access_token()
    calls = get_call_logs(token, ZOOM_ACCOUNT_ID, today, today)
    aggregate_per_user(calls)

if __name__ == "__main__":
    main()

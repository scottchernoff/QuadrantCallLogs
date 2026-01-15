import requests
import os
import pandas as pd
from datetime import datetime

# --- 1. Get access token from Zoom ---
def get_access_token():
    client_id = os.getenv("ZOOM_CLIENT_ID")
    client_secret = os.getenv("ZOOM_CLIENT_SECRET")

    import base64
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    token_url = "https://zoom.us/oauth/token?grant_type=client_credentials"
    r = requests.post(token_url, headers={"Authorization": f"Basic {encoded_credentials}"})
    r.raise_for_status()
    return r.json()["access_token"]

# --- 2. Get today's external outbound call logs ---
def get_call_logs():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    today = datetime.utcnow().strftime("%Y-%m-%d")
    page_number = 1
    page_size = 300
    all_calls = []

    while True:
        url = (
            f"https://api.zoom.us/v2/phone/call_logs?"
            f"from={today}&to={today}&type=outbound&page_size={page_size}&page_number={page_number}"
        )
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        if "call_logs" not in data:
            break
        all_calls.extend(data["call_logs"])
        if len(data["call_logs"]) < page_size:
            break
        page_number += 1

    # Filter for external calls
    external_calls = [c for c in all_calls if c.get("callee_number_source") == "external"]
    return external_calls

# --- 3. Aggregate per user ---
def aggregate_per_user(calls):
    if not calls:
        print("No external calls today")
        return
    df = pd.DataFrame(calls)
    df["caller_name"] = df["caller_name"].fillna("Unknown")
    summary = df.groupby("caller_name").agg(
        total_calls=pd.NamedAgg(column="id", aggfunc="count"),
        total_talk_time=pd.NamedAgg(column="duration", aggfunc="sum"),
        department=pd.NamedAgg(column="department", aggfunc=lambda x: x.mode()[0] if not x.mode().empty else "")
    ).reset_index()
    return summary

# --- 4. Save CSV ---
def save_csv(df):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    file_path = f"data/external_outbound_calls_{today}.csv"
    df.to_csv(file_path, index=False)
    print(f"Saved {len(df)} external outbound calls to {file_path}")

# --- 5. Main ---
def main():
    calls = get_call_logs()
    summary = aggregate_per_user(calls)
    if summary is not None:
        save_csv(summary)

if __name__ == "__main__":
    main()

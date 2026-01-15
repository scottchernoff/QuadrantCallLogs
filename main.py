import os
import base64
import requests
import pandas as pd
from datetime import datetime, timezone

# --- 1️⃣ Get access token ---
def get_access_token():
    client_id = os.getenv("ZOOM_CLIENT_ID")
    client_secret = os.getenv("ZOOM_CLIENT_SECRET")

    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    token_url = "https://zoom.us/oauth/token?grant_type=client_credentials"
    r = requests.post(token_url, headers={"Authorization": f"Basic {encoded_credentials}"})
    r.raise_for_status()
    return r.json()["access_token"]

# --- 2️⃣ Get today's external outbound call logs ---
def get_call_logs():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Today in ISO8601
    today = datetime.now(timezone.utc)
    from_time = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    to_time = today.replace(hour=23, minute=59, second=59, microsecond=0).isoformat().replace("+00:00", "Z")

    all_calls = []
    page_number = 1
    page_size = 300

    while True:
        url = (
            f"https://api.zoom.us/v2/phone/call_logs?"
            f"from={from_time}&to={to_time}&direction=outbound&call_type=external"
            f"&page_size={page_size}&page_number={page_number}"
        )
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "call_logs" not in data or not data["call_logs"]:
            break

        all_calls.extend(data["call_logs"])

        # If fewer than page_size, we are done
        if len(data["call_logs"]) < page_size:
            break

        page_number += 1

    print(f"Total external outbound calls today: {len(all_calls)}")
    return all_calls

# --- 3️⃣ Aggregate per user ---
def aggregate_per_user(calls):
    if not calls:
        print("No external calls today")
        return None

    df = pd.DataFrame(calls)
    df["caller_name"] = df["caller_name"].fillna("Unknown")
    df["department"] = df.get("department", "")  # Some calls may not have department

    summary = df.groupby("caller_name").agg(
        total_calls=pd.NamedAgg(column="id", aggfunc="count"),
        total_talk_time=pd.NamedAgg(column="duration", aggfunc="sum"),
        department=pd.NamedAgg(column="department", aggfunc=lambda x: x.mode()[0] if not x.mode().empty else "")
    ).reset_index()

    return summary

# --- 4️⃣ Save to CSV ---
def save_csv(df):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = f"data/external_outbound_calls_{today_str}.csv"
    df.to_csv(file_path, index=False)
    print(f"Saved aggregated call data to {file_path}")

# --- 5️⃣ Main ---
def main():
    calls = get_call_logs()
    summary = aggregate_per_user(calls)
    if summary is not None:
        save_csv(summary)

if __name__ == "__main__":
    main()

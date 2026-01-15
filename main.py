import os
import base64
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

# -------------------------------
# 1️⃣ Load .env variables
# -------------------------------
load_dotenv()

ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

if not ZOOM_CLIENT_ID or not ZOOM_CLIENT_SECRET:
    raise Exception("Please set ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET in your .env file")

# -------------------------------
# 2️⃣ Get Server-to-Server OAuth token
# -------------------------------
def get_access_token():
    credentials = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    token_url = "https://zoom.us/oauth/token?grant_type=client_credentials"
    response = requests.post(token_url, headers={"Authorization": f"Basic {encoded}"})

    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise Exception("Access token not returned")
    return token

# -------------------------------
# 3️⃣ Pull external outbound call logs
# -------------------------------
def get_call_logs():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Today in UTC
    now = datetime.now(timezone.utc)
    from_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    to_time = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat().replace("+00:00", "Z")

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
        if response.status_code in [401, 403]:
            raise Exception(f"{response.status_code} error: Check token/scopes/installation")
        
        data = response.json()
        calls = data.get("call_logs", [])
        if not calls:
            break

        all_calls.extend(calls)
        if len(calls) < page_size:
            break

        page_number += 1

    print(f"Fetched {len(all_calls)} external outbound calls for today")
    return all_calls

# -------------------------------
# 4️⃣ Aggregate per user
# -------------------------------
def aggregate_per_user(calls):
    if not calls:
        return pd.DataFrame()

    df = pd.DataFrame(calls)
    df["caller_name"] = df["caller_name"].fillna("Unknown")
    df["department"] = df.get("department", "")

    summary = df.groupby("caller_name").agg(
        total_calls=pd.NamedAgg(column="id", aggfunc="count"),
        total_talk_time=pd.NamedAgg(column="duration", aggfunc="sum"),
        department=pd.NamedAgg(column="department", aggfunc=lambda x: x.mode()[0] if not x.mode().empty else "")
    ).reset_index()

    return summary

# -------------------------------
# 5️⃣ Save CSV (overwrite daily)
# -------------------------------
def save_csv(df, folder="data"):
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "external_outbound_calls_today.csv")
    df.to_csv(file_path, index=False)
    print(f"Saved aggregated call data to {file_path}")

# -------------------------------
# 6️⃣ Main
# -------------------------------
def main():
    try:
        calls = get_call_logs()
        summary = aggregate_per_user(calls)
        if summary.empty:
            print("No external outbound calls found today.")
        else:
            save_csv(summary)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()

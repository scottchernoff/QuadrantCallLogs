import os
import requests
import pandas as pd
from datetime import datetime, timezone

# ===========================
# Configuration
# ===========================
ZOOM_ACCESS_TOKEN = os.getenv("ZOOM_ACCESS_TOKEN")  # GitHub Secret
OUTPUT_FOLDER = "data"  # CSV folder in repo

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ===========================
# Helper functions
# ===========================
def get_call_logs():
    """Fetch all call logs for today, external outbound only"""
    today = datetime.now(timezone.utc).date()
    url = "https://api.zoom.us/v2/phone/call_logs"
    headers = {"Authorization": f"Bearer {ZOOM_ACCESS_TOKEN}"}
    
    params = {
        "page_size": 300,  # Zoom max per request
        "from": today.isoformat(),
        "to": today.isoformat(),
        "type": "outbound"
    }

    all_calls = []
    page_number = 1
    while True:
        params["page_number"] = page_number
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        all_calls.extend(data.get("call_logs", []))
        if page_number >= data.get("total_pages", 1):
            break
        page_number += 1

    # Filter for external outbound calls
    external_calls = [c for c in all_calls if c.get("callee_number_source") == "external"]
    return external_calls

def get_user_department(user_id):
    """Fetch department for a user via Zoom API"""
    url = f"https://api.zoom.us/v2/users/{user_id}"
    headers = {"Authorization": f"Bearer {ZOOM_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("department", "Unknown")
    else:
        return "Unknown"

def aggregate_per_user(calls):
    """Aggregate call counts and talk time per user, include department"""
    df = pd.DataFrame(calls)
    if df.empty:
        return pd.DataFrame()  # no calls today

    # Add department
    df["department"] = df["user_id"].apply(get_user_department)

    # Aggregate
    summary = df.groupby(["caller_name", "department"]).agg(
        total_outbound=pd.NamedAgg(column="id", aggfunc="count"),
        total_talk_time=pd.NamedAgg(column="duration", aggfunc="sum")
    ).reset_index()
    return summary

def save_csv(df):
    """Save the daily CSV in the data folder"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"external_outbound_calls_{today_str}.csv"
    path = os.path.join(OUTPUT_FOLDER, filename)
    df.to_csv(path, index=False)
    print(f"✅ Saved {len(df)} rows to {path}")
    return path

# ===========================
# Main execution
# ===========================
def main():
    calls = get_call_logs()
    print(f"Total external outbound calls today: {len(calls)}")
    df_summary = aggregate_per_user(calls)
    if not df_summary.empty:
        save_csv(df_summary)
    else:
        print("No external outbound calls found today.")

if __name__ == "__main__":
    main()

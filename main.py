import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

def get_access_token():
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "account_credentials",
        "account_id": ACCOUNT_ID
    }

    response = requests.post(
        url,
        params=params,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )

    response.raise_for_status()
    return response.json()["access_token"]

if __name__ == "__main__":
    token = get_access_token()
    print("Access token received:", token[:20], "...")

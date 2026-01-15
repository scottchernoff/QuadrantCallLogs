import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

def get_access_token():
    # Include account_id in query string, not body
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}"

    # Basic Auth handled by requests
    response = requests.post(url, auth=HTTPBasicAuth(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET))

    if response.status_code != 200:
        print("TOKEN ERROR RESPONSE:", response.text)
        response.raise_for_status()

    token = response.json()["access_token"]
    print("Access token retrieved:", token[:20], "...")
    return token

if __name__ == "__main__":
    token = get_access_token()

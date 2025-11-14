import requests
import json
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_ID = os.getenv("APP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
TOKEN_FILE = "tokens.json"

# Đọc refresh_token từ file JSON
def load_tokens():
    """Load tokens from the tokens.json file."""
    try:
        with open(TOKEN_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("❌ Token file not found.")
        return None
    except json.JSONDecodeError:
        print("❌ Error decoding token file.")
        return None

# Ghi lại token mới vào file
def save_tokens(tokens):
    """Save updated tokens to the tokens.json file."""
    with open(TOKEN_FILE, "w") as file:
        json.dump(tokens, file, indent=2)

# Hàm refresh_token
def refresh_oa_token(tokens):
    """Refresh the token for the OA."""
    # Lấy refresh_token từ file
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("❌ No refresh_token found in tokens.json")
        return None

    # Gửi yêu cầu POST đến Zalo API để refresh token
    url = "https://oauth.zaloapp.com/v4/oa/access_token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "secret_key": SECRET_KEY
    }
    # Dữ liệu gửi đi
    data = {
        "app_id": APP_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    # Gửi yêu cầu
    response = requests.post(url, headers=headers, data=urlencode(data))
    # Kiểm tra mã trạng thái phản hồi
    if response.status_code == 200:
        result = response.json()
        if "error" in result:
            print(f"❌ Error refreshing token: {result['error']}")
            return None
        else:
            print(result)  # Print the entire response
            print("✅ Token refreshed successfully")
            return {
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "expires_in": result.get("expires_in")
            }
    else:
        print(f"❌ Error refreshing token, Status: {response.status_code}")
        print(response.text)
        return None

# Hàm chính để refresh token
def refresh_token():
    """Refresh token for the single OA."""
    tokens = load_tokens()
    if not tokens:
        print("❌ No tokens to refresh.")
        return

    updated_tokens = refresh_oa_token(tokens)
    if updated_tokens:
        save_tokens(updated_tokens)
        print("✅ Token updated successfully.")
    else:
        print("❌ Token refresh failed. Keeping old token.")

if __name__ == "__main__":
    refresh_token()

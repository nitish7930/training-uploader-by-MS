import time
import requests

API_URL = "https://youtube-6kes.onrender.com"

def keep_awake():
    while True:
        try:
            response = requests.get(API_URL)
            print(f"Pinged {API_URL}: {response.status_code}")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(300)  # Wait 10 minutes (adjust if needed)

if __name__ == "__main__":
    keep_awake()
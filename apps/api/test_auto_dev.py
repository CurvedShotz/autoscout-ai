import os

import httpx
from dotenv import load_dotenv


load_dotenv(override=True)

api_key = os.getenv("AUTO_DEV_API_KEY")

if not api_key:
    raise RuntimeError("AUTO_DEV_API_KEY is not set")

response = httpx.get(
    "https://api.auto.dev/vin/WP0AF2A99KS165242",
    params={"apiKey": api_key},
    timeout=10.0,
)

print("Status:", response.status_code)
print(response.json())
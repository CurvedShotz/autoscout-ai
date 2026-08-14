import os

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AUTO_DEV_API_KEY")

if not api_key:
    raise RuntimeError("AUTO_DEV_API_KEY is not set")

response = httpx.get(
    "https://api.auto.dev/listings",
    headers={"Authorization": f"Bearer {api_key}"},
    params={
        "vehicle.make": "Toyota",
        "vehicle.model": "Camry",
        "vehicle.year": "2018-2022",
        "retailListing.price": "1-20000",
        "limit": 5,
    },
)

print("Status:", response.status_code)
print(response.json())
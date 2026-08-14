from app.services.auto_dev_client import AutoDevClient


client = AutoDevClient()

result = client.search_listings(
    make="Toyota",
    model="Camry",
    min_year=2018,
    max_year=2022,
    max_price=20000,
    max_mileage=100000,
    location="75080",
    limit=5,
)

print("Success")
print(result)
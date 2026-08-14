from app.services.auto_dev_client import AutoDevClient


client = AutoDevClient()

result = client.decode_vin("1FTFW3LDXRFB40317")

print("Success")
print(result)
import requests

URL = "http://127.0.0.1:5000/register"

data = {
    "username": "timothy",
    "password": "1234"
}

response = requests.post(
    URL,
    data=data,
    timeout=10
)

print("Status:", response.status_code)
print(response.text)
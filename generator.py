import requests
import random
import json

# =========================
# API Endpoint
# =========================
API_URL = "http://127.0.0.1:5000/predict"

# =========================
# Sample Messages
# =========================
messages = [
    "Congratulations!!! You won a FREE iPhone. Click here now!",
    "Verify your bank account immediately.",
    "URGENT: Your PayPal account has been suspended.",
    "Meeting tomorrow at 10 AM",
    "Dinner tonight?",
    "Your Netflix account has expired.",
    "Claim your reward now!",
    "Free cashback available today only!"
]

# =========================
# Send Messages to API
# =========================
results = []

for msg in messages:

    try:
        response = requests.post(
            API_URL,
            json={"message": msg}
        )

        data = response.json()

        print("=" * 60)
        print("Message:", msg)
        print("Prediction:", data)

        results.append(data)

    except Exception as e:
        print("Error:", e)

# =========================
# Save Results
# =========================
with open("prediction_results.json", "w") as f:
    json.dump(results, f, indent=4)

print("\nResults saved to prediction_results.json")
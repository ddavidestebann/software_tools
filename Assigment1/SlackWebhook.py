"""
Create Slack Webhook

- Go to your Slack workspace.
- Install the app → Incoming Webhooks
- Create a new webhook, choose a channel (#mlalerts).
- Copy the Webhook URL (you’ll need this in code).
"""

## Reference Code

import requests
import time
import SlackWebhook
import os
from dotenv import load_dotenv
 
 
load_dotenv()
 
webhook_url = os.getenv("WEBHOOK_URL")
 
response = requests.post(
    webhook_url,
    json={
        "text": "🚚 MapleFreight test: Slack webhook is working!"
    }
)
 
print(response.status_code)
print(response.text)

# def send_slack_message(message):
#     payload = {"text": message}
#     requests.post(webhook_url, json=payload)

# # Example: Simulate training alerts
# for epoch in range(1, 6):
#     accuracy = 0.7 + epoch * 0.05
#     msg = f"Training Update - Epoch {epoch}: Accuracy = {accuracy:.2f}"
#     send_slack_message(msg)
#     time.sleep(2)  # simulate processing time

# send_slack_message("✅ Training Completed!")

# send_slack_message("💯 Sending new testing message")


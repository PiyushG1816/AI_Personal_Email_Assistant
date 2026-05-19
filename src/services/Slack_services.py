import requests

# Slack Bot Token and Channel
SLACK_TOKEN = ""  # Replace with your actual Slack bot token
SLACK_CHANNEL = "#general"  # Replace with your Slack channel name or ID

# Function to send message to Slack
def send_slack_message(text):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": SLACK_CHANNEL,
        "text": text
    }
    response = requests.post(url, json=data, headers=headers)
    if not response.ok or not response.json().get("ok"):
        print("Failed to send Slack message:", response.text)
    else:
        print("Slack message sent successfully.")

def send_meeting_alert(key_info, email):
    text = (
        f"*Meeting detected*\n"
        f"*Title:* {key_info.meeting_title}\n"
        f"*Date:* {key_info.meeting_date or 'TBD'}\n"
        f"*Time:* {key_info.meeting_time or 'TBD'}\n"
        f"*Duration:* {key_info.meeting_duration_minutes or 60} min\n"
        f"*From:* {email['sender']}\n"
        f"*Subject:* {email['subject']}"
    )
    send_slack_message(text)


def send_priority_alert(email, summary, category, action_required):
    text = (
        f"*High-priority email*\n"
        f"*From:* {email['sender']}\n"
        f"*Subject:* {email['subject']}\n"
        f"*Category:* {category}\n"
        f"*Summary:* {summary}\n"
        f"*Action required:* {action_required}"
    )
    send_slack_message(text)

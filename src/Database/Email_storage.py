import mysql.connector
import os ,sys, re, base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timezone
from bs4 import BeautifulSoup

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
from Gmail_services import authenticate_gmail_api

def get_gmail_service():
    creds = authenticate_gmail_api()
    return build("gmail", "v1", credentials=creds)

def connect_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="Email_assistant"
    )
    return db, db.cursor()

def store_email(data):
    db, cursor = connect_db()
    query = """
        INSERT INTO emails (
            message_id, sender, recipient, subject, timestamp, body, 
            has_attachment, thread_id, summary, priority, category
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sender = VALUES(sender),
            recipient = VALUES(recipient),
            subject = VALUES(subject),
            timestamp = VALUES(timestamp),
            body = VALUES(body),
            has_attachment = VALUES(has_attachment),
            thread_id = VALUES(thread_id),
            summary = VALUES(summary),
            priority = VALUES(priority),
            category = VALUES(category)
    """
    cursor.execute(query, data)
    db.commit()
    cursor.close()
    db.close()

def extract_email_address(recipient_str):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+', recipient_str)
    return emails[0] if emails else recipient_str

def extract_body(payload):
    def extract_parts(parts):
        plain_text = ""
        html_text = ""

        for part in parts:
            mime_type = part.get("mimeType", "")
            body_data = part.get("body", {}).get("data")

            if mime_type == "multipart/alternative" and "parts" in part:
                # Nested parts — handle recursively
                nested_plain, nested_html = extract_parts(part["parts"])
                if nested_plain:
                    plain_text = nested_plain
                elif nested_html:
                    html_text = nested_html

            elif body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                if mime_type == "text/plain":
                    plain_text = decoded
                elif mime_type == "text/html":
                    html_text = decoded

        return plain_text, html_text

    def clean_html(html):
        soup = BeautifulSoup(html, "html.parser")
        if soup.body:
            return soup.body.get_text(separator="\n", strip=True)
        else:
            return soup.get_text(separator="\n", strip=True)

    if "parts" in payload:
        plain, html = extract_parts(payload["parts"])
        if plain:
            return plain
        elif html:
            return clean_html(html)
    elif "body" in payload and "data" in payload["body"]:
        decoded = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        return clean_html(decoded)

    return ""

def store_attachment(email_id, filename, file_path):
    db, cursor = connect_db()
    query = "INSERT INTO attachments (email_id, filename, file_path) VALUES (%s, %s, %s)"
    cursor.execute(query, (email_id, filename, file_path))
    db.commit()
    cursor.close()
    db.close()

def has_attachments(service, msg_data, email_id):
    parts = msg_data.get("payload", {}).get("parts", [])
    for part in parts:
        if part.get("filename"):  # Attachment exists
            return "Yes"
    return "No"

def fetch_latest_unread(service):
    results = service.users().messages().list(
        userId="me",
        labelIds=["UNREAD"],
        maxResults=1
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return None
    return service.users().messages().get(
        userId="me",
        id=messages[0]["id"],
        format="full"        # ← this is what you're missing
    ).execute()

def parse_message(msg_data) -> dict:
    headers = msg_data["payload"]["headers"]
    return {
        "id": msg_data["id"],
        "thread_id": msg_data.get("threadId"),
        "sender": next((h["value"] for h in headers if h["name"] == "From"), "Unknown"),
        "recipient": extract_email_address(
            next((h["value"] for h in headers if h["name"] == "To"), "Unknown")
        ),
        "subject": next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject"),
        "timestamp": datetime.fromtimestamp(int(msg_data["internalDate"]) / 1000, tz=timezone.utc),
        "body": extract_body(msg_data["payload"]),
        "has_attachment": has_attachments(None, msg_data, msg_data["id"])
    }

if __name__ == "__main__":
    service = get_gmail_service()
    raw = fetch_latest_unread(service)
    if raw:
        email = parse_message(raw)
        print(email["subject"])
        print(email["body"][:200])
        print("Fetched successfully (smoke test only — pipeline writes via email_pipeline.py)")
    else:
        print("No unread emails")
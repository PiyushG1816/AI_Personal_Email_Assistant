from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.services.Gmail_services import authenticate_gmail_api
import base64


def create_email_draft(to_email, subject, body, thread_id=None):
    creds = authenticate_gmail_api()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = f"Re: {subject}"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    print(f"Draft created. Draft ID: {draft['id']}")
    return draft

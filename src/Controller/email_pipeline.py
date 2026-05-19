import time
import schedule

from src.Database.Email_storage import (
    get_gmail_service,
    fetch_latest_unread,
    parse_message,
    store_email,
)
from src.Utils.Enrichment_chain import enrichment_chain
from src.services.Slack_services import send_meeting_alert, send_priority_alert
from src.services.Reply_services import create_email_draft


def run_pipeline():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Running email pipeline...")

    service = get_gmail_service()
    raw = fetch_latest_unread(service)
    if raw is None:
        print("No unread emails.")
        return

    email = parse_message(raw)
    result = enrichment_chain.invoke({
        "sender": email["sender"],
        "subject": email["subject"],
        "body": email["body"],
    })

    summary = result["summarizer"].strip()
    category = result["classifier"].strip()
    priority = result["priority"].strip().lower()
    key_info = result["key_info"]

    if key_info.meeting_title is not None:
        send_meeting_alert(key_info, email)

    elif priority.strip().lower().startswith("high") and key_info.action_required:
        draft_body = (
            "Hi,\n\n"
            f"{summary}\n\n"
            f"Action required: {key_info.action_required}\n\n"
            "Best regards"
        )
        create_email_draft(
            to_email=email["sender"],
            subject=email["subject"],
            body=draft_body,
            thread_id=email["thread_id"],
        )
        send_priority_alert(
            email,
            summary=summary,
            category=category,
            action_required=key_info.action_required,
        )

    store_email((
        email["id"],
        email["sender"],
        email["recipient"],
        email["subject"],
        email["timestamp"],
        email["body"],
        email["has_attachment"],
        email["thread_id"],
        summary,
        priority,
        category,
    ))
    print(f"Stored '{email['subject']}' [category={category}, priority={priority}]")


if __name__ == "__main__":
    run_pipeline()
    schedule.every(5).minutes.do(run_pipeline)
    print("\nScheduler started — checking every 5 minutes. Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(1)

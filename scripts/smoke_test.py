from appvault.config import load_email_credentials
from appvault.email_client import EmailClient

creds = load_email_credentials()
with EmailClient(creds) as client:
    messages = client.fetch_recent_messages(limit=3)
    for m in messages:
        print(f"Subject: {m.subject}")
        print(f"From: {m.sender_display_name} <{m.sender_address}>")
        print(f"Body (first 200 chars): {m.body[:200]!r}")
        print("---")
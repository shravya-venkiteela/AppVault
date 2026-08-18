import email
import imaplib
import logging
from dataclasses import dataclass

from appvault.config import EmailCredentials
from appvault.exceptions import EmailAuthenticationError, EmailConnectionError
logger = logging.getLogger("appvault.email_client")

@dataclass
class FetchedMessage:
    subject: str
    sender_display_name: str | None
    sender_address: str | None
    body: str


class EmailClient:
    """Thin wrapper around imaplib. All IMAP calls live here so this
    class can be mocked in tests without touching the network."""

    def __init__(self, credentials: EmailCredentials):
        self._credentials = credentials
        self._connection: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        logger.debug(f"Connecting to IMAP host: {self._credentials.imap_host}")
        try:
            self._connection = imaplib.IMAP4_SSL(self._credentials.imap_host)
        except (imaplib.IMAP4.error, OSError) as exc:
            raise EmailConnectionError(
                f"Could not connect to {self._credentials.imap_host}: {exc}"
            ) from exc
        logger.debug(f"Attempting login for {self._credentials.address}")
        try:
            self._connection.login(self._credentials.address, self._credentials.password)
        except imaplib.IMAP4.error as exc:
            logger.debug(f"Login failed: {exc}")
            raise EmailAuthenticationError(
                f"Login failed for {self._credentials.address}. "
                f"If your provider requires an app-specific password, confirm you're using one."
            ) from exc
        logger.debug("Login Successful")
    def fetch_recent_messages(self, folder: str = "INBOX", limit: int = 20) -> list[FetchedMessage]:
        """Fetch recent messages with subject, sender, and plain-text body.

        Unlike fetch_recent_subjects(), this pulls the full message so
        parser.py has body text to run its patterns against.
        """
        if self._connection is None:
            raise EmailConnectionError("Not connected. Call connect() first.")

        self._connection.select(folder)
        status, data = self._connection.search(None, "ALL")
        if status != "OK":
            raise EmailConnectionError(f"Search failed on folder '{folder}'.")

        message_ids = data[0].split()[-limit:]
        messages: list[FetchedMessage] = []

        for msg_id in reversed(message_ids):
            status, msg_data = self._connection.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw_bytes = msg_data[0][1]
            parsed = email.message_from_bytes(raw_bytes)

            subject = self._decode_header(parsed.get("Subject", ""))
            sender_name, sender_address = email.utils.parseaddr(parsed.get("From", ""))
            body = self._extract_plain_text_body(parsed)

            messages.append(
                FetchedMessage(
                    subject=subject,
                    sender_display_name=sender_name or None,
                    sender_address=sender_address or None,
                    body=body,
                )
            )

        return messages

    def fetch_recent_subjects(self, folder: str = "INBOX", limit: int = 10) -> list[str]:
        """Subject-only fetch, kept for the Milestone 5 smoke test.
        Use fetch_recent_messages() for anything that needs body text."""
        return [m.subject for m in self.fetch_recent_messages(folder=folder, limit=limit)]

    @staticmethod
    def _decode_header(raw_header: str) -> str:
        decoded_parts = email.header.decode_header(raw_header)
        pieces = []
        for text, encoding in decoded_parts:
            if isinstance(text, bytes):
                pieces.append(text.decode(encoding or "utf-8", errors="replace"))
            else:
                pieces.append(text)
        return "".join(pieces)

    @staticmethod
    def _extract_plain_text_body(parsed_message) -> str:
        if parsed_message.is_multipart():
            for part in parsed_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(charset, errors="replace")
            return ""
        else:
            charset = parsed_message.get_content_charset() or "utf-8"
            payload = parsed_message.get_payload(decode=True)
            return payload.decode(charset, errors="replace") if payload else ""

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection.logout()
            except imaplib.IMAP4.error:
                pass
            finally:
                self._connection = None


    def __enter__(self) -> "EmailClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
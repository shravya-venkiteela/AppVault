import imaplib
from unittest.mock import MagicMock, patch

import pytest

from appvault.config import EmailCredentials
from appvault.email_client import EmailClient
from appvault.exceptions import EmailAuthenticationError, EmailConnectionError


def _make_credentials() -> EmailCredentials:
    return EmailCredentials(
        address="test@example.com",
        password="fake-password",
        imap_host="imap.example.com",
    )


def test_connect_success_calls_login_with_correct_credentials():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_imap_class.return_value = mock_connection

        client = EmailClient(creds)
        client.connect()

        mock_imap_class.assert_called_once_with("imap.example.com")
        mock_connection.login.assert_called_once_with("test@example.com", "fake-password")


def test_connect_raises_connection_error_on_socket_failure():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL", side_effect=OSError("Connection refused")):
        client = EmailClient(creds)
        with pytest.raises(EmailConnectionError):
            client.connect()


def test_connect_raises_authentication_error_on_bad_login():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_connection.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        mock_imap_class.return_value = mock_connection

        client = EmailClient(creds)
        with pytest.raises(EmailAuthenticationError):
            client.connect()


def test_connection_and_authentication_errors_are_distinct_types():
    assert not issubclass(EmailConnectionError, EmailAuthenticationError)
    assert not issubclass(EmailAuthenticationError, EmailConnectionError)


def _make_raw_email_bytes(subject: str, sender: str, body: str) -> bytes:
    return (
        f"Subject: {subject}\r\n"
        f"From: {sender}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    ).encode("utf-8")


def test_fetch_recent_messages_parses_subject_sender_and_body():
    creds = _make_credentials()
    raw_bytes = _make_raw_email_bytes(
        subject="Thank you for applying",
        sender="Acme Recruiting <recruiting@acme.example.com>",
        body="We have received your application for Data Analyst.",
    )

    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_connection.search.return_value = ("OK", [b"1"])
        mock_connection.fetch.return_value = ("OK", [(b"1 (RFC822 {123}", raw_bytes)])
        mock_imap_class.return_value = mock_connection

        client = EmailClient(creds)
        client.connect()
        messages = client.fetch_recent_messages(limit=5)

    assert len(messages) == 1
    assert messages[0].subject == "Thank you for applying"
    assert messages[0].sender_display_name == "Acme Recruiting"
    assert messages[0].sender_address == "recruiting@acme.example.com"
    assert "Data Analyst" in messages[0].body


def test_fetch_recent_messages_raises_if_not_connected():
    creds = _make_credentials()
    client = EmailClient(creds)
    with pytest.raises(EmailConnectionError):
        client.fetch_recent_messages()


def test_fetch_recent_messages_skips_malformed_results_without_crashing():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_connection.search.return_value = ("OK", [b"1"])
        mock_connection.fetch.return_value = ("NO", [None])
        mock_imap_class.return_value = mock_connection

        client = EmailClient(creds)
        client.connect()
        messages = client.fetch_recent_messages(limit=5)

    assert messages == []


def test_close_calls_logout_and_clears_connection():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_imap_class.return_value = mock_connection

        client = EmailClient(creds)
        client.connect()
        client.close()

        mock_connection.close.assert_called_once()
        mock_connection.logout.assert_called_once()


def test_context_manager_connects_and_closes():
    creds = _make_credentials()
    with patch("imaplib.IMAP4_SSL") as mock_imap_class:
        mock_connection = MagicMock()
        mock_imap_class.return_value = mock_connection

        with EmailClient(creds) as client:
            assert client._connection is mock_connection

        mock_connection.logout.assert_called_once()
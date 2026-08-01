import os
from dataclasses import dataclass

from appvault.exceptions import AppVaultError

EMAIL_ADDRESS_VAR = "APPVAULT_EMAIL_ADDRESS"
EMAIL_PASSWORD_VAR = "APPVAULT_EMAIL_PASSWORD"
IMAP_HOST_VAR = "APPVAULT_IMAP_HOST"


class MissingCredentialsError(AppVaultError):
    """Raised when required environment variables are not set."""


@dataclass(frozen=True)
class EmailCredentials:
    address: str
    password: str
    imap_host: str


def load_email_credentials() -> EmailCredentials:
    address = os.environ.get(EMAIL_ADDRESS_VAR)
    password = os.environ.get(EMAIL_PASSWORD_VAR)
    imap_host = os.environ.get(IMAP_HOST_VAR)

    missing = [
        name for name, value in (
            (EMAIL_ADDRESS_VAR, address),
            (EMAIL_PASSWORD_VAR, password),
            (IMAP_HOST_VAR, imap_host),
        )
        if not value
    ]
    if missing:
        raise MissingCredentialsError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )

    return EmailCredentials(address=address, password=password, imap_host=imap_host)
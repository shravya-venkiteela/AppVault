import os
import re
from dataclasses import dataclass, field

from appvault.exceptions import AppVaultError

EMAIL_ADDRESS_VAR = "APPVAULT_EMAIL_ADDRESS"
EMAIL_PASSWORD_VAR = "APPVAULT_EMAIL_PASSWORD"
IMAP_HOST_VAR = "APPVAULT_IMAP_HOST"
HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$")
class MissingCredentialsError(AppVaultError):
    """Raised when required environment variables are not set."""


@dataclass(frozen=True)
class EmailCredentials:
    address: str
    password: str = field(repr=False)
    imap_host: str


def load_email_credentials() -> EmailCredentials:
    address = (os.environ.get(EMAIL_ADDRESS_VAR) or "").strip()
    password = (os.environ.get(EMAIL_PASSWORD_VAR) or "").strip()
    imap_host = (os.environ.get(IMAP_HOST_VAR) or "").strip()

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
    if not HOSTNAME_REGEX.match(imap_host):
        raise MissingCredentialsError(
           f"{IMAP_HOST_VAR} does not look like a valid hostname: '{imap_host}' "
           f"(expected something like 'imap.gmail.com', no scheme or path)"
        )
    return EmailCredentials(address=address, password=password, imap_host=imap_host)


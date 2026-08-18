class AppVaultError(Exception):
    """Base class for all AppVault-specific errors."""

class EmailConnectionError(AppVaultError):
    """Raised whenthe IMAP server can't be reached (wrong host, network down, port blocked)."""

class EmailAuthenticationError(AppVaultError):
    """Raised when login fails (wrong credentials, missing app-specific password). """

    
class StorageError(AppVaultError):
    """Raised on read/write or lookup failures against local storage."""
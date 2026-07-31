class AppVaultError(Exception):
    """Base class for all AppVault-specific errors."""

class StorageError(AppVaultError):
    """Raised on read/write or lookup failures against local storage."""
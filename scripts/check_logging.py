import os
import logging
from appvault.logging_setup import setup_logging

os.environ['APPVAULT_EMAIL_PASSWORD'] = 'super-secret-app-123'

setup_logging(debug=True)
logger = logging.getLogger('appvault.test')

logger.debug('Connecting with email password super-secret-app-123 to imap.gmail.com')

try:
    raise ConnectionError('Login failed for user with password super-secret-app-123')
except ConnectionError:
    logger.exception('Connection attempt failed')

logger.debug('Credentials: %s', 'super-secret-app-123')

logger = logging.getLogger("appvault")


# Store various constants here

# Maximum file upload size (in bytes).
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024

# Authentication constants
PWD_HASH_ALGORITHM = 'pbkdf2_sha256'
SALT_SIZE = 24
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1024
HASH_ROUNDS = 100000
PWD_RESET_KEY_LENGTH = 32
# Length of time before recovery key expires, in minutes.
PWD_RESET_KEY_EXPIRATION = 1440

class Permissions:
  '''
  Enumerates administrator permissions. These values are independent of
  each other, but must be unique. Permissions should be stored in the session
  '''
  # Access to the admin page
  Admin = 0
  # Website admins.
  SiteAdmin = 1
  # Allowed to add and manage users.
  UserAdmin = 2
  # Allowed to run the room hassle.
  HassleAdmin = 3

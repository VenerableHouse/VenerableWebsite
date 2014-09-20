# Store various constants here

# Maximum file upload size (in bytes).
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024

class Permissions:
  '''
  Enumerates administrator permissions. These values are independent of
  each other, but must be unique. Permissions should be stored in the session
  '''
  # Website admins.
  SiteAdmin = 1
  # Allowed to add and manage users.
  UserAdmin = 2

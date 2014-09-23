# Store various constants here

# Maximum file upload size (in bytes).
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024

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

# Store various constants here

# Maximum file upload size (in bytes).
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024

##### ACCESS LEVEL CONSTANTS  #####
AL_EDIT_PAGE = 3 # access level to edit a page
AL_USER_ADMIN = 7 # access level to add/edit members

# Enumerates permissions.
class Permissions:
  # Website admins.
  SiteAdmin = 1
  # Allowed to edit users' data.
  UserAdmin = 2

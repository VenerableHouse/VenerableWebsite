"""
Use this module to contain static data. Static data is directly used by the
codebase and should never be changed without a commit, as opposed to data
stored in the database that can change at any moment and whose values are not
necessarily constant.

Note: DO NOT re-use enum values unless you know exactly what you are doing!
"""

from RuddockWebsite.resource_utils import EnumValue

# Enum for permissions available to users.
class Permissions:
  # Site admins: always has access to everything
  ADMIN = EnumValue(1)
  # Add, edit, or delete user data
  USERS = EnumValue(2)
  # Run the room hassle
  HASSLE = EnumValue(3)
  # Manage mailing lists
  EMAIL = EnumValue(4)

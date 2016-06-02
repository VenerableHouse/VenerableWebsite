"""Hashes a password and formats the hash in our internal format.

This is useful for creating test data.

Example usage:
  python hash_password.py examplepassword
"""

import argparse

from ruddock import auth_utils
from ruddock import constants

parser = argparse.ArgumentParser(
    description="Prints a formatted hash of the password.")
parser.add_argument("password")

if __name__ == "__main__":
  args = parser.parse_args()
  salt = auth_utils.generate_salt()
  password_hash = auth_utils.hash_password(
      args.password,
      salt,
      constants.HASH_ROUNDS,
      constants.PWD_HASH_ALGORITHM)
  # Use the parser to format the hash.
  parser = auth_utils.PasswordHashParser(
      algorithms=[constants.PWD_HASH_ALGORITHM],
      rounds=[constants.HASH_ROUNDS],
      salts=[salt],
      password_hash=password_hash)
  print(str(parser))

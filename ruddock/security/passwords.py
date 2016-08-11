"""Provides utilities for password authentication."""

import hashlib

# List of supported algorithms.
SUPPORTED_ALGORITHMS = ["md5", "pbkdf2_sha256"]

# Current hash algorithm.
HASH_ALGORITHM = "pbkdf2_sha256"
SALT_SIZE = 24
HASH_COST = 100000

class PasswordHash(object):
  """Handles password hash formatting and password checking.

  See https://github.com/RuddockHouse/RuddockWebsite/wiki/Security-Design
  for a discussion of the password hash format.

  Fields:
    algorithms: list of algorithms.
    costs: list of costs. Values are either integers or None.
    salts: list of salts.
    hash_value: hex representation of the hash value.
  """

  def __init__(self,
      algorithms=None,
      costs=None,
      salts=None,
      hash_value=None):
    self.algorithms = algorithms if algorithms is not None else []
    self.costs = costs if costs is not None else []
    self.salts = salts if salts is not None else []
    self.hash_value = hash_value

  @classmethod
  def from_hash(cls, formatted_hash):
    """Parses a formatted hash string.

    Returns:
      An instance of this class, or None if the hash is not parseable.
    """
    components = formatted_hash.split("$")
    # Expect 5 components (empty string, algorithms, costs, salts, hash).
    if len(components) != 5 or components[0] != "":
      return None

    algorithms = components[1].split("|")
    costs = components[2].split("|")
    salts = components[3].split("|")
    hash_value = components[4]

    if any(x not in SUPPORTED_ALGORITHMS for x in algorithms):
      return None

    try:
      costs = [int(x) if len(x) > 0 else None for x in costs]
    except ValueError:
      # Something wasn't an integer.
      return None

    return cls(algorithms, costs, salts, hash_value)

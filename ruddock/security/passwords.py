"""Provides utilities for password authentication."""

import binascii
import hashlib

from ruddock.security import utils

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

  Attributes:
    algorithms: List of algorithm names.
    costs: List of cost values. Values are either integers or None.
    salts: List of salt values.
    hash_value: Hex representation of the hash value as a string.
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

    Args:
      formatted_hash: A formatted hash string.

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

  def __str__(self):
    """Returns the formatted hash string."""
    return "${0}${1}${2}${3}".format(
        "|".join(self.algorithms),
        "|".join([str(x) if x is not None else "" for x in self.costs]),
        "|".join(self.salts),
        self.hash_value)

  def verify_password(self, candidate):
    """Checks if the candidate password hashes to the true password's value.

    Args:
      candidate: The candidate password.

    Returns:
      True if passwords match, else False.
    """
    if not self._check_internal_state():
      return False
    candidate_hash = candidate
    try:
      for i in range(len(self.algorithms)):
        candidate_hash = compute_hash(
            candidate_hash,
            self.salts[i],
            self.costs[i],
            self.algorithms[i])
    except ValueError as e:
      # TODO(dkong): log when we have logging set up.
      return False
    return utils.compare_strings(candidate_hash, self.hash_value)

  def is_legacy(self):
    """Indicates if the hashing algorithm(s) used needs to be updated.

    Returns:
      True if the hash is computed using legacy algorithms, else False.
    """
    return len(self.algorithms) != 1 \
        or self.algorithms[0] != HASH_ALGORITHM \
        or self.costs[0] != HASH_COST

  def _check_internal_state(self):
    """Checks if the internal state is valid.

    Returns:
      True if this object can be used to verify a password, else False.
    """
    if len(self.algorithms) == 0 \
        or len(self.algorithms) != len(self.costs) \
        or len(self.algorithms) != len(self.salts):
      return False
    if self.hash_value is None:
      return False
    return all(x in SUPPORTED_ALGORITHMS for x in self.algorithms)

def compute_hash(password, salt, cost, algorithm):
  """Computes the hash for the input password.

  Args:
    password: The input string to hash.
    salt: A randomly generated salt string.
    cost: The cost parameter as an integer if appropriate. Otherwise, None.
    algorithm: The name of the algorithm. Must be in SUPPORTED_ALGORITHMS.

  Returns:
    The hash value as a hex string.

  Raises:
    ValueError if an invalid argument is passed.
  """
  if algorithm == "pbkdf2_sha256":
    if cost is None:
      raise ValueError("The pbkdf2_sha256 algorithm requires a cost.")
    result = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        cost)
    return binascii.hexlify(result).decode()
  elif algorithm == "md5":
    return hashlib.md5((salt + password).encode()).hexdigest()
  else:
    raise ValueError("Unrecognized algorithm name: {}".format(algorithm))

def generate_salt():
  """Generates a new salt value.

  Returns:
    A randomly generated salt.
  """
  return utils.generate_random_string(SALT_SIZE)

"""Test suite ruddock/security/passwords.py."""

import unittest

from ruddock.security import passwords

PWD = "hunter2"
SALTS = ["J6Wx4qd9iTQ6QLWceXoRbv33", "56SPBqd5FMtBpg5wCIQDAUSd"]
ALGORITHMS = ["md5", "pbkdf2_sha256"]
COSTS = [None, 100000]
HASH_VALUE = "5ebf7e04767ee8fc73f753f0ec78d2db92db7ad1617a688c5f6b3bc7dd8514d6"
HASH_STRING = "${}${}${}${}".format(
    "|".join(ALGORITHMS),
    "|".join(["", "100000"]), # Costs
    "|".join(SALTS),
    HASH_VALUE)

class PasswordHashTest(unittest.TestCase):

  def test_from_hash(self):
    ph = passwords.PasswordHash.from_hash(HASH_STRING)
    self.assertTrue(ph.verify_password("hunter2"))

  def test_is_legacy(self):
    ph = passwords.PasswordHash.from_hash(HASH_STRING)
    self.assertTrue(ph.is_legacy())

  def test_to_string(self):
    ph = passwords.PasswordHash(
        algorithms=ALGORITHMS,
        costs=COSTS,
        salts=SALTS,
        hash_value=HASH_VALUE)
    self.assertEqual(str(ph), HASH_STRING)

import string
import random

def generate_random_string(length, chars=None):
  """
  Generates a random string. Chars should be a string or list with the
  characters to choose from. If chars is not provided, then we default to all
  uppercase and lowercase letters plus digits.
  """
  # Sanity check on inputs.
  if not length >= 1:
    raise ValueError
  # Default character set.
  if chars is None:
    chars = string.ascii_letters + string.digits
  return "".join(random.SystemRandom().choice(chars) for i in range(length))

def compare_secure_strings(string1, string2):
  """
  String comparison function where the time complexity depends only on the
  length of the string and not the characters themselves. This function must be
  used for comparing cryptographic strings to prevent side-channel timing
  attacks.
  """
  result = len(string1) ^ len(string2)
  for x, y in zip(string1, string2):
    result |= ord(x) ^ ord(y)
  return result == 0

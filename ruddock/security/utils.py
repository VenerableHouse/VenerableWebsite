import string
import random

def generate_random_string(length, chars=None):
  """Generates a random (not pseudorandom) string.

  Args:
    length: A positive integer.
    chars: A string (or other iterable) of characters to choose from.
      If None is provided, default to using [a-zA-Z0-9].

  Returns:
    The generated string.
  """
  # Sanity check on inputs.
  if not length >= 1:
    raise ValueError("Invalid length: {}".format(length))
  # Default character set.
  if chars is None:
    chars = string.ascii_letters + string.digits
  return "".join(random.SystemRandom().choice(chars) for i in range(length))

def compare_strings(string1, string2):
  """Compares two strings for equality.

  The running time of this function depends only on the length of the strings
  and not their values. Use this function for comparing sensitive strings
  to prevent timing attacks.

  Args:
    string1: A string.
    string2: A string.

  Returns:
    True if string1 == string2, otherwise False.
  """
  result = len(string1) ^ len(string2)
  for x, y in zip(string1, string2):
    result |= ord(x) ^ ord(y)
  return result == 0

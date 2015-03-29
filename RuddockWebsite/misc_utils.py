import string
import random

def generate_random_string(length, chars=None):
  '''
  Generates a random string. Chars should be a string or list with the
  characters to choose from. If chars is not provided, then we default to all
  uppercase and lowercase letters plus digits.
  '''
  # Sanity check on inputs.
  if not length >= 1:
    raise ValueError
  # Default character set.
  if chars is None:
    chars = string.ascii_letters + string.digits
  return "".join(random.SystemRandom().choice(chars) for i in xrange(length))

import string
import random

def generate_random_string(length, chars=None):
  '''
  Generates a random string. Chars should be a string or list with the
  characters to choose from. If chars is not provided, then we default to all
  uppercase and lowercase letters plus digits. Note that this is pseudorandom.
  '''
  if chars is None:
    chars = string.ascii_letters + string.digits
  return "".join(random.choice(chars) for i in xrange(length))

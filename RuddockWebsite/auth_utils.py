"""
This module provides library classes and functions for everything concerning
authentication and authorization, including logins and permissions.
"""

import hashlib
import binascii
import string
import sqlalchemy
import flask

from RuddockWebsite import constants
from RuddockWebsite.constants import Permissions
from RuddockWebsite import misc_utils

class PasswordHashParser:
  """
  Class to manage parsed password hashes.

  Handling of current and legacy hashing algorithms:
  ==================================================

  We store all hashes in the format:

    $algorithm1|...|algorithmN$rounds1|...|roundsN$salt1|...|saltN$hash

  Where algorithmN is the most current algorithm (think of it as piping the
  result of one algorithm to the next). To compute the hash, we execute:

    algorithmN(saltN + algorithmN-1(saltN-1 + ... algorithm1(salt1 + password)))

  We do not store hashes from legacy algorithms in the database (the whole
  point of upgrading algorithms is to improve hash strength). Instead, we use
  the output from the first hash as the 'password' input to the next hash, so
  all passwords are hashed with the more secure algorithm. To keep track of the
  algorithm and parameters (rounds, salt) for each step, we use the format
  above. For example, if a password is initally hashed with MD5, then later
  upgraded to SHA1, then later upgraded to PBKDF2_SHA256, the hash string might
  look like this:

    $md5|sha1|pbkdf2_sha256$||100000$salt1|salt2|salt3$final_hash_here

  Note that 'rounds' may be the empty string if it does not apply to the
  algorithm used.

  Storing hashes in this format was designed to make it easier to upgrade
  algorithms in the future (simply take the actual hash as the password,
  generate a new salt, and then append the new algorithm, number of rounds, and
  salt to the modular hash formatted string). Upgrading algorithms with this
  design should be invisible to users.
  """

  # Static list of supported hashing algorithms.
  valid_algorithms = ['md5', 'pbkdf2_sha256']

  def __init__(self, algorithms=[], rounds=[], salts=[], password_hash=None):
    # Algorithm, rounds, and salt are lists. The order in which elements appear
    # in the list must be the order in which the algorithms are to be applied,
    # which is the same as the order in which they are stored. So if we want
    # sha256(md5(password)), then we have $md5|sha256$ which becomes
    # ['md5', 'sha256'].
    if password_hash is not None:
      self.algorithms = algorithms
      self.rounds = rounds
      self.salts = salts
      self.password_hash = password_hash
      # Check given values.
      if not self.check_self():
        raise ValueError
    else:
      self.algorithms = []
      self.rounds = []
      self.salts = []
      self.password_hash = None

  def __str__(self):
    """
    Method to convert object into string. This method is overridden to convert
    the object into the full hash string it was generated from. Can also be
    used to generate a full hash string.
    """
    # Must be initialized to some valid state.
    if not self.check_self():
      return None

    algorithms = self.algorithms
    rounds = map(lambda x: str(x) if x is not None else '', self.rounds)
    salts = self.salts

    algorithm_str = '|'.join(algorithms)
    rounds_str = '|'.join(rounds)
    salt_str = '|'.join(salts)
    return "${0}${1}${2}${3}".format(algorithm_str, rounds_str, salt_str,
        self.password_hash)

  def check_self(self):
    """
    This helper checks if this object is currently in a state that is valid for
    checking passwords.  Returns True if successful.
    """
    # Check that each list is nonempty and of the same length.
    if len(self.algorithms) == 0 \
        or len(self.algorithms) != len(self.rounds) \
        or len(self.algorithms) != len(self.salts):
      return False
    # Check that a password hash is actually set.
    if self.password_hash is None:
      return False

    # Check that each algorithm is supported.
    return all(x in PasswordHashParser.valid_algorithms
        for x in self.algorithms)

  def parse(self, full_hash):
    """
    Parses a hash in the format:
      $algorithm1|...|algorithmN$rounds1|...|roundsN$salt1|...|saltN$hash
    Returns True if successful, False if something unexpected happens.
    """
    hash_components = full_hash.split('$')
    # Expect 5 components (empty string, algorithms, rounds, salts, hash).
    if len(hash_components) != 5 or hash_components[0] != '':
      return False

    algorithms = hash_components[1].split('|')
    rounds = hash_components[2].split('|')
    salts = hash_components[3].split('|')
    password_hash = hash_components[4]

    # Algorithms must be valid.
    if any(x not in PasswordHashParser.valid_algorithms for x in algorithms):
      return False

    # Rounds must be integers. If empty string, set to None (not all algorithms
    # supported use key stretching).
    try:
      rounds = list(int(x) if len(x) != 0 else None for x in rounds)
    except ValueError:
      # Something wasn't an integer.
      return False

    # Update with parsed values.
    self.algorithms = algorithms
    self.rounds = rounds
    self.salts = salts
    self.password_hash = password_hash
    # Sanity check
    return self.check_self()

  def verify_password(self, password):
    """
    Verifies a password by applying each algorithm in turn to the password.
    Returns True if successful, else False.
    """
    # Check that we're in a state to check a password.
    if not self.check_self():
      return False

    test_hash = password
    true_hash = self.password_hash
    for i in xrange(len(self.algorithms)):
      algorithm = self.algorithms[i]
      rounds = self.rounds[i]
      salt = self.salts[i]
      test_hash = hash_password(test_hash, salt, rounds, algorithm)
      # In case an error occurs.
      if test_hash is None:
        return False
    return misc_utils.compare_secure_strings(test_hash, true_hash)

  def is_legacy(self):
    """
    Returns true if the hashing algorithm is not the most current version.
    """
    return len(self.algorithms) != 1 or \
        self.algorithms[0] != constants.PWD_HASH_ALGORITHM or \
        self.rounds[0] != constants.HASH_ROUNDS

def hash_password(password, salt, rounds, algorithm):
  """
  Hashes the password with the salt and algorithm provided. The supported
  algorithms are in PasswordHashParser.valid_algorithms.

  Returns just the hash (not the full hash string). Returns None if an error
  occurs.

  Algorithms using the passlib library are returned in base64 format.
  Algorithms using the hashlib library are returned in hex format.
  """
  if algorithm == 'pbkdf2_sha256':
    # Rounds must be set.
    if rounds is None:
      return None
    result = hashlib.pbkdf2_hmac('sha256', password, salt, rounds)
    return binascii.hexlify(result)
  elif algorithm == 'md5':
    # Rounds is ignored.
    return hashlib.md5(salt + password).hexdigest()
  return None

def set_password(username, password):
  """ Sets the user's password. Automatically generates a new salt. """
  algorithm = constants.PWD_HASH_ALGORITHM
  rounds = constants.HASH_ROUNDS
  salt = generate_salt()
  password_hash = hash_password(password, salt, rounds, algorithm)
  if password_hash is None:
    raise ValueError

  # Create new password hash string.
  parser = PasswordHashParser([algorithm], [rounds], [salt], password_hash)
  full_hash = str(parser)
  # Sanity check
  if full_hash is None:
    raise ValueError
  query = sqlalchemy.text("""
    UPDATE users
    SET password_hash=:ph
    WHERE username=:u
    """)
  flask.g.db.execute(query, ph=full_hash, u=username)
  return

def generate_salt():
  """ Generates a pseudorandom salt. """
  return misc_utils.generate_random_string(constants.SALT_SIZE)

def generate_reset_key():
  """
  Generates a random reset key. We use only digits and lowercase letters since
  the database string comparison is case insensitive (if more entropy is
  needed, just make the string longer).
  """
  chars = string.ascii_lowercase + string.digits
  return misc_utils.generate_random_string(constants.PWD_RESET_KEY_LENGTH,
      chars=chars)

def check_reset_key(reset_key):
  """ Returns the username if the reset key is valid, otherwise None. """
  query = sqlalchemy.text("""
    SELECT username
    FROM users
    WHERE password_reset_key = :rk AND NOW() < password_reset_expiration
    """)
  result = flask.g.db.execute(query, rk=reset_key).first()
  if result is not None:
    return result['username']
  else:
    return None

def get_user_id(username):
  """ Takes a username and returns the user's ID. """
  query = sqlalchemy.text("SELECT user_id FROM users WHERE username = :u")
  result = flask.g.db.execute(query, u = username).first()
  if result is not None:
    return int(result['user_id'])
  return None

def update_last_login(username):
  """ Updates the last login time for the user. """
  query = sqlalchemy.text("""
    UPDATE users
    SET lastlogin=NOW()
    WHERE username=:u
    """)
  flask.g.db.execute(query, u=username)

def generate_create_account_key():
  """
  Generates a random account creation key. Implementation is very similar to
  generate_reset_key().
  """
  chars = string.ascii_lowercase + string.digits
  return misc_utils.generate_random_string(constants.CREATE_ACCOUNT_KEY_LENGTH,
      chars=chars)

def check_create_account_key(key):
  """
  Returns the user_id if the reset key is valid (matches a user_id and that
  user does not already have an account). Otherwise returns None.
  """
  query = sqlalchemy.text("""
    SELECT user_id
    FROM members
    WHERE create_account_key = :k
      AND user_id NOT IN (SELECT user_id FROM users)
    """)
  result = flask.g.db.execute(query, k=key).first()
  if result is not None:
    return result['user_id']
  else:
    return None

def check_login():
  """ Returns true if the user is logged in. """
  return 'username' in flask.session

def login_redirect():
  """
  Redirects the user to the login page, saving the intended destination in the
  sesson variable. This function returns a redirect, so it must be called like
  this:

  return login_redirect()

  In order for it to work properly.
  """
  flask.session['next'] = flask.request.url
  flask.flash("You must be logged in to visit this page.")
  return flask.redirect(flask.url_for('auth.login'))

def get_permissions(username):
  """
  Returns a list with all of the permissions available to the user.
  A list is returned because Python sets cannot be stored in cookie data.
  """
  query = sqlalchemy.text("""
    (SELECT permission_id
      FROM users
        NATURAL JOIN offices
        NATURAL JOIN office_assignments
        NATURAL JOIN office_assignments_current
        NATURAL JOIN office_permissions
      WHERE username=:u)
    UNION
    (SELECT permission_id
      FROM users
        NATURAL JOIN user_permissions
      WHERE username=:u)
    """)
  result = flask.g.db.execute(query, u=username)
  return list(row['permission_id'] for row in result)

def check_permission(permission):
  """ Returns true if the user has the given permission. """
  if 'permissions' not in flask.session:
    return False
  # Admins always have access to everything.
  if Permissions.Admin in flask.session['permissions']:
    return True
  # Otherwise check if the permission is present in their permission list.
  return permission in flask.session['permissions']

class AdminLink:
  """ Simple class to hold link information. """
  def __init__(self, name, link):
    self.name = name
    self.link = link

def generate_admin_links():
  """ Generates a list of links for the admin page. """
  links = []
  if check_permission(Permissions.ModifyUsers):
    links.append(AdminLink('Add members',
      flask.url_for('admin.add_members', _external=True)))
    links.append(AdminLink('Manage positions',
      flask.url_for('admin.manage_positions', _external=True)))
  if check_permission(Permissions.RunHassle):
    links.append(AdminLink('Room hassle',
      flask.url_for('hassle.run_hassle', _external=True)))
  if check_permission(Permissions.EmailAdmin):
    links.append(AdminLink('Mailing lists',
      # This one needs to be hard coded.
      "https://ruddock.caltech.edu/mailman/admin"))
  return links

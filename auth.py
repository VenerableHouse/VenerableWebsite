import hashlib
import passlib.hash
import string
from sqlalchemy import text
from flask import session, g, url_for, flash
import constants as const
import email_utils
import email_templates
import misc_utils

class PasswordHashParser:
  '''
  Class to manage parsed password hashes. See comments for authenticate() for
  the format this class expects.
  '''

  # Static list of supported hashing algorithms.
  valid_algorithms = ['md5', 'pbkdf2_sha256']

  def __init__(self):
    # Algorithm, rounds, and salt are lists. The order in which elements appear
    # in the list must be the order in which the algorithms are to be applied,
    # which is the same as the order in which they are stored. So if we want
    # sha256(md5(password)), then we have $md5|sha256$ which becomes
    # ['md5', 'sha256'].
    self.algorithms = []
    self.rounds = []
    self.salts = []
    self.password_hash = None

  def __str__(self):
    '''
    Method to convert object into string. This method is overridden to conver
    the object into the full hash string it was generated from. Can also be
    used to generate a full hash string.
    '''
    # Cannot be used if not initialized.
    if self.password_hash is None:
      return None
    algorithms = self.algorithms
    rounds = map(lambda x: str(x) if x is not None else '', self.rounds)
    salts = self.salts

    algorithm_str = '|'.join(algorithms)
    rounds_str = '|'.join(rounds)
    salt_str = '|'.join(salts)
    return "${0}${1}${2}${3}".format(algorithm_str, rounds_str, salt_str, \
        self.password_hash)

  def parse(self, full_hash):
    '''
    Parses a hash in the format:

      $algorithm1|...|algorithmN$rounds1|...|roundsN$salt1|...|saltN$hash

    Returns True if successful, False if something unexpected happens.
    '''
    hash_components = full_hash.split('$')
    # Expect 5 components (empty string, algorithms, rounds, salts, hash).
    if len(hash_components) != 5 or hash_components[0] != '':
      return False

    algorithms = hash_components[1].split('|')
    rounds = hash_components[2].split('|')
    salts = hash_components[3].split('|')
    password_hash = hash_components[4]

    # Algorithms must be valid.
    if any(map(lambda x: x not in PasswordHashParser.valid_algorithms, algorithms)):
      return False

    # Rounds must be integers. If empty string, set to None (not all algorithms
    # supported use key stretching).
    try:
      rounds = map(lambda x: int(x) if len(x) != 0 else None, rounds)
    except ValueError:
      # Something wasn't an integer.
      return False

    # At least one algorithm must be given and all lists must be the same length.
    if len(algorithms) == 0 or \
        len(algorithms) != len(rounds) or len(algorithms) != len(salts):
      return False

    # Update with parsed values.
    self.algorithms = algorithms
    self.rounds = rounds
    self.salts = salts
    self.password_hash = password_hash
    return True

  def verify_password(self, password):
    '''
    Verifies a password by applying each algorithm in turn to the password.
    Returns True if successful, else False.
    '''
    if self.password_hash is None:
      # Not initialized properly.
      return False

    test_hash = password
    for i in xrange(len(self.algorithms)):
      algorithm = self.algorithms[i]
      rounds = self.rounds[i]
      salt = self.salts[i]
      test_hash = hash_password(test_hash, salt, rounds, algorithm)
    return test_hash == self.password_hash

  def is_legacy(self):
    ''' Returns true if the hashing algorithm is not the most current version. '''
    return len(self.algorithms) != 1 or \
        self.algorithms[0] != const.PWD_HASH_ALGORITHM or \
        self.rounds[0] != const.HASH_ROUNDS


def hash_password(password, salt, rounds, algorithm):
  '''
  Hashes the password with the salt and algorithm provided. The supported
  algorithms are in PasswordHashParser.valid_algorithms.

  Returns just the hash (not the full hash string). Returns None if an error
  occurs.

  Algorithms using the passlib library are returned in base64 format.
  Algorithms using the hashlib library are returned in hex format.
  '''
  if algorithm == 'pbkdf2_sha256':
    # Rounds must be set.
    if rounds is None:
      return None
    result = passlib.hash.pbkdf2_sha256.encrypt(password, salt=salt, rounds=rounds)
    # Return just the hash.
    return result.split('$')[-1]
  elif algorithm == 'md5':
    # Rounds is ignored.
    return hashlib.md5(salt + password).hexdigest()
  return None

def authenticate(username, password):
  '''
  Takes a username and password and checks if this corresponds to an actual
  user. Returns user_id if successful, else None.

  Handling of current and legacy hashing algorithms:
  ==================================================

  We store legacy hashes in the format:

    $algorithm1|...|algorithmN$rounds1|...|roundsN$salt1|...|saltN$hash

  Where algorithmN is the most current algorithm (think of it as piping the
  result of one algorithm to the next). To compute the hash, we execute:

    algorithmN(saltN + algorithmN-1(saltN-1 + ... algorithm1(salt1 + password)))

  We do not store hashes from legacy algorithms in the database. Instead, we
  use the output from the first hash as the 'password' input to the next hash,
  so all passwords are hashed with the more secure algorithm. If a password is
  authenticated using a legacy hash, it is then rehashed using only the most
  current algorithm.

  Storing hashes in this format was designed to make it easier to upgrade
  algorithms in the future (simply take the actual hash as the password,
  generate a new salt, and then append the new algorithm, number of rounds, and
  salt as appropriate.
  '''

  # Make sure the password is not too long (hashing extremely long passwords
  # can be used to attack the site, so we set an upper limit well beyond what
  # people generally use for passwords).
  if len(password) > const.MAX_PASSWORD_LENGTH:
    return None

  # Get the correct password hash and user_id from the database.
  query = text("SELECT user_id, password_hash FROM users WHERE username=:u")
  result = g.db.execute(query, u=username).first()
  if result is None:
    # Invalid username.
    return None
  user_id = result['user_id']
  password_hash = result['password_hash']

  # Parse the hash into a PasswordHashParser object.
  parser = PasswordHashParser()
  if parser.parse(password_hash):
    if parser.verify_password(password):
      # Check if password was legacy.
      if parser.is_legacy():
        # Rehash the password.
        set_password(username, password)
      # User is authenticated.
      return user_id
  return None

def set_password(username, password):
  ''' Sets the user's password. Automatically generates a new salt. '''
  algorithm = const.PWD_HASH_ALGORITHM
  rounds = const.HASH_ROUNDS
  salt = generate_salt()
  password_hash = hash_password(password, salt, rounds, algorithm)

  # Create new password hash string.
  parser = PasswordHashParser()
  parser.algorithms = [algorithm]
  parser.rounds = [rounds]
  parser.salts = [salt]
  parser.password_hash = password_hash
  full_hash = str(parser)
  query = text("UPDATE users SET password_hash=:ph WHERE username=:u")
  g.db.execute(query, ph=full_hash, u=username)
  return

def change_password(username, new_password, send_email=False):
  '''
  Changes a user's password. If send_email is True, then an email will be sent
  to the user notifying them that their password has been changed.
  '''
  set_password(username, new_password)

  if send_email:
    # Get the user's name and email.
    query = text("""
      SELECT CONCAT(fname, ' ', lname) AS name, email
      FROM members NATURAL JOIN users
      WHERE username=:u
      """)
    result = g.db.execute(query, u=username).first()
    if result is not None:
      email = result['email']
      name = result['name']
      subject = "Password change request"
      msg = email_templates.PasswordChangedEmail.format(name)
      email_utils.sendEmail(email, msg, subject)
  return

def handle_forgotten_password(username, email):
  '''
  Handles a forgotten password request. Takes a submitted (username, email)
  pair and checks that the email is associated with that username in the
  database. If successful, the user is emailed a reset key. Returns True on
  success, False if the (username, email) pair is not valid.
  '''
  # Check username, email pair.
  query = text("""
    SELECT user_id, CONCAT(fname, ' ', lname) AS name, email
    FROM members NATURAL JOIN users
    WHERE username=:u
    """)
  result = g.db.execute(query, u=username).first()

  if result is not None:
    if email == result['email']:
      name = result['name']
      user_id = result['user_id']
      # Generate a reset key for the user.
      reset_key = generate_reset_key()
      query = text("""
        UPDATE users
        SET password_reset_key = :rk,
        password_reset_expiration = NOW() + INTERVAL :time MINUTE
        WHERE username = :u
        """)
      g.db.execute(query, rk=reset_key, \
          time=const.PWD_RESET_KEY_EXPIRATION, u=username)
      # Determine if we want to say "your link expires in _ minutes" or "_ hours".
      if const.PWD_RESET_KEY_EXPIRATION < 60:
        expiration_time_str = "{} minutes".format(const.PWD_RESET_KEY_EXPIRATION)
      else:
        expiration_time_str = "{} hours".format(const.PWD_RESET_KEY_EXPIRATION / 60)
      # Send email to user.
      msg = email_templates.ResetPasswordEmail.format(name, \
          url_for('reset_password', reset_key=reset_key, _external=True), \
          expiration_time_str)
      subject = "Password reset request"
      email_utils.sendEmail(email, msg, subject)
      return True
  return False

def check_reset_key(reset_key):
  ''' Returns the username if the reset key is valid. Otherwise returns None. '''
  query = text("""
    SELECT username
    FROM users
    WHERE password_reset_key = :rk AND NOW() < password_reset_expiration
    """)
  result = g.db.execute(query, rk=reset_key).first()
  if result is not None:
    return result['username']
  else:
    return None

def handle_password_reset(username, new_password, new_password2):
  '''
  Handles the submitted password reset request. Returns True if successful,
  False otherwise. Also handles all messages displayed to the user.
  '''
  if not new_password:
    flash('You must provide a password!')
    return False
  elif not new_password2:
    flash('You must confirm your password!')
  elif new_password != new_password2:
    flash('Passwords do not match. Please try again!')
    return False
  elif len(new_password) < const.MIN_PASSWORD_LENGTH:
    flash('Your password must be at least {0} characters long!'.format( \
        const.MIN_PASSWORD_LENGTH))
    return False
  elif len(new_password) > const.MAX_PASSWORD_LENGTH:
    flash('Your password cannot be more than {0} characters long!'.format( \
        const.MAX_PASSWORD_LENGTH))
  else:
    # Actually change the password.
    set_password(username, new_password)
    # Clean up the password reset key, so that it cannot be used again.
    query = text("""
      UPDATE users
      SET password_reset_key = NULL, password_reset_expiration = NULL
      WHERE username = :u
      """)
    g.db.execute(query, u=username)
    # Get the user's email.
    query = text("""
      SELECT CONCAT(fname, ' ', lname) AS name, email
      FROM members NATURAL JOIN users
      WHERE username=:u
      """)
    result = g.db.execute(query, u=username).first()
    if result is not None:
      # Send confirmation email to user.
      email = result['email']
      name = result['name']
      msg = email_templates.ResetPasswordSuccessfulEmail.format(name)
      subject = "Password reset successful"
      email_utils.sendEmail(email, msg, subject)
    flash('Password successfully changed.')
    return True

def generate_salt():
  '''
  Generates a pseudorandom salt.
  '''
  return misc_utils.generate_random_string(const.SALT_SIZE)

def generate_reset_key():
  '''
  Generates a pseudorandom reset key. Guaranteed to be unique in the database.
  We use only digits and lowercase letters since the database string comparison
  is case insensitive (we already have more than enough entropy anyway).
  '''
  chars = string.ascii_lowercase + string.digits
  while True:
    reset_key = misc_utils.generate_random_string(const.PWD_RESET_KEY_LENGTH, \
        chars=chars)
    # Reset keys are random, so is extremely unlikely that they overlap.
    # However, it would be nice to make sure anyway.
    query = text("SELECT 1 FROM users WHERE password_reset_key = :rk")
    result = g.db.execute(query, rk=reset_key).first()
    # If a result is returned, then the key already exists.
    if result is None:
      break
  return reset_key

def get_permissions(username):
  '''
  Returns a list with all of the permissions available to the user.
  A list is returned because Python sets cannot be stored in cookie data.
  '''

  query = text("""
    (SELECT permission
      FROM users
        NATURAL JOIN offices
        NATURAL JOIN office_members_current
        NATURAL JOIN office_permissions
      WHERE username=:u)
    UNION
    (SELECT permission
      FROM users
        NATURAL JOIN user_permissions
      WHERE username=:u)
    """)
  result = g.db.execute(query, u=username)
  return [row['permission'] for row in result]

def get_user_id(username):
  ''' Takes a username and returns the user's ID. '''
  query = text("SELECT user_id FROM users WHERE username = :u")
  result = g.db.execute(query, u = username).first()

  if result is not None:
    return int(result['user_id'])
  return None

def check_permission(permission):
  ''' Returns true if the user has the input permission. '''
  if 'permissions' in session:
    return permission in session['permissions']
  return False

def update_last_login(username):
  ''' Updates the last login time for the user. '''
  query = text("UPDATE users SET lastlogin=NOW() WHERE username=:u")
  g.db.execute(query, u=username)

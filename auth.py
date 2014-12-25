import hashlib
import passlib.hash
import string
from sqlalchemy import text
from flask import session, g, url_for, flash
import constants as const
import email_utils
import email_templates
import misc_utils

def get_user_id(username):
  ''' Takes a username and returns the user's ID. '''
  query = text("SELECT user_id FROM users WHERE username = :u")
  result = g.db.execute(query, u = username).first()

  if result is not None:
    return int(result['user_id'])
  return None

def hash_password(password):
  '''
  Wrapper for cryptographically secure hashing method. Automatically generates
  salt. Use this function for all password hashing.
  '''
  algorithm = const.PWD_HASH_ALGORITHM
  password_hash = algorithm.encrypt(password, \
      salt_size=const.SALT_SIZE, \
      rounds=const.HASH_ROUNDS)
  return password_hash

def verify_password(password, password_hash):
  '''
  Verifies the username/password combination. The provided password_hash should
  be the correct hash to verfiy against. This is just a wrapper for the current
  hashing algorithm.
  '''
  algorithm = const.PWD_HASH_ALGORITHM
  try:
    return algorithm.verify(password, password_hash)
  except (TypeError, ValueError):
    # Something is wrong with the password or hash (wrong algorithm, invalid
    # characters, etc.
    return False

def verify_legacy_password(password, legacy_salt, password_hash, algorithm):
  '''
  Verifies a password using a legacy algorithm. The provided algorithm should
  be a string that describes an algorithm that was used in the past. Supported
  legacy algorithms:

  md5 - used through December 2014

  For security reasons, we do NOT store legacy hashes in the database
  (algorithms generally become legacy because they are easier to crack).
  Instead, we use the old hash as the input to the current hashing algorithm.
  For example, if MD5 is legacy and PBKDF2_SHA256 is the current, then the
  old hash MD5(password) should be stored as PBKDF2_SHA256(MD5(password)) in
  the database until the user logs in again and the password is rehashed
  properly.
  '''
  if algorithm == 'md5':
    legacy_hash = hashlib.md5(legacy_salt + password).hexdigest()
  else:
    # Provided algorithm doesn't match anything supported.
    return False
  return verify_password(legacy_hash, password_hash)

def authenticate(username, password):
  '''
  Takes a username and password and checks if this corresponds to
  an actual user. Returns user_id if successful, else None.

  This function defaults to using the current hashing algorithm. However, if
  that fails, then we also run through legacy algorithms, and if any legacy
  algorithm matches, then we rehash the user's password using the current
  algorithm and authenticate the user.
  '''
  # Make sure the password is not too long (hashing extremely long passwords
  # can be used to attack the site, so we set an upper limit well beyond what
  # people generally use for passwords).
  if len(password) > const.MAX_PASSWORD_LENGTH:
    return None
  # Get the correct password hash and user_id from the database.
  query = text("""
    SELECT user_id, password_hash, legacy_salt
    FROM users
    WHERE username=:u
    """)
  result = g.db.execute(query, u=username).first()
  if result is None:
    # Invalid username.
    return None
  user_id = result['user_id']
  password_hash = result['password_hash']

  result = False
  # Try current algorithm.
  if verify_password(password, password_hash):
    result = True
  # Try legacy algorithms.
  else:
    # Get legacy salt, if present.
    legacy_salt = result['legacy_salt'] if result['legacy_salt'] is not None else ''
    # Algorithms to try.
    legacy_algorithms = ['md5']
    for algorithm in legacy_algorithms:
      if verify_legacy_password(password, legacy_salt, password_hash, algorithm):
        # User is authenticated.
        result = True
        # Rehash the password.
        set_password(username, password)
        break
  if result:
    return user_id
  else:
    return None

def set_password(username, password):
  ''' Sets the user's password. '''
  password_hash = hash_password(password)
  query = text("UPDATE users SET password_hash=:ph WHERE username=:u")
  g.db.execute(query, ph=password_hash, u=username)
  return

def change_password(username, new_password, send_email=False):
  '''
  Changes a user's password. If send_email is True, then an email will be sent
  to the user notifying them that their password has been changed.
  '''
  set_password(username, password)

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

def check_permission(permission):
  ''' Returns true if the user has the input permission. '''
  if 'permissions' in session:
    return permission in session['permissions']
  return False

def update_last_login(username):
  ''' Updates the last login time for the user. '''
  query = text("UPDATE users SET lastlogin=NOW() WHERE username=:u")
  g.db.execute(query, u=username)

import hashlib
import binascii
import string
import random
from sqlalchemy import text
from flask import session, g, url_for
import constants as const
import email_utils
import email_templates

def hash_password(password, salt):
  '''
  Wrapper for cryptographically secure hashing method. Use this function for
  all password hashing.
  '''
  output = hashlib.pbkdf2_hmac('sha256', password, salt, const.HASH_ROUNDS)
  return binascii.hexlify(output)

def get_user_id(username):
  ''' Takes a username and returns the user's ID. '''
  query = text("SELECT user_id FROM users WHERE username = :u")
  result = g.db.execute(query, u = username).first()

  if result is not None:
    return int(result['user_id'])
  return None

def authenticate(username, password):
  '''
  Takes a username and password and checks if this corresponds to
  an actual user. Returns user_id if successful, else None.
  '''
  # Get salt
  query = text("SELECT salt FROM users WHERE username=:u")
  result = g.db.execute(query, u=username).first()
  salt = result['salt'] if result is not None and result['salt'] is not None else ''

  # Hash and check the password.
  password_hash = hash_password(password, salt)
  query = text("SELECT user_id FROM users WHERE username=:u AND password_hash=:ph")
  result = g.db.execute(query, u=username, ph=password_hash).first()

  if result is not None:
    return result['user_id']
  return None

def set_password(username, password):
  '''
  Sets the user's password.
  '''
  # Always generate a new salt.
  salt = generate_salt()
  password_hash = hash_password(password, salt)
  query = text("UPDATE users SET salt=:s, password_hash=:ph WHERE username=:u")
  g.db.execute(query, s=salt, ph=password_hash, u=username)

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

def handle_forgotten_password(username, email, reset_endpoint):
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
          time=const.PWD_RECOVERY_KEY_EXPIRATION, u=username)
      # Send email to user.
      msg = email_templates.ResetPasswordEmail.format(name, \
          # Generate reset link. We can't use url_for because this isn't
          # in the application context?
          "{0}?u={1}&k={2}".format(reset_endpoint, user_id, reset_key))
      subject = "Password reset request"
      email_utils.sendEmail(email, msg, subject)
      return True
  return False

def generate_reset_key():
  '''
  Generates a pseudorandom reset key.
  '''
  # Characters to choose from
  chars = string.ascii_letters + string.digits
  return "".join(random.choice(chars) for i in xrange(const.PWD_RECOVERY_KEY_LENGTH))

def generate_salt():
  '''
  Generates a random salt. It's pseudorandom but that's good enough for a salt.
  '''
  # Characters to choose from
  chars = string.ascii_letters + string.digits
  return "".join(random.choice(chars) for i in xrange(const.SALT_SIZE))

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

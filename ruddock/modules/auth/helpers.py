import flask
import sqlalchemy

from ruddock import auth_utils
from ruddock import constants
from ruddock import email_templates
from ruddock import email_utils
from ruddock import validation_utils

def authenticate(username, password):
  """
  Takes a username and password and checks if this corresponds to an actual
  user. Returns user_id if successful, else None. If a legacy algorithm is
  used, then the password is rehashed using the current algorithm.
  """

  # Make sure the password is not too long (hashing extremely long passwords
  # can be used to attack the site, so we set an upper limit well beyond what
  # people generally use for passwords).
  if len(password) > constants.MAX_PASSWORD_LENGTH:
    return None

  # Get the correct password hash and user_id from the database.
  query = sqlalchemy.text("""
    SELECT user_id, password_hash
    FROM users
    WHERE username=:u
    """)
  result = flask.g.db.execute(query, u=username).first()
  if result is None:
    # Invalid username.
    return None
  user_id = result['user_id']
  password_hash = result['password_hash']

  # Parse the hash into a PasswordHashParser object.
  parser = auth_utils.PasswordHashParser()
  if parser.parse(password_hash):
    if parser.verify_password(password):
      # Check if password was legacy.
      if parser.is_legacy():
        # Rehash the password.
        auth_utils.set_password(username, password)
      # User is authenticated.
      return user_id
  return None

def handle_forgotten_password(username, email):
  """
  Handles a forgotten password request. Takes a submitted (username, email)
  pair and checks that the email is associated with that username in the
  database. If successful, the user is emailed a reset key. Returns True on
  success, False if the (username, email) pair is not valid.
  """
  # Check username, email pair.
  query = sqlalchemy.text("""
    SELECT user_id, name, email
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN users
    WHERE username = :u
    """)
  result = flask.g.db.execute(query, u=username).first()

  if result is not None and email == result['email']:
    name = result['name']
    user_id = result['user_id']
    # Generate a reset key for the user.
    reset_key = auth_utils.generate_reset_key()
    query = sqlalchemy.text("""
      UPDATE users
      SET password_reset_key = :rk,
      password_reset_expiration = NOW() + INTERVAL :time MINUTE
      WHERE username = :u
      """)
    flask.g.db.execute(query, rk=reset_key,
        time=constants.PWD_RESET_KEY_EXPIRATION, u=username)
    # Determine if we want to say "your link expires in _ minutes" or
    # "your link expires in _ hours".
    if constants.PWD_RESET_KEY_EXPIRATION < 60:
      expiration_time_str = "{} minutes".format(
          constants.PWD_RESET_KEY_EXPIRATION)
    else:
      expiration_time_str = "{} hours".format(
          constants.PWD_RESET_KEY_EXPIRATION // 60)
    # Send email to user.
    msg = email_templates.ResetPasswordEmail.format(name,
        flask.url_for('auth.reset_password',
          reset_key=reset_key, _external=True),
        expiration_time_str)
    subject = "Password reset request"
    email_utils.send_email(email, msg, subject)
    return True
  return False

def handle_password_reset(username, new_password, new_password2):
  """
  Handles the submitted password reset request. Returns True if successful,
  False otherwise. Also handles all messages displayed to the user.
  """
  if not validation_utils.validate_password(new_password, new_password2):
    return False

  auth_utils.set_password(username, new_password)
  # Clean up the password reset key, so that it cannot be used again.
  query = sqlalchemy.text("""
    UPDATE users
    SET password_reset_key = NULL, password_reset_expiration = NULL
    WHERE username = :u
    """)
  flask.g.db.execute(query, u=username)
  # Get the user's email.
  query = sqlalchemy.text("""
    SELECT name, email
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN users
    WHERE username = :u
    """)
  result = flask.g.db.execute(query, u=username).first()
  # Send confirmation email to user.
  email = result['email']
  name = result['name']
  msg = email_templates.ResetPasswordSuccessfulEmail.format(name)
  subject = "Password reset successful"
  email_utils.send_email(email, msg, subject)
  return True

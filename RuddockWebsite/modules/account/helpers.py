import flask
import sqlalchemy

from RuddockWebsite import auth_utils
from RuddockWebsite import email_templates
from RuddockWebsite import email_utils
from RuddockWebsite import misc_utils
from RuddockWebsite import validation_utils

def get_user_data(user_id):
  ''' Helper function to get user data. '''
  query = sqlalchemy.text("""
    SELECT fname, lname, uid, matriculate_year, grad_year, email
    FROM members
    WHERE user_id=:uid
    """)
  return flask.g.db.execute(query, uid=user_id).first()

def handle_create_account(user_id, username, password, password2, birthday):
  '''
  Creates a new account. Flashes a message and returns False if an error
  occurs, otherwise returns True.
  '''
  # Validate username and password. The validate_* functions will flash errors.
  # We want to check all fields and not just stop at the first error.
  is_valid = True
  if not validation_utils.validate_username(username):
    is_valid = False
  if not validation_utils.validate_password(password, password2):
    is_valid = False
  if not validation_utils.validate_birthday(birthday):
    is_valid = False

  if not is_valid:
    return False

  # Insert new values into the database. Because the password is updated in a
  # separate step, we must use a transaction to execute this query.
  trans = flask.g.db.begin()
  try:
    # Insert the new row into users.
    query = sqlalchemy.text("""
      INSERT INTO users (user_id, username, password_hash)
      VALUES (:uid, :u, :ph)
      """)
    flask.g.db.execute(query, uid=user_id, u=username, ph='')
    # Set the password.
    auth_utils.set_password(username, password)
    # Set the birthday and invalidate the account creation key.
    query = sqlalchemy.text("""
      UPDATE members
      SET bday = :b,
        create_account_key = NULL
      WHERE user_id = :u
      """)
    flask.g.db.execute(query, b=birthday, u=user_id)
    trans.commit()
  except Exception:
    trans.rollback()
    flask.flash("An unexpected error occurred. Please find an IMSS rep.")
    return False
  # Email the user.
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, email
    FROM members NATURAL JOIN users
    WHERE username=:u
    """)
  result = flask.g.db.execute(query, u=username).first()
  # Send confirmation email to user.
  email = result['email']
  name = result['name']
  msg = email_templates.CreateAccountSuccessfulEmail.format(name, username)
  subject = "Thanks for creating an account!"
  email_utils.send_email(email, msg, subject)
  return True

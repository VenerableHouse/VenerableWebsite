from flask import g
from sqlalchemy import text
from RuddockWebsite import auth_utils
from RuddockWebsite import email_templates
from RuddockWebsite import email_utils
from RuddockWebsite import misc_utils

def get_user_data(user_id):
  ''' Helper funciton to get user data. '''
  query = text("""
    SELECT fname, lname, uid, matriculate_year, grad_year, email
    FROM members
    WHERE user_id=:uid
    """)
  return g.db.execute(query, uid=user_id).first()

def handle_create_account(user_id, username, password, password2, birthday):
  '''
  Creates a new account. Flashes a message and returns False if an error
  occurs, otherwise returns True.
  '''
  # Validate username and password. The validate_* functions will flash errors.
  if validation_utils.validate_username(username) \
      and validation_utils.validate_password(password, password2) \
      and validation_utils.validate_birthday(birthday):
    # Insert new values into the database. Because the password is updated in a
    # separate step, we must use a transaction to execute this query.
    trans = g.db.begin()
    try:
      # Insert the new row into users.
      query = text("""
        INSERT INTO users (user_id, username, password_hash)
        VALUES (:uid, :u, :ph)
        """)
      g.db.execute(query, uid=user_id, u=username, ph='')
      # Set the password.
      auth_utils.set_password(username, password)
      # Set the birthday.
      query = text("""
        UPDATE members
        SET birthday = :b
        WHERE user_id = :u
        """)
      g.db.execute(query, b=birthday, u=user_id)
      # Invalidate the account creation key.
      query = text("""
        UPDATE members
        SET create_account_key = NULL
        WHERE user_id = :u
        """)
      g.db.execute(query, u=user_id)
      trans.commit()
    except Exception:
      trans.rollback()
      flash("An unexpected error occurred. Please find an IMSS rep.")
      return False
    # Email the user.
    query = text("""
      SELECT CONCAT(fname, ' ', lname) AS name, email
      FROM members NATURAL JOIN users
      WHERE username=:u
      """)
    result = g.db.execute(query, u=username).first()
    # Send confirmation email to user.
    email = result['email']
    name = result['name']
    msg = email_templates.CreateAccountSuccessfulEmail.format(name, username)
    subject = "Thanks for creating an account!"
    email_utils.sendEmail(email, msg, subject)
    return True
  return False

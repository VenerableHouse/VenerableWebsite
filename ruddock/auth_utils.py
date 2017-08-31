"""
This module provides library classes and functions for everything concerning
authentication and authorization, including logins and permissions.
"""

import hashlib
import binascii
import string
import sqlalchemy
import flask

from ruddock import constants
from ruddock.resources import Permissions

def set_password(username, password):
  """Sets the user's password. Automatically generates a new salt."""
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
  """Returns the username if the reset key is valid, otherwise None."""
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
  """Takes a username and returns the user's ID."""
  query = sqlalchemy.text("SELECT user_id FROM users WHERE username = :u")
  result = flask.g.db.execute(query, u = username).first()
  if result is not None:
    return int(result['user_id'])
  return None

def update_last_login(username):
  """Updates the last login time for the user."""
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
  """Returns true if the user is logged in."""
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
  """Returns true if the user has the given permission."""
  if 'permissions' not in flask.session:
    return False
  # Admins always have access to everything.
  if Permissions.ADMIN in flask.session['permissions']:
    return True
  # Otherwise check if the permission is present in their permission list.
  return permission in flask.session['permissions']

class AdminLink:
  """Simple class to hold link information."""
  def __init__(self, name, link):
    self.name = name
    self.link = link

def generate_admin_links():
  """Generates a list of links for the admin page."""
  links = []
  if check_permission(Permissions.USERS):
    links.append(AdminLink('Add members',
      flask.url_for('admin.add_members', _external=True)))
    links.append(AdminLink('Manage positions',
      flask.url_for('admin.manage_positions', _external=True)))
  if check_permission(Permissions.HASSLE):
    links.append(AdminLink('Room hassle',
      flask.url_for('hassle.run_hassle', _external=True)))
  if check_permission(Permissions.ROTATION):
    links.append(AdminLink('Rotation',
      flask.url_for('rotation.show_portal', _external=True)))
  if check_permission(Permissions.EMAIL):
    links.append(AdminLink('Mailing lists',
      # This one needs to be hard coded.
      "https://ruddock.caltech.edu/mailman/admin"))
  if check_permission(Permissions.BIRTHDAYS):
    links.append(AdminLink('Birthday list',
      flask.url_for('birthdays.show_bdays', _external=True)))
  return links

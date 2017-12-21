import flask
import sqlalchemy
from collections import OrderedDict

from ruddock import auth_utils
from ruddock.resources import Permissions

def get_memberlist(search_type):
  """
  Retrieves the full memberlist. Valid values for search_type
  are 'all', 'current', or 'alumni'.
  """
  tables = "members NATURAL JOIN members_extra NATURAL JOIN membership_types"
  if search_type == "all":
    # Nothing to be done
    pass
  elif search_type == "current":
    tables += " NATURAL JOIN members_current"
  elif search_type == "alumni":
    tables += " NATURAL JOIN members_alumni"
  else:
    # Something went wrong (this should have been validated earlier).
    raise ValueError

  # We also want usernames, or NULL if they don't exist.
  tables += " NATURAL LEFT JOIN users"

  query = sqlalchemy.text("""
    SELECT user_id, username, first_name, last_name, email,
      matriculation_year, graduation_year, membership_desc
    FROM {}
    ORDER BY first_name
    """.format(tables))
  return flask.g.db.execute(query).fetchall()

def get_user_info(username):
  """Retrieves a user's info from their username."""
  user_id = get_user_id_from_username(username)
  if user_id is not None:
    return get_member_info(user_id)
  else:
    return None

def get_office_info(username):
  """Procedure to get a user's officer info."""
  query = sqlalchemy.text("""
    SELECT office_name, start_date, end_date
    FROM office_assignments NATURAL JOIN users NATURAL JOIN offices
    WHERE username = :u
    ORDER BY start_date, end_date, office_name
  """)
  return flask.g.db.execute(query, u=username).fetchall()

def get_user_id_from_username(username):
  """
  Given a user's username, returns their user_id. Returns None if no user
  with this username exists.
  """
  query = sqlalchemy.text('SELECT user_id FROM users WHERE username=:u')
  user_id = flask.g.db.execute(query, u=username).first()['user_id']
  if user_id is not None:
    return int(user_id)
  else:
    return None

def get_member_info(user_id):
  """
  Retrieves a member's info.
  Returns None if no member with this user_id exists.
  """
  query = sqlalchemy.text("""
    SELECT
      user_id,
      uid,
      first_name,
      last_name,
      preferred_name,
      name,
      email,
      phone,
      msc,
      birthday,
      matriculation_year,
      graduation_year,
      major,
      membership_desc,
      building,
      room_number
    FROM members
      NATURAL JOIN members_extra
      NATURAL JOIN membership_types
    WHERE user_id=:u
    """)
  return flask.g.db.execute(query, u=user_id).first()

def remove_member(user_id):
  """
  Permanently removes a member from the members database, removing any
  record of them from the website. Returns True on success and False otherwise.
  Be careful with this!
  """
  query = sqlalchemy.text("""
    DELETE
    FROM members
    WHERE user_id=:u
    """)
  # Return whether the query was successful or not. Since we're deleting
  # on a primary key, we know that we only have to check for row count
  # 1 or 0.
  return flask.g.db.execute(query, u=user_id).rowcount == 1

def edit_member_column(user_id, column, new_value):
  """Edits a member using the new value given."""
  # Using a string format instead of the sqlalchemy.text formatting method
  # for the column name, because otherwise it will always have single quotes
  # around it, which SQL doesn't like. The only more consistent way I can
  # think of to do this is to use SQLAlchemy's built-in query objects instead
  # of writing all the queries manually, but that involves changing a lot of
  # existing code.
  query = sqlalchemy.text("""
    UPDATE members
    SET {}=:new_val
    WHERE user_id=:u
    """.format(column))
  # Same pattern as the return for remove_member.
  return flask.g.db.execute(query, u=user_id, new_val=new_value).rowcount == 1

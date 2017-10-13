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
  """Retrieves a user's info."""
  query = sqlalchemy.text("""
    SELECT
      username,
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
      NATURAL JOIN users
    WHERE username=:u
    """)
  return flask.g.db.execute(query, u=username).first()

def get_office_info(username):
  """Procedure to get a user's officer info."""
  query = sqlalchemy.text("""
    SELECT office_name, start_date, end_date
    FROM office_assignments NATURAL JOIN users NATURAL JOIN offices
    WHERE username = :u
    ORDER BY start_date, end_date, office_name
  """)
  return flask.g.db.execute(query, u=username).fetchall()

def get_member_info(user_id):
  """Retrieves a member's info. Intended to be used in the case of a member not
  having an account on the website, which would make get_user_info
  impossible."""
  query = sqlalchemy.text("""
    SELECT
      user_id,
      uid,
      first_name,
      last_name,
      preferred_name,
      email,
      member_type,
      birthday,
      matriculation_year,
      graduation_year,
      msc,
      phone,
      building,
      room_number,
      major
    FROM members
    WHERE user_id=:user_id
    """)
  return flask.g.db.execute(query, user_id=user_id).first()

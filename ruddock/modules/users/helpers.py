import flask
import sqlalchemy
from collections import OrderedDict

from ruddock import auth_utils
from ruddock.resources import Permissions

search_filters_grad_year = [
    'grad2020',
    'grad2019',
    'grad2018',
    'grad2017',
    'grad2016',
    'grad2015',
    'grad2014',
    'grad2013',
    'grad2012',
    'grad2011',
    'grad2010',
    'grad2009',
    'grad2008',
    'grad2007'
]

def get_memberlist(search_type):
  """
  Retrieves the full memberlist. Valid values for search_type
  are 'all', 'current', or 'alumni'.
  or various graduation years.
  """
  tables = "members NATURAL JOIN members_extra NATURAL JOIN membership_types"
  if search_type == "all":
    # Nothing to be done
    pass
  elif search_type == "current":
    tables += " NATURAL JOIN members_current"
  elif search_type == "alumni":
    tables += " NATURAL JOIN members_alumni"
  elif search_type in search_filters_grad_year:
    pass
  else:
    # Something went wrong (this should have been validated earlier).
    raise ValueError

  # We also want usernames, or NULL if they don't exist.
  tables += " NATURAL LEFT JOIN users"

  sqlText = """
    SELECT user_id, username, first_name, last_name, email,
      matriculation_year, graduation_year, membership_desc
    FROM {}
    """

  if search_type in ["all", "current", "alumni"]:
    pass
  elif search_type in search_filters_grad_year:
    grad_year_str = search_type[4:8]
    sqlText += "WHERE graduation_year=" + grad_year_str + " "
  else:
    # This should never happen
    pass

  sqlText += "ORDER BY first_name"
  query = sqlalchemy.text(sqlText.format(tables))
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

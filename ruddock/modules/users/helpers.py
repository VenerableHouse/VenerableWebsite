import flask
import sqlalchemy
from collections import OrderedDict

from ruddock import auth_utils
from ruddock.resources import Permissions

def get_memberlist(search_type):
  """
  Retrieves the full memberlist. Valid values for search_type
  are 'all', 'current', or 'alumni'.
  or various graduation years.
  """
  search_filters_grad_year = get_all_grad_years()
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
    raise ValueError("Failed to get members with search filter: " + search_type)

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
    # Note: following line is not vulnerable to sql injection attack
    #       because search_type can only be from the list pulled from the database
    sqlText += "WHERE graduation_year=" + search_type + " "
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

def get_all_grad_years():
    """ Returns a list of strings of all graduation years with no dupliacates """
    query = "SELECT graduation_year FROM members NATURAL JOIN members_extra"
    grad_years_set = {'2020'} # need to put an initial value to make this a set instead of dict
    all_grad_years = flask.g.db.execute(query).fetchall()
    for grad_year in all_grad_years:
        cleaned_grad_year = grad_year[0]
        if cleaned_grad_year == None:
            continue
        grad_years_set.add(str(cleaned_grad_year))
    grad_years_list_sorted = list(grad_years_set)
    grad_years_list_sorted.sort()
    grad_years_list_sorted.reverse()
    if len(grad_years_list_sorted) > 5: # Only show the 5 most recent years
        grad_years_list_sorted = grad_years_list_sorted[0: 5]
    return grad_years_list_sorted


import flask
import sqlalchemy

from RuddockWebsite import search_utils
from RuddockWebsite.resources import MemberSearchMode

def search_members_by_name(query, mode=None):
  """
  Searches members by name. Returns a list of user_id values that match the
  search query. By default, this searches all members. If mode is set to
  'current', then only current members are searched. If mode is set to
  'alumni', then only alumni are searched.
  """
  if mode is None:
    table = "members"
  elif mode == "current":
    table = "members_current NATURAL JOIN members"
  elif mode == "alumni":
    table = "members_alumni NATURAL JOIN members"
  else:
    # This is not an option.
    raise ValueError

  # Don't name this 'query'!
  db_query = sqlalchemy.text("""
    SELECT user_id, CONCAT(fname, ' ', lname) AS name
    FROM {}
    ORDER BY name
    """.format(table))
  members = flask.g.db.execute(db_query)

  # Results from the search
  results = []

  # Parse the query.
  query_keywords = search_utils.parse_keywords(query)
  # Nothing to search here.
  if len(query_keywords) < 1:
    return results

  # The last keyword is special, since it can be a partial match (this handles
  # the case where the user is still typing).
  last_keyword = query.lower().split()[-1]

  # We want names that match every keyword in the query, allowing partial
  # matches on the last word.
  for member in members:
    member_keywords = search_utils.parse_keywords(member['name'])
    matches = search_utils.count_matches(member_keywords,
        query_keywords, [last_keyword])
    if matches >= len(query_keywords):
      results.append(member['user_id'])
  return results

def get_members(search_mode=None, columns=None, order_by=None):
  """
  Loads members from the database.

  search_mode should be an element of the MemberSearchMode enum.
  columns should be a list of strings (the columns to select).
  order_by should be a list of strings (the columns to order by).

  If you want to specify ASC/DESC for columns, it should look like:
  order_by = ["col1 ASC", "col2 DESC", ...]

  Provide either both columns and order_by or neither.
  """
  # Default values for args.
  if search_mode is None:
    search_mode = MemberSearchMode.ALL
  if columns is None:
    columns = ["user_id, name"]
  if order_by is None:
    order_by = ["name ASC"]

  # Determine which tables we're using.
  if search_mode == MemberSearchMode.ALL:
    tables = "members NATURAL JOIN members_extra"
  elif search_mode == MemberSearchMode.CURRENT:
    tables = "members NATURAL JOIN members_extra NATURAL JOIN members_current"
  elif search_mode == MemberSearchMode.ALUMNI:
    tables = "members NATURAL JOIN members_extra NATURAL JOIN members_alumni"
  else:
    # Invalid enum value.
    raise ValueError

  # Determine what columns we're using.
  selected_columns = ", ".join(columns)

  query = sqlalchemy.text("""
    SELECT {}
    FROM {}
    ORDER BY {}
    """)
  return flask.g.db.execute(query).fetchall()

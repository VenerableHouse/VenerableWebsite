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
  table = "members NATURAL JOIN members_extra"
  if mode is None:
    pass
  elif mode == "current":
    table += " NATURAL JOIN members_current"
  elif mode == "alumni":
    table += " NATURAL JOIN members_alumni"
  else:
    # Invalid request.
    raise ValueError

  # Don't name this 'query'!
  db_query = sqlalchemy.text("""
    SELECT user_id, name
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

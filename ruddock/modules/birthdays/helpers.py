import flask
import sqlalchemy

def fetch_birthdays():
  """Returns the birthdays of all current students."""
  query = sqlalchemy.text("""
    SELECT name, birthday
    FROM members
      NATURAL JOIN members_current
      NATURAL JOIN members_extra
  """)

  return flask.g.db.execute(query).fetchall()
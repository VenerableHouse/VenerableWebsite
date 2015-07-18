import flask
import sqlalchemy

# Template for queries (to reduce redundancy).
# Remainder of FROM clause and optional WHERE clause is customizable.
BASE_ASSIGNMENT_QUERY = """
SELECT assignment_id, start_date, end_date,
  office_id, office_name, office_email, is_excomm, is_ucc,
  user_id, CONCAT(fname, ' ', lname) AS name, username
FROM office_assignments
  NATURAL JOIN offices
  NATURAL JOIN members
  NATURAL JOIN users
{0}
ORDER BY office_order, start_date
"""

def get_current_assignments():
  """
  Gets all current office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text(BASE_ASSIGNMENT_QUERY.format(
    "NATURAL JOIN office_assignments_current"))
  return flask.g.db.execute(query).fetchall()

def get_past_assignments():
  """
  Gets all past office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text(BASE_ASSIGNMENT_QUERY.format(
    "NATURAL JOIN office_assignments_past"))
  return flask.g.db.execute(query).fetchall()

def get_future_assignments():
  """
  Gets all past office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text(BASE_ASSIGNMENT_QUERY.format(
    "NATURAL JOIN office_assignments_future"))
  return flask.g.db.execute(query).fetchall()

def get_all_assignments():
  """
  Gets all office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text(BASE_ASSIGNMENT_QUERY.format(''))
  return flask.g.db.execute(query).fetchall()

def get_all_offices():
  """
  Gets all available offices.
  """
  query = sqlalchemy.text("""
    SELECT office_id, office_name, is_excomm, is_ucc,
      office_email, office_order
    FROM offices
    WHERE is_active
    ORDER BY office_order
    """)
  return flask.g.db.execute(query).fetchall()

def get_assignment(assignment_id):
  """
  Loads details for the requested assignment. Returns None if no valid
  assignment exists.
  """
  query = sqlalchemy.text(BASE_ASSIGNMENT_QUERY.format(
    "WHERE assignment_id = :a"))
  result = flask.g.db.execute(query, a=assignment_id).first()
  # Technically this does exactly the same thing as returning result
  # immediately, but it's a bit more clear what's going on this way.
  if result is None:
    return None
  return result

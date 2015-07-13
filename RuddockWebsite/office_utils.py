import flask
import sqlalchemy

def get_current_assignments():
  """
  Gets all current office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc, start_date, end_date
    FROM office_assignments_current
      NATURAL JOIN office_assignments
      NATURAL JOIN offices
      NATURAL JOIN members
      NATURAL JOIN users
    ORDER BY office_order
    """)
  return flask.g.db.execute(query).fetchall()

def get_past_assignments():
  """
  Gets all past office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc, start_date, end_date
    FROM office_assignments_past
      NATURAL JOIN office_assignments
      NATURAL JOIN offices
      NATURAL JOIN members
      NATURAL JOIN users
    ORDER BY office_order
    """)
  return flask.g.db.execute(query).fetchall()

def get_future_assignments():
  """
  Gets all past office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc, start_date, end_date
    FROM office_assignments_future
      NATURAL JOIN office_assignments
      NATURAL JOIN offices
      NATURAL JOIN members
      NATURAL JOIN users
    ORDER BY office_order
    """)
  return flask.g.db.execute(query).fetchall()

def get_all_assignments():
  """
  Gets all office assignments. Also gets additional information
  including name and username.
  """
  query = sqlalchemy.text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc, start_date, end_date
    FROM office_assignments
      NATURAL JOIN offices
      NATURAL JOIN members
      NATURAL JOIN users
    ORDER BY office_order
    """)
  return flask.g.db.execute(query).fetchall()

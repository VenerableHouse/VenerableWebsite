import flask
import sqlalchemy

from ruddock import validation_utils

def handle_new_assignment(office_id, user_id, start_date, end_date):
  """
  Validates provided form data and creates the new assignment if successful.
  Returns True on success, False otherwise.
  """
  # Check that IDs are integers, at least.
  try:
    office_id = int(office_id)
    user_id = int(user_id)
    assert office_id >= 0
    assert user_id >= 0
  except Exception:
    flask.flash("Invalid request.")
    return False

  # Check date strings. This automatically flashes error messages.
  if not validation_utils.validate_date(start_date) \
      or not validation_utils.validate_date(end_date):
    return False

  # Start date should be before end date...
  # Conveniently, since we use YYYY-MM-DD format, we can compare the strings directly.
  if end_date <= start_date:
    flask.flash("Start date must be before end date!")
    return False

  query = sqlalchemy.text("""
    INSERT INTO office_assignments (office_id, user_id, start_date, end_date)
    VALUES (:oid, :uid, :start, :end)
    """)
  try:
    flask.g.db.execute(query, oid=office_id, uid=user_id,
        start=start_date, end=end_date)
    return True
  except Exception:
    flask.flash("Encountered unexpected error. Try again?")
    return False

def handle_edit_assignment(assignment_id, start_date, end_date):
  """
  Validates form data and edits the existing assignment.
  Returns True on success, False otherwise.
  """
  if not validation_utils.validate_date(start_date) \
      or not validation_utils.validate_date(end_date):
    return False

  if end_date <= start_date:
    flask.flash("Start date must be before end date!")

  query = sqlalchemy.text("""
    UPDATE office_assignments
    SET start_date = :start,
      end_date = :end
    WHERE assignment_id = :a
    """)
  try:
    flask.g.db.execute(query, start=start_date, end=end_date, a=assignment_id)
    return True
  except Exception:
    return False

def handle_delete_assignment(assignment_id):
  """
  Deletes an assignment.
  """
  query = sqlalchemy.text("""
    DELETE FROM office_assignments
    WHERE assignment_id = :a
    """)
  try:
    flask.g.db.execute(query, a=assignment_id)
    return True
  except Exception:
    return False

def get_members():
  """ Returns name and ID for all members. """
  query = sqlalchemy.text("""
    SELECT user_id, name
    FROM members NATURAL JOIN members_extra
    ORDER BY name
    """)
  return flask.g.db.execute(query).fetchall()

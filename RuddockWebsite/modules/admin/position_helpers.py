import flask
import sqlalchemy

from RuddockWebsite import validation_utils

def handle_new_assignment(office_id, user_id, start_date, end_date):
  """
  Validates provided form data and creates the new assignment if successful.
  Returns True on success, False otherwise.
  """
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
    flask.flash("Something's not quite right...")
    raise
    return False

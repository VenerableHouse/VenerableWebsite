"""
Tests that database is synced with enums defined in constants.py.
"""
import sqlalchemy

from RuddockWebsite import constants
from RuddockWebsite.tests.fixtures import db

def test_permissions(db):
  """
  Checks that constants.Permissions is synced with the permissions table.
  """
  query = sqlalchemy.text("""
    SELECT permission_id
    FROM permissions
    """)
  result = db.execute(query)
  db_values = list(r['permission_id'] for r in result)

  assert len(db_values) == len(constants.Permissions)
  for p in constants.Permissions:
    assert p in db_values

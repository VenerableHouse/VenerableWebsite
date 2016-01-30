"""
Tests routes in the users module.
"""

import flask
import sqlalchemy
import httplib

from ruddock.tests import utils
from ruddock.tests.fixtures import client, db

def test_show_memberlist(client):
  """Tests /members route."""
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(flask.url_for('users.show_memberlist'))
  assert response.status_code == httplib.OK

def test_view_profile(client, db):
  """Tests that viewing a user works."""
  # Find a user to test.
  query = sqlalchemy.text("SELECT username FROM users LIMIT 1")
  result = db.execute(query).first()
  if result is not None:
    username = result['username']
    with client.session_transaction() as session:
      utils.login(session)
    response = client.get(
        flask.url_for('users.view_profile', username=username))
    assert response.status_code == httplib.OK

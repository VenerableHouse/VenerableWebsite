"""
Tests routes in the users module.
"""

import flask
import sqlalchemy
import httplib

from ruddock.testing import utils
from ruddock.testing.fixtures import client

def test_show_memberlist(client):
  """Tests /members route."""
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(flask.url_for('users.show_memberlist'))
  assert response.status_code == httplib.OK

def test_view_member(client):
  """Tests that viewing a user works."""
  user_id = 1
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(
      flask.url_for('users.view_member', user_id=user_id))
  assert response.status_code == httplib.OK

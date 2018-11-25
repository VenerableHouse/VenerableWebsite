"""
Tests routes in the users module.
"""

import flask
import sqlalchemy
import http.client

from ruddock.testing import utils

def test_show_memberlist(client):
  """Tests /members route."""
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(flask.url_for('users.show_memberlist'))
  assert response.status_code == http.client.OK

def test_view_profile(client):
  """Tests that viewing a user works."""
  username = "twilight"
  with client.session_transaction() as session:
    utils.login(session)
  response = client.get(
      flask.url_for('users.view_profile', username=username))
  assert response.status_code == http.client.OK

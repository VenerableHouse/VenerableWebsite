"""
Tests routes that are not in a module.
"""

import flask
import httplib

from ruddock.testing.fixtures import client

def test_home(client):
  """Tests the / route."""
  response = client.get(flask.url_for('home'))
  assert response.status_code == httplib.OK

def test_contact(client):
  """Tests the /contact route."""
  response = client.get(flask.url_for('show_contact'))
  assert response.status_code == httplib.OK
